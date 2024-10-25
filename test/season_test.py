from unittest import TestCase
from parameterized import parameterized
import datetime
import random

from sports.season import SeasonSnapshot, Conference, Game

date = datetime.date.today()
games = {
    Game(date, "a", "b", False, (1, 0), None),
    Game(date, "a", "c", False, (0, 1), None),
    Game(date, "a", "d", False, None, 0.25),
    Game(date, "a", "e", False, None, 0.90),
    Game(date, "f", "a", False, None, 0.32),
    Game(date, "g", "a", False, None, 0.87),
    Game(date, "h", "a", False, None, 0.51),
}
season = SeasonSnapshot(2024, {Conference("zzz", {"a", "b", "c", "d", "e", "f", "g", "h"}, None, True, None)}, games)


class SeasonRollTest(TestCase):
    def test_roll_average_wins(self):
        iterations = 100000
        wins = 0
        for _ in range(iterations):
            team = season.roll(random.random).team("a")
            wins += team.wins
        
        expected_average_wins = sum(game.win_probability("a") for game in games)
        actual_average_wins = wins / iterations

        print(expected_average_wins, actual_average_wins)
        self.assertAlmostEqual(actual_average_wins, expected_average_wins, 2)

    def test_roll_force_win(self):
        iterations = 30
        team = season.team("a")
        expected_wins = team.wins + len(team.remaining_games)
        for _ in range(iterations):
            team = season.roll(random.random, force_winners=["a"]).team("a")
            self.assertEqual(team.wins, expected_wins)

    def test_roll_force_lose(self):
        iterations = 30
        team = season.team("a")
        expected_wins = team.wins
        for _ in range(iterations):
            team = season.roll(random.random, force_losers=["a"]).team("a")
            self.assertEqual(team.wins, expected_wins)
    
    def test_roll_force_record(self):
        team = season.team("a")
        starting_wins = team.wins
        remaining_games = len(team.remaining_games)
        for remaining_losses in range(remaining_games + 1):
            expected_wins = starting_wins + remaining_games - remaining_losses
            for _ in range(10):
                actual_wins = season.roll(random.random, force_future_loss_counts={"a": remaining_losses}).team("a").wins
                self.assertEqual(actual_wins, expected_wins)
