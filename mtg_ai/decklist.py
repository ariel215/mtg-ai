from mtg_ai import actions, game, getters, zone 
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
            actions.AddMana(game.Mana(green=1))
        )

class VineTrellis(Card):
    def __init__(self, game_state):
        super().__init__(     
            name="Vine Trellis",
            types=(CardType.Creature,),
            subtypes=("wall",),
            cost=game.Mana(green=1,generic=1),
            game_state=game_state)

        self.activated(
            actions.TapSymbol(self),
            actions.AddMana(game.Mana(green=1))
        )


class WallOfOmens(Card):
    def __init__(self, game_state):
        super().__init__(
            name="Wall of Omens",
            types=(CardType.Creature,),
            subtypes=("wall",),
            cost = game.Mana(white=1, generic=1),
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
        cost = game.Mana(green=1, generic=1),
        game_state=game_state
        )
        def mana_added(game_state)->game.Mana:
            owner = getters.Controller(self)(game_state)
            total = game.Mana(green=len([card
                for card in game_state.in_zone(zone.Field(owner=owner))
                if "wall" in card.subtypes # this is technically wrong -- should be for defenders not walls
            ]))
            return total

        self.activated(
            cost=actions.TapSymbol(self),
            effect=actions.AddMana(mana_added)
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
            effect=actions.AddMana(game.Mana(green=1))
        )
