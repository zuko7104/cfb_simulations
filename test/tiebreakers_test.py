# NOTE: This file was used to debug some initial issues with the tiebreakers.
# The tiebreakers have been updated a little since this file was written, so
# some of the tests might not work anymore.

from unittest import TestCase
from parameterized import parameterized
import datetime

from sports.season import TeamName, Game, TeamSnapshot
from sports import tiebreakers

class SortedWithTiesTest(TestCase):
    @parameterized.expand([
        ([1.0, 3.0, 2.0, 3.3, 2.5, 3.6], int, False, [{1.0}, {2.0, 2.5}, {3.0, 3.3, 3.6}]),
        ([1.0, 3.0, 2.0, 3.3, 2.5, 3.6], int, True, [{3.0, 3.3, 3.6}, {2.0, 2.5}, {1.0}]),
        ([1.0, 3.0, 2.0, 3.3, 2.5, 3.6], lambda x: (-1) ** int(x), False, [{1.0, 3.0, 3.3, 3.6}, {2.0, 2.5}]),
        (['tim', 'bob', 'sally', 'jerry', 'kim', 'sam', 'jack'], len, False, [{'tim', 'bob', 'kim', 'sam'}, {'jack'}, {'sally', 'jerry'}]),
    ])
    def test_sorted_with_ties(self, input, key, reverse, expected):
        actual = tiebreakers.sorted_with_ties(input, key=key, reverse=reverse)
        self.assertEqual(actual, expected)

date = datetime.date.today()
games = [
    Game(date, "a", "b", False, (1, 0), None), # a > b (h2h)
    Game(date, "a", "c", False, (1, 0), None), # a > c (h2h)
    Game(date, "a", "d", False, (0, 1), None), # d > a (h2h)
    Game(date, "b", "c", False, (1, 0), None), # b > c (h2h)
    Game(date, "b", "d", False, (1, 0), None), # b > d (h2h)
    Game(date, "b", "e", False, (1, 0), None), # b > e (h2h)
    Game(date, "c", "d", False, (1, 0), None), # c > d (h2h)
    Game(date, "c", "e", False, (1, 0), None), # c > e (h2h)
    Game(date, "c", "f", False, (0, 1), None), 
    Game(date, "d", "e", False, (1, 0), None), # d > e (h2h)
    Game(date, "d", "f", False, (1, 0), None),
    Game(date, "d", "g", False, (1, 0), None),
    Game(date, "e", "f", False, (0, 1), None),
    Game(date, "e", "g", False, (0, 1), None),
    Game(date, "e", "h", False, (0, 1), None),
    Game(date, "f", "g", False, (1, 0), None),
    Game(date, "f", "h", False, (1, 0), None),
    Game(date, "f", "a", False, (1, 0), None),
    Game(date, "g", "h", False, (0, 1), None),
    Game(date, "g", "a", False, (1, 0), None),
    Game(date, "g", "b", False, (0, 1), None),
    Game(date, "h", "a", False, (1, 0), None),
    Game(date, "h", "b", False, (1, 0), None),
    Game(date, "h", "c", False, (1, 0), None),
]
# record:
# 5-1 hf
# 4-2 bd
# 2-4 gca
# 0-6 e

# conference sos:
# 22 ae
# 20 cg
# 15 dh
# 13 bf

t = {
    name: TeamSnapshot(name, list(filter(lambda game: name in game, games)), "zzz") for name in "abcdefgh"
}
all_team_names = set(t.keys())
all_teams = set(t.values())
standings = tiebreakers.sorted_with_ties(t.values(), key=lambda team: team.win_percentage, reverse=True)

for tier in standings:
    print(next(iter(tier)).record, "".join(team.name for team in tier))

