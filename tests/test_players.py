from mtg_ai.players import TestPlayer


def test_test_player_picks_the_first_choice():
    player = TestPlayer()
    assert player.choose([10, 20, 30], None) == 10
    assert player.choose(["a"], None) == "a"
