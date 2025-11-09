import mtg_ai.game as mtg
import mtg_ai.cards as cards


def test_watcher():
    prev = len(mtg.ChangeTracker.changes[(mtg.Deck, mtg.Hand)])
    class Checker:
        def __init__(self):
            self.called = False

        def __call__(self, *args):
            self.called = True
    checker = Checker()
    mtg.ChangeTracker.on_draw(checker)
    new = len(mtg.ChangeTracker.changes[(mtg.Deck, mtg.Hand)])
    assert prev + 1 == new

    card = mtg.Card("Glass")
    card.zone = mtg.Deck()
    card.zone = mtg.Hand()

    assert checker.called


def test_deck():
    deck = [[mtg.Card(name) for name in 'ABCDE']]
    game = mtg.Game(decks=deck, track_history=True)
    assert game.root.players == [0]
    
    deck_zone = mtg.Deck(owner=0)
    new_deck = game.root.in_zone(deck_zone)
    assert len(new_deck) == len(deck[0])

def test_history():
    deck = [mtg.Card(name) for name in ('a','b','c','d','e')]
    game = mtg.Game(decks=[deck], track_history=True)
    for i in range(3):
        game.draw(0)
        assert len(game.history) == i+1
        assert len(game.root.in_zone(mtg.Deck(owner=0))) == len(deck) - (i+1)

def test_play():
    forest = cards.forest()
    game = mtg.Game([[forest]], track_history=True)
    game.play(forest)
    assert forest.permanent is not None