class HeadToHeadTest(TestCase):
    @parameterized.expand([
        ("1_on_1", "ab", ["a", "b"]),
        ("2_teams_not_played", "ae", ["ae"]),
        ("3_way", "abc", ["a", "b", "c"]),
        ("3_way_not_all_played", "abe", ["abe"]),
        ("4_way", "bcde", ["b", "c", "d", "e"]),
        ("4_way_with_ties", "abcd", ["ab", "cd"]),
        ("4_way_not_all_played", "abcf", ["abcf"]),
    ])
    def test_head_to_head(self, _, tied, tiers):
        tied_teams = {t[name] for name in tied}
        expected = [{t[name] for name in tier} for tier in tiers]

        actual = tiebreakers.head_to_head(all_team_names, all_teams, tied_teams, standings)
        print("actual:  ", ", ".join("".join(team.name for team in tier) for tier in actual))
        print("expected:", ", ".join("".join(team.name for team in tier) for tier in expected))
        self.assertEqual(actual, expected)

class AgainstHighestCommonOpponenTest(TestCase):
    @parameterized.expand([
        ("tie_4_common", "bd", ["bd"]),
        ("tie_4_common_2", "fh", ["fh"]),
        ("pair", "ef", ["f", "e"]),
        ("triple", "abc", ["bc", "a"]),
    ])
    def test_against_highest_common_opponent(self, _, tied, tiers):
        tied_teams = {t[name] for name in tied}
        expected = [{t[name] for name in tier} for tier in tiers]

        actual = tiebreakers.against_highest_common_opponent(all_team_names, all_teams, tied_teams, standings)
        print("actual:  ", ", ".join("".join(team.name for team in tier) for tier in actual))
        print("expected:", ", ".join("".join(team.name for team in tier) for tier in expected))
        self.assertEqual(actual, expected)

class AgainstAllCommonOpponentsTest(TestCase):
    @parameterized.expand([
        ("pair", "ab", ["b", "a"]),
        ("triple", "def", ["f", "d", "e"]),
        ("triple_tie", "efg", ["f", "eg"]),
    ])
    def test_against_all_common_opponents(self, _, tied, tiers):
        tied_teams = {t[name] for name in tied}
        expected = [{t[name] for name in tier} for tier in tiers]

        actual = tiebreakers.against_all_common_opponents(all_team_names, all_teams, tied_teams, standings)
        print("actual:  ", ", ".join("".join(team.name for team in tier) for tier in actual))
        print("expected:", ", ".join("".join(team.name for team in tier) for tier in expected))
        self.assertEqual(actual, expected)

class StrengthOfConferenceScheduleTest(TestCase):
    @parameterized.expand([
        ("pair", "ab", ["a", "b"]),
        ("pair_tie", "ae", ["ae"]),
        ("triple", "acd", ["a", "c", "d"]),
        ("triple_with_tie", "ace", ["ae", "c"]),
        ("quadruple", "abce", ["ae", "c", "b"]),
    ])
    def test_strength_of_conference_schedule(self, _, tied, tiers):
        tied_teams = {t[name] for name in tied}
        expected = [{t[name] for name in tier} for tier in tiers]

        actual = tiebreakers.strength_of_conference_schedule(all_team_names, all_teams, tied_teams, standings)
        print("actual:  ", ", ".join("".join(team.name for team in tier) for tier in actual))
        print("expected:", ", ".join("".join(team.name for team in tier) for tier in expected))
        self.assertEqual(actual, expected)

class TotalWinsTest(TestCase):
    @parameterized.expand([
        ("pair", "ab", ["b", "a"]),
        ("pair_tie", "ag", ["ag"]),
        ("triple", "adf", ["f", "d", "a"]),
        ("triple_with_tie", "ace", ["ac", "e"]),
        ("quadruple", "abce", ["b", "ac", "e"]),
    ])
    def test_total_wins(self, _, tied, tiers):
        tied_teams = {t[name] for name in tied}
        expected = [{t[name] for name in tier} for tier in tiers]

        actual = tiebreakers.total_wins_in_12_game_season(all_team_names, all_teams, tied_teams, standings)
        print("actual:  ", ", ".join("".join(team.name for team in tier) for tier in actual))
        print("expected:", ", ".join("".join(team.name for team in tier) for tier in expected))
        self.assertEqual(actual, expected)
