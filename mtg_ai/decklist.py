from mtg_ai import actions, game, getters, zone, mana
from mtg_ai.cards import Card, CardType
  
def tap_mana(card,mana) -> actions.ActivatedAbility:
    return actions.ActivatedAbility(
        cost=actions.TapSymbol(card),
        effect=actions.AddMana(mana)
    )

class Forest(Card):
    def __init__(self, game_state):
        super().__init__( "Forest", (CardType.Land,), game_state=game_state)
        self.activated(
            actions.TapSymbol(self),
            actions.AddMana(mana.Mana(green=1))
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
                for card in game_state.in_zone(zone.Field(owner=owner))
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
                for card in game_state.in_zone(zone.Field(owner=owner))
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
            if not isinstance(arc_here.zone, zone.Field):
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
            game_state=game_state
        )
        self.activated(
            cost=actions.All(
                actions.TapSymbol(self),
                actions.Tap(lambda card: CardType.Creature in card.types and card.uid != self.uid)
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
