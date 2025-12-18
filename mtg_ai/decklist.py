from mtg_ai import actions, game, getters, zones, mana
from mtg_ai.cards import Card, CardType

# -------------------------------------------------

# Cards in walls: 

# [x] Caretaker
# [x] Caryatid
# [?] Roots
# [x] Battlement
# [x] Axebane
# [x] Blossoms
# [x] Arcades
# [x] Recruiter
# [x] TrophyMage
# [x] Staff
# [x] Company

# [x] Forest
# [x] Plains
# [x] Island
# [x] TempleGarden
# [x] BreedingPool
# HallowedFountain
# WindsweptHeath
# Westvale
# Wildwoods
# LumberingFalls


def tap_mana(card,mana) -> actions.ActivatedAbility:
    return actions.ActivatedAbility(
        cost=actions.TapSymbol(card),
        effect=actions.AddMana(mana)
    )

class Forest(Card):
    def __init__(self, game_state):
        super().__init__( "Forest", 
                         types=(CardType.Land,),
                         subtypes=("forest",),
                         game_state=game_state)
        self.activated(
            actions.TapSymbol(self),
            actions.AddMana(mana.Mana(green=1))
        )

class Plains(Card):
    def __init__(self, game_state):
        super().__init__( "Plains",
            types=(CardType.Land,), 
            subtypes=("plains",),
            game_state=game_state)
        self.activated(
            actions.TapSymbol(self),
            actions.AddMana(mana.Mana(white=1))
        )

class Island(Card):
    def __init__(self, game_state):
        super().__init__( "Island", types=(CardType.Land,), 
        subtypes=("island",),
        game_state=game_state)
        self.activated(
            actions.TapSymbol(self),
            actions.AddMana(mana.Mana(blue=1))
        )


class TempleGarden(Card):
    def __init__(self, game_state):
        super().__init__( "Temple Garden", types=(CardType.Land,), 
        subtypes=("forest","plains"),game_state=game_state)
        self.activated(
            actions.TapSymbol(self),
            actions.AddMana(mana.Mana(white=1))
        ).activated(
            actions.TapSymbol(self),
            actions.AddMana(mana.Mana(green=1))
        )

class BreedingPool(Card):
    def __init__(self, game_state):
        super().__init__( "Breeding Pool", types=(CardType.Land,),
        subtypes=("forest","island"), game_state=game_state)
        self.activated(
            actions.TapSymbol(self),
            actions.AddMana(mana.Mana(blue=1))
        ).activated(
            actions.TapSymbol(self),
            actions.AddMana(mana.Mana(green=1))
        )

class WindsweptHeath(Card):
    def __init__(self, game_state):
        super().__init__("Windswept Heath", types=(CardType.Land,),
        game_state=game_state)
        self.activated(
            actions.TapSymbol(self) + actions.Sacrifice(self), #todo: pay 1 life
            actions.Search(
                getters.FromZone(getters.Zone(zones.Deck(),getters.Controller(self))),
                lambda cards: [[c] for c in cards if "forest" in c.subtypes],
                actions.Play(),
                actions.Shuffle()
            )
        )


class VineTrellis(Card):
    def __init__(self, game_state):
        super().__init__(     
            name="Vine Trellis",
            types=(CardType.Creature,),
            subtypes=("wall",),
            cost=mana.Mana(green=1,generic=1),
            game_state=game_state)

        self.activated(
            actions.TapSymbol(self),
            actions.AddMana(mana.Mana(green=1))
        )


class WallOfRoots(Card):
    def __init__(self, game_state):
        super().__init__(     
            name="Wall of Roots",
            types=(CardType.Creature,),
            subtypes=("wall",),
            cost=mana.Mana(green=1,generic=1),
            game_state=game_state)
        # Todo: make this do the right thing
        self.activated(
            actions.Tap(lambda card: card.uid == self.uid) + actions.AddCounter(self,"-0/-1", zones.Field()), 
            actions.AddMana(mana.Mana(green=1))
        )

class WallOfOmens(Card):
    def __init__(self, game_state):
        super().__init__(
            name="Wall of Omens",
            types=(CardType.Creature,),
            subtypes=("wall",),
            cost = mana.Mana(white=1, generic=1),
            game_state=game_state
        )

        self.triggered(
            when=actions.Play,
            condition=lambda ev: ev.source.uid == self.uid,
            action=actions.Draw(getters.Controller(self))
        )

class Battlement(Card):
    def __init__(self, game_state):
        super().__init__(
        name="Overgrown Battlement",
        types=(CardType.Creature,),
        subtypes=("wall",),
        cost = mana.Mana(green=1, generic=1),
        game_state=game_state
        )
        def mana_added(game_state)->mana.Mana:
            owner = getters.Controller(self)(game_state)
            total = mana.Mana(green=len([card
                for card in game_state.in_zone(zones.Field(owner=owner))
                if "wall" in card.subtypes # this is technically wrong -- should be for defenders not walls
            ]))
            return total

        self.activated(
            cost=actions.TapSymbol(self),
            effect=actions.AddMana(mana_added)
        )

