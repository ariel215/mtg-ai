import mtg_ai.game as mtg

def test_watcher():
    prev = len(mtg.ZoneTracker.handlers[(mtg.Deck, mtg.Hand)])
    class Checker:
        def __init__(self):
            self.called = False

        def __call__(self, *args):
            self.called = True
    checker = Checker()
    mtg.ZoneTracker.on_draw(checker)
    new = len(mtg.ZoneTracker.handlers[(mtg.Deck, mtg.Hand)])
    assert prev + 1 == new

    card = mtg.Card("Glass")
    card.zone = mtg.Deck()
    card.zone = mtg.Hand()

    assert checker.called