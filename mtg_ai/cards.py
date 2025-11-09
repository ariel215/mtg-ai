from mtg_ai import game, abilities

def forest():
    card = game.Card("Forest",
                     (game.CardType.Land,)
                     )
    card.set_abilities(
                     activated=[
                         abilities.ActivatedAbility(
                             costs=[abilities.TapSymbol(card)],
                             effects=[abilities.AddMana(game.Mana(green=1))]
                         )]
                     )
    return card