class Axebane(Card):
    def __init__(self, game_state):
        super().__init__(
            name="Axebane Guardian",
            types=(CardType.Creature,),
            subtypes=("wall",),
            cost = mana.Mana(green=1, generic=2),
            game_state=game_state
        )
        def mana_added(game_state: game.GameState)->mana.Mana:
            owner = getters.Controller(self)(game_state)
            total = mana.Mana(gold=len([card
                for card in game_state.in_zone(zones.Field(owner=owner))
                if "wall" in card.subtypes # this is technically wrong -- should be for defenders not walls
            ]))
            return total

        self.activated(
            cost=actions.TapSymbol(self),
            effect=actions.AddMana(mana_added)
        )

class Arcades(Card):

    def __init__(self, game_state: game.GameState) -> Card: 
        super().__init__(
            name="Arcades the Strategist",
            types=(CardType.Creature,),
            subtypes=("dragon", ),
            cost=mana.Mana(white=1,blue=1, green=1,generic=1),
            game_state=game_state
        )
        def arc_triggers_if(event):
            gs = event.game_state
            arc_here = gs.get(self)
            if not isinstance(arc_here.zone, zones.Field):
                return False
            if arc_here.zone.owner != event.source.zone.owner:
                return False
            return "wall" in event.source.subtypes
        
        self.triggered(
            when=actions.Play,
            condition=arc_triggers_if,
            action=actions.Draw(player=getters.Controller(self))
        )


class Saruli(Card):
    def __init__(self, game_state):
        super().__init__(
            name="Saruli Caretaker",
            types=(CardType.Creature,),
            subtypes=("wall",),
            cost=mana.Mana(green=1),
            game_state=game_state
        )
        self.activated(
            cost=game.And(
                actions.TapSymbol(self),
                actions.Tap(lambda card: (
                    zones.Field().contains(card) 
                    and CardType.Creature in card.types 
                    and card.uid != self.uid)
                )
            ),
            effect=actions.AddMana(mana.Mana(green=1))
        )

class SylvanCaryatid(Card):
    def __init__(self, game_state: game.GameState):
        super().__init__(name="Sylvan Caryatid",
                types=(CardType.Creature,),
                subtypes=("wall",),
                cost=mana.Mana(green=1,generic=1),
                game_state=game_state)
        self.activated(
            actions.TapSymbol(self),
            actions.AddMana(mana.Mana(gold=1))
        )

class CollectedCompany(Card):
    def __init__(self,game_state: game.GameState) -> Card:
        super().__init__(
            name="Collected Company",
            game_state=game_state,
            cost=mana.Mana(green=1, generic=3),
            types=(CardType.Instant,)
        )
        self.with_effect(
            actions.Search(
                search_in=getters.FromZone(getters.Zone(zones.Deck(), getters.Controller(self)), top=6),
                search_for=getters.UpTo(2,lambda card: CardType.Creature in card.types and card.cost.mana_value <= 3),
                to_found=actions.Play(),
                to_rest=actions.MoveTo(getters.Zone(zones.Deck(),getters.Controller(self),zones.BOTTOM))
            )
        )

class Duskwatch(Card):
    def __init__(self, game_state: game.GameState):
        super().__init__(
            "Duskwatch Recruiter",
            cost=mana.Mana(green=1,generic=1),
            types=(CardType.Creature,),
            game_state=game_state
        )

        self.activated(
            cost=actions.PayMana(mana=mana.Mana(generic=2,green=1)),
            effect=actions.Search(
                search_in=getters.FromZone(getters.Zone(zones.Deck(), getters.Controller(self)), top=3),
                search_for=getters.UpTo(1,lambda card: CardType.Creature in card.types),
                to_found=actions.MoveTo(getters.Zone(zones.Hand(),getters.Controller(self))),
                to_rest=actions.MoveTo(getters.Zone(zones.Deck(),getters.Controller(self),zones.BOTTOM))
            ),
        )

class TrophyMage(Card):
    def __init__(self, game_state: game.GameState):
        super().__init__(
            "Trophy Mage",
            cost=mana.Mana(blue=1,generic=2),
            types=(CardType.Creature,),
            game_state=game_state
        )

        self.triggered(
            actions.Play,
            condition=lambda ev: ev.source.uid == self.uid,
            action=actions.Search(
                search_in=getters.FromZone(getters.Zone(zones.Deck(),getters.Controller(self))),
                search_for=getters.UpTo(1,lambda card: CardType.Artifact in card.types and card.mana_value == 3),
                to_found=actions.MoveTo(getters.Zone(zones.Hand(),getters.Controller(self))),
                to_rest=actions.MoveTo(getters.Zone(zones.Deck(),getters.Controller(self),zones.BOTTOM))
            )
        )

class Staff(Card):
    def __init__(self, game_state):
        super().__init__(
            "Staff of Domination",
            mana.Mana(generic=3),
            types=(CardType.Artifact,),
            game_state=game_state
        )
        # technically this card can do a bunch of stuff,
        # but the only thing we're interested in right now is 
        # "does it win the game" and we're going to hack that on separately


def build_deck(card_types, game_state, player):
    cards = [ty(game_state) for ty in card_types]
    for card in cards: 
        card.zone = zones.Deck(player)
    return cards
