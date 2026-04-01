"""
SQLite persistence for the MCTS transposition table.

The transposition table is a Dict[tuple, MCTSInfo] keyed by canonical_key(game_state).
This module provides three operations:

  save_statistics(path, statistics)   -- upsert, overwriting existing value/visits
  load_statistics(path)               -- load the full table from disk
  merge_statistics(path, statistics)  -- upsert, accumulating value and visits

Schema follows the design in .notes/SERIALIZATION.md (subset: no mcts_edges or
pending_triggers, which are out of scope for the transposition table).
"""
import hashlib
import os
import pickle
import sqlite3
from typing import Dict

from mtg_ai.search import MCTSInfo


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS game_states (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_hash BLOB    NOT NULL UNIQUE,
    turn_number    INTEGER NOT NULL,
    land_drops     INTEGER NOT NULL,
    active_player  INTEGER NOT NULL,
    mana_white     INTEGER NOT NULL DEFAULT 0,
    mana_blue      INTEGER NOT NULL DEFAULT 0,
    mana_black     INTEGER NOT NULL DEFAULT 0,
    mana_red       INTEGER NOT NULL DEFAULT 0,
    mana_green     INTEGER NOT NULL DEFAULT 0,
    mana_gold      INTEGER NOT NULL DEFAULT 0,
    mana_colorless INTEGER NOT NULL DEFAULT 0,
    mana_generic   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS game_objects (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    game_state_id  INTEGER NOT NULL REFERENCES game_states(id) ON DELETE CASCADE,
    card_class     TEXT    NOT NULL,
    zone_type      TEXT    NOT NULL,
    zone_owner     INTEGER NOT NULL DEFAULT -1,
    zone_position  INTEGER NOT NULL DEFAULT -1,
    tapped         INTEGER NOT NULL DEFAULT 0,
    summoning_sick INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_game_objects_state ON game_objects(game_state_id);

CREATE TABLE IF NOT EXISTS object_counters (
    game_object_id INTEGER NOT NULL REFERENCES game_objects(id) ON DELETE CASCADE,
    counter_type   TEXT    NOT NULL,
    count          INTEGER NOT NULL,
    PRIMARY KEY (game_object_id, counter_type)
);

CREATE TABLE IF NOT EXISTS mcts_stats (
    game_state_id INTEGER PRIMARY KEY REFERENCES game_states(id) ON DELETE CASCADE,
    value         REAL    NOT NULL DEFAULT 0.0,
    visits        INTEGER NOT NULL DEFAULT 0
);
"""


def _canonical_hash(key: tuple) -> bytes:
    """SHA-256 of the canonical key, stable across processes."""
    return hashlib.sha256(pickle.dumps(key, protocol=4)).digest()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def _decompose_key(key: tuple) -> tuple:
    """
    Split a canonical_key tuple into its component parts for DB insertion.

    canonical_key structure:
        (turn_number, land_drops, active_player, mana_key, objects_key)

    mana_key:
        (white, blue, black, red, green, gold, colorless, generic)

    objects_key: sorted tuple of
        (class_name, zone_class, zone_owner, zone_pos, tapped, sick, counters)
        where counters = sorted tuple of (counter_type, count)

    Returns:
        (gs_fields: dict, objects: list of dict)
    """
    turn_number, land_drops, active_player, mana_key, objects_key = key
    mw, mb_lu, mb_la, mr, mg, mgo, mc, mge = mana_key

    gs_fields = {
        'turn_number': turn_number,
        'land_drops': land_drops,
        'active_player': active_player,
        'mana_white': mw,
        'mana_blue': mb_lu,
        'mana_black': mb_la,
        'mana_red': mr,
        'mana_green': mg,
        'mana_gold': mgo,
        'mana_colorless': mc,
        'mana_generic': mge,
    }

    objects = []
    for obj_tuple in objects_key:
        class_name, zone_class, zone_owner, zone_pos, tapped, sick, counters = obj_tuple
        objects.append({
            'card_class': class_name,
            'zone_type': zone_class,
            'zone_owner': zone_owner,
            'zone_position': zone_pos,
            'tapped': int(tapped),
            'summoning_sick': int(sick),
            'counters': counters,   # tuple of (counter_type, count)
        })

    return gs_fields, objects


def _recompose_key(gs_row: sqlite3.Row,
                   obj_rows: list[sqlite3.Row],
                   counter_map: dict[int, list]) -> tuple:
    """
    Reconstruct a canonical_key tuple from DB rows.

    counter_map maps game_object.id -> list of (counter_type, count).
    """
    mana_key = (
        gs_row['mana_white'], gs_row['mana_blue'], gs_row['mana_black'],
        gs_row['mana_red'], gs_row['mana_green'], gs_row['mana_gold'],
        gs_row['mana_colorless'], gs_row['mana_generic'],
    )

    obj_tuples = []
    for obj in obj_rows:
        counters = tuple(sorted(counter_map.get(obj['id'], [])))
        obj_tuple = (
            obj['card_class'],
            obj['zone_type'],
            obj['zone_owner'],
            obj['zone_position'],
            bool(obj['tapped']),
            bool(obj['summoning_sick']),
            counters,
        )
        obj_tuples.append(obj_tuple)

    objects_key = tuple(sorted(obj_tuples))
    return (
        gs_row['turn_number'],
        gs_row['land_drops'],
        gs_row['active_player'],
        mana_key,
        objects_key,
    )


def _insert_game_state(conn: sqlite3.Connection,
                       chash: bytes,
                       gs_fields: dict,
                       objects: list,
                       info: MCTSInfo,
                       replace_stats: bool) -> None:
    """
    Insert (or replace) a game state and its objects, then upsert mcts_stats.

    replace_stats=True  → overwrite existing value/visits (save semantics)
    replace_stats=False → accumulate existing value/visits (merge semantics)
    """
    # Upsert game_states (structural data never changes for a given hash)
    conn.execute("""
        INSERT OR IGNORE INTO game_states
            (canonical_hash, turn_number, land_drops, active_player,
             mana_white, mana_blue, mana_black, mana_red, mana_green,
             mana_gold, mana_colorless, mana_generic)
        VALUES
            (:hash, :turn_number, :land_drops, :active_player,
             :mana_white, :mana_blue, :mana_black, :mana_red, :mana_green,
             :mana_gold, :mana_colorless, :mana_generic)
    """, {'hash': chash, **gs_fields})

    gs_id = conn.execute(
        "SELECT id FROM game_states WHERE canonical_hash = ?", (chash,)
    ).fetchone()['id']

    # Only insert objects if this is a new state (they're structurally immutable)
    existing_objs = conn.execute(
        "SELECT COUNT(*) FROM game_objects WHERE game_state_id = ?", (gs_id,)
    ).fetchone()[0]

    if existing_objs == 0:
        cur = conn.cursor()
        for obj in objects:
            cur.execute("""
                INSERT INTO game_objects
                    (game_state_id, card_class, zone_type, zone_owner,
                     zone_position, tapped, summoning_sick)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (gs_id, obj['card_class'], obj['zone_type'], obj['zone_owner'],
                  obj['zone_position'], obj['tapped'], obj['summoning_sick']))
            obj_id = cur.lastrowid
            for counter_type, count in obj['counters']:
                cur.execute("""
                    INSERT INTO object_counters (game_object_id, counter_type, count)
                    VALUES (?, ?, ?)
                """, (obj_id, counter_type, count))

    # Upsert mcts_stats
    if replace_stats:
        conn.execute("""
            INSERT INTO mcts_stats (game_state_id, value, visits)
            VALUES (?, ?, ?)
            ON CONFLICT (game_state_id) DO UPDATE SET
                value  = excluded.value,
                visits = excluded.visits
        """, (gs_id, info.value, info.visits))
    else:
        conn.execute("""
            INSERT INTO mcts_stats (game_state_id, value, visits)
            VALUES (?, ?, ?)
            ON CONFLICT (game_state_id) DO UPDATE SET
                value  = mcts_stats.value  + excluded.value,
                visits = mcts_stats.visits + excluded.visits
        """, (gs_id, info.value, info.visits))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_statistics(path: str, statistics: Dict[tuple, MCTSInfo]) -> None:
    """
    Persist the transposition table to a SQLite database at *path*.

    Existing entries for the same canonical state are **replaced** (value and
    visits are overwritten, not accumulated).  Use merge_statistics() to
    accumulate across runs instead.
    """
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_schema(conn)
        for key, info in statistics.items():
            chash = _canonical_hash(key)
            gs_fields, objects = _decompose_key(key)
            _insert_game_state(conn, chash, gs_fields, objects, info, replace_stats=True)


def load_statistics(path: str) -> Dict[tuple, MCTSInfo]:
    """
    Load the transposition table from *path*.

    Returns an empty dict if the file does not exist.
    """
    if not os.path.exists(path):
        return {}

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_schema(conn)

        gs_rows = conn.execute("""
            SELECT gs.*, ms.value, ms.visits
            FROM game_states gs
            JOIN mcts_stats ms ON ms.game_state_id = gs.id
        """).fetchall()

        if not gs_rows:
            return {}

        # Load all objects and counters in bulk
        gs_ids = [row['id'] for row in gs_rows]
        placeholders = ','.join('?' * len(gs_ids))

        obj_rows = conn.execute(
            f"SELECT * FROM game_objects WHERE game_state_id IN ({placeholders})",
            gs_ids
        ).fetchall()

        obj_ids = [obj['id'] for obj in obj_rows]
        counter_map: dict[int, list] = {}
        if obj_ids:
            ctr_placeholders = ','.join('?' * len(obj_ids))
            ctr_rows = conn.execute(
                f"SELECT * FROM object_counters WHERE game_object_id IN ({ctr_placeholders})",
                obj_ids
            ).fetchall()
            for ctr in ctr_rows:
                counter_map.setdefault(ctr['game_object_id'], []).append(
                    (ctr['counter_type'], ctr['count'])
                )

        # Group objects by game_state_id
        objs_by_state: dict[int, list] = {}
        for obj in obj_rows:
            objs_by_state.setdefault(obj['game_state_id'], []).append(obj)

        result: Dict[tuple, MCTSInfo] = {}
        for gs_row in gs_rows:
            state_objs = objs_by_state.get(gs_row['id'], [])
            key = _recompose_key(gs_row, state_objs, counter_map)
            result[key] = MCTSInfo(value=gs_row['value'], visits=gs_row['visits'])

        return result


def merge_statistics(path: str, statistics: Dict[tuple, MCTSInfo]) -> None:
    """
    Accumulate the transposition table into the database at *path*.

    For each entry, the existing value and visits are **added to** rather than
    replaced.  The database is created if it does not exist.  This is the
    right operation for combining results from parallel MCTS workers.
    """
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_schema(conn)
        for key, info in statistics.items():
            chash = _canonical_hash(key)
            gs_fields, objects = _decompose_key(key)
            _insert_game_state(conn, chash, gs_fields, objects, info, replace_stats=False)
