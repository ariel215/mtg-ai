from mtg_ai import game, abilities

def forest(game_state: game.GameState):
    card = abilities.Card(
                          "Forest",
                     (abilities.CardType.Land,),
                     game_state=game_state
                     )
    card.set_abilities(
                     activated=[
                         abilities.ActivatedAbility(
                             costs=[abilities.TapSymbol(card)],
                             effects=[abilities.AddMana(game.Mana(green=1))]
                         )]
                     )
    return card

