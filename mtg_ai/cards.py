from mtg_ai import game, actions, getters, zone
from typing import Iterable, Optional
from dataclasses import dataclass, field
from enum import Enum


class CardType(str, Enum):
    Land = "land"
    Creature = "creature"
    Instant = "instant"
    Sorcery = "sorcery"
    Artifact = "artifact"

class Card(game.GameObject):

    @dataclass
    class Abilities:
        static: list = field(default_factory=list)
        activated: list = field(default_factory=list)

    def __init__(self, name,
                 cost: Optional[game.Mana] = None,
                 types: Iterable[CardType]=(),
                 subtypes: Iterable[str] = (),
                 abilities: Optional[Abilities] = None,
                 zone:Optional[zone.Zone]=None,
                 permanent: bool = False,
                 tapped: bool = False,
                 game_state: Optional[game.GameState] = None,
             ):

        super().__init__(game_state)
        self.cost = cost
        self.zone = zone 
        self.name = name
        self.types = set(types)
        self.subtypes = set(st.lower() for st in subtypes)
        self.permanent = permanent
        self.tapped = tapped
        self.abilities = abilities or Card.Abilities()


    def activated(self, cost: game.Action, effect: game.Action, uses_stack: bool=False):
        self.abilities.activated.append(actions.ActivatedAbility(
            cost=cost,
            effect=effect,
            uses_stack=uses_stack
        ))
        return self

    def triggered(self, when: type(game.Action), condition, action: actions.Action):
        when.triggers.append(actions.Trigger(condition=condition, action=action))
        return self

    @property
    def summoning_sick(self):
        return self.permanent and self.permanent.summoning_sick

    @property
    def controller(self):
        return self.zone.owner
            
    def make_permanent(self):
        self.permanent = True

    def del_permanent(self):
        self.permanent = False

    def copy(self):
        return Card(name=self.name,
                    types=self.types,
                    subtypes=self.subtypes,
                    cost=self.cost,
                    abilities=self.abilities,
                    zone=self.zone,
                    permanent=self.permanent,
                    tapped=self.tapped,
                    game_state=self.game_state)

    def __str__(self):
        return f"[{self.name}@{self.zone}]"

    def __repr__(self):
        return str(self)


class Permanent:

    def __init__(self, card: Card, tapped: bool = False):        
        self.card = card
        self.tapped = tapped 
        self.summoning_sick = CardType.Creature in self.card.types 
          
def tap_mana(card,mana) -> actions.ActivatedAbility:
    return actions.ActivatedAbility(
        cost=actions.TapSymbol(card),
        effect=actions.AddMana(mana)
    )

def forest(game_state: game.GameState):
    card = Card( "Forest", (CardType.Land,), game_state=game_state )
    card.activated(
        actions.TapSymbol(card),
        actions.AddMana(game.Mana(green=1))
    )
    return card


def vine_trellis(game_state: game.GameState):
    vt = Card(name="Vine Trellis",
             types=(CardType.Creature,),
             subtypes=("wall",),
             cost=game.Mana(green=1,generic=1),
             game_state=game_state)
    vt.activated(
        actions.TapSymbol(vt),
        actions.AddMana(game.Mana(green=1))
    )
    return vt


def wall_of_omens(game_state: game.GameState):
    wo = Card(
        name="Wall of Omens",
        types=(CardType.Creature,),
        subtypes=("wall",),
        cost = game.Mana(white=1, generic=1),
        game_state=game_state
    )

    wo.triggered(
        when=actions.Play,
        condition=lambda ev: ev.source.uid == wo.uid,
        action=actions.Draw(getters.Controller(wo))
    )

    return wo

def overgrown_battlement(game_state: game.GameState):
    battlement = Card(
        name="Overgrown Battlement",
        types=(CardType.Creature,),
        subtypes=("wall",),
        cost = game.Mana(green=1, generic=1),
        game_state=game_state
    )
    def mana_added(game_state)->game.Mana:
        owner = getters.Controller(battlement)(game_state)
        total = game.Mana(green=len([card
            for card in game_state.in_zone(zone.Field(owner=owner))
            if "wall" in card.subtypes # this is technically wrong -- should be for defenders not walls
        ]))
        return total

    battlement.activated(
        cost=actions.TapSymbol(battlement),
        effect=actions.AddMana(mana_added)
    )
    return battlement

def saruli(game_state) -> Card:
    sl = Card(
        name="Saruli Caretaker",
        types=(CardType.Creature,),
        subtypes=("wall",),
        game_state=game_state
    )
    sl.activated(
        cost=actions.All(
            actions.TapSymbol(sl),
            actions.Tap(lambda card: CardType.Creature in card.types and card.uid != sl.uid)
        ),
        effect=actions.AddMana(game.Mana(green=1))
    )
    return sl