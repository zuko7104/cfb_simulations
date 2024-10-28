from sports.season import TeamName, SeasonSnapshot, ConferenceName,  TeamPair
from sports.outcomes import ConferenceSeasonOutcomes, ScenarioOutcomes, WeekOutcomes
import random
import os
import datetime


class Simulator:
    def __init__(self, season: SeasonSnapshot, scenarios: list[ScenarioOutcomes] = [], week_end: datetime.date = ...):
        today = datetime.date.today()
        if week_end is ...:
            week_end = today + datetime.timedelta(days=7)
            while week_end.weekday() != 6: # 6 is Sunday
                week_end = week_end - datetime.timedelta(days=1)
        
        self.__season = season

        week_outcomes: dict[ConferenceName, WeekOutcomes] = {}
        for conference in season.conferences:
            week_games: list[TeamPair] = []
            for game in self.__season.games:
                if game.date >= today and game.date <= week_end:
                    if game.team_a in conference.teams or game.team_b in conference.teams:
                        week_games.append((game.team_a, game.team_b))
            week_outcomes[conference.name] = WeekOutcomes(week_games)
        self.week_outcomes = week_outcomes

        self.scenarios = scenarios
        self.conference_outcomes = {conference.name: ConferenceSeasonOutcomes() for conference in season.conferences}

    def simulate(self, iterations: int):
        print(f"Running {iterations} simulations")
        for i in range(iterations):
            if i % 1000 == 0:
                print("completed", i)
            rolled_season = self.__season.roll(random.random)
            ccg_teams: dict[ConferenceName, TeamPair] = {}
            for conference in rolled_season.conferences:
                rolled_conference = rolled_season.conference(conference.name)
                rolled_ccg_teams = tuple(sorted(rolled_conference.championship_game_participants))
                ccg_teams[conference.name] = rolled_ccg_teams

                self.conference_outcomes[conference.name] += (rolled_conference, rolled_ccg_teams)
                self.week_outcomes[conference.name] += rolled_conference

            ccg_games = tuple(item[1] for item in sorted(ccg_teams.items(), key=lambda item: item[0]))
            for scenario in self.scenarios:
                scenario += (rolled_season, ccg_games)
