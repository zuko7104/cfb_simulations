from sports.season import Standing, TeamName, TeamNames, TeamPair, SeasonSnapshot, ConferenceSnapshot, TeamSnapshot
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, TypeAlias


@dataclass
class BasicTeamSeasonOutcomes:
    total_seasons: int = 0
    made_ccg: int = 0
    standing: dict[Standing, int] = field(default_factory=lambda: defaultdict(lambda: 0))
    ccg_participants: dict[TeamPair, int] = field(default_factory=lambda: defaultdict(lambda: 0))

    def __iadd__(self, result: tuple[TeamSnapshot, Standing, TeamPair]) -> "BasicTeamSeasonOutcomes":
        team, standing, ccg_teams = result
        self.total_seasons += 1
        self.standing[standing] += 1
        self.ccg_participants[ccg_teams] += 1
        if team.name in ccg_teams:
            self.made_ccg += 1
        return self


@dataclass
class TeamSeasonOutcomes:
    total_seasons: int = 0
    win_counts: dict[int, int] = field(default_factory=lambda: defaultdict(lambda: 0))
    win_counts_in_ccg: dict[int, int] = field(default_factory=lambda: defaultdict(lambda: 0))
    made_ccg: int = 0
    standing: dict[Standing, int] = field(default_factory=lambda: defaultdict(lambda: 0))
    lost_to: dict[TeamNames, BasicTeamSeasonOutcomes] = field(default_factory=lambda: defaultdict(lambda: BasicTeamSeasonOutcomes()))

    def __iadd__(self, result: tuple[ConferenceSnapshot, TeamSnapshot, TeamPair]) -> "TeamSeasonOutcomes":
        conference, team, ccg_teams = result
        standing = conference.standing(team.name)
        lost_to: TeamNames = tuple(sorted(team.losses_against))

        self.total_seasons += 1
        self.standing[standing] += 1
        self.win_counts[team.wins] += 1
        if team.name in ccg_teams:
            self.made_ccg += 1
            self.win_counts_in_ccg[team.wins] += 1
        self.lost_to[lost_to] += (team, standing, ccg_teams)

        return self


@dataclass
class ConferenceSeasonOutcomes:
    total_seasons: int = 0
    teams: dict[TeamName, TeamSeasonOutcomes] = field(default_factory=lambda: defaultdict(lambda: TeamSeasonOutcomes()))
    ccg_participants: dict[TeamPair, int] = field(default_factory=lambda: defaultdict(lambda: 0))
    @property
    def team_names(self) -> set[TeamName]:
        return set(self.teams.keys())

    def __iadd__(self, result: tuple[ConferenceSnapshot, TeamPair]) -> "ConferenceSeasonOutcomes":
        conference, ccg_teams = result
        self.total_seasons += 1
        self.ccg_participants[ccg_teams] += 1
        for team in conference.teams:
            self.teams[team.name] += (conference, team, ccg_teams)
        return self
    
    def prob_in_ccg(self, team: TeamName) -> float:
        return sum(count for ccg_teams, count in self.ccg_participants.items() if team in ccg_teams) / (self.total_seasons or 0)

    def prob_in_ccg_given_specific_losses(self, team: TeamName, ccg_target: TeamName = ...) -> dict[TeamNames, float]:
        if ccg_target is ...:
            ccg_target = team
        team_outcomes = self.teams[team]
        result = {}
        for losses, outcomes in team_outcomes.lost_to.items():
            prob = sum(count for ccg_teams, count in outcomes.ccg_participants.items() if ccg_target in ccg_teams) / outcomes.total_seasons
            if prob > 0:
                result[losses] = prob
        return result

    def prob_in_ccg_given_total_losses(self, team: TeamName, ccg_target: TeamName = ...) -> dict[int, float]:
        if ccg_target is ...:
            ccg_target = team
        team_outcomes = self.teams[team]
        ccg_made_counts: dict[int, int] = defaultdict(lambda: 0)
        losses_counts: dict[int, int] = defaultdict(lambda: 0)
        for losses, outcomes in team_outcomes.lost_to.items():
            count = sum(count for ccg_teams, count in outcomes.ccg_participants.items() if ccg_target in ccg_teams)
            ccg_made_counts[len(losses)] += count
            losses_counts[len(losses)] += outcomes.total_seasons
        return {total_losses: count / losses_counts[total_losses] for total_losses, count in ccg_made_counts.items()}
    
    def prob_final_win_count(self, team: TeamName) -> dict[int, float]:
        team_outcomes = self.teams[team]
        losses_counts: dict[int, int] = defaultdict(lambda: 0)
        for losses, outcomes in team_outcomes.lost_to.items():
            losses_counts[len(losses)] += outcomes.total_seasons
        return {12 - losses: count / self.total_seasons for losses, count in losses_counts.items()}


ScenarioCondition: TypeAlias = Callable[[SeasonSnapshot], bool]


def win_exactly(team: TeamName, wins: int) -> ScenarioCondition:
    return lambda roll: roll.team(team).wins == wins


def win_at_least(team: TeamName, wins: int) -> ScenarioCondition:
    return lambda roll: roll.team(team).wins >= wins


def win_out(season: SeasonSnapshot, team: TeamName) -> ScenarioCondition:
    original_team = season.team(team)
    loss_count = original_team.losses
    return lambda roll: roll.team(team).losses == loss_count


def beat(winner: TeamName, loser: TeamName) -> ScenarioCondition:
    return lambda roll: loser in roll.team(winner).wins_against


def win_out_except_possibly(season: SeasonSnapshot, team: TeamName, possible_losses: list[TeamName]) -> Callable[[SeasonSnapshot], bool]:
    original_team = season.team(team)
    allowed_losses = set(possible_losses) | original_team.losses_against
    return lambda roll: roll.team(team).losses_against.issubset(allowed_losses)


@dataclass
class ScenarioOutcomes:
    description: str
    conditions: list[Callable[[SeasonSnapshot], bool]]
    total_seasons: int = 0
    ccg_participants: dict[tuple[TeamPair], int] = field(default_factory=lambda: defaultdict(lambda: 0))

    def __contains__(self, rolled_season: SeasonSnapshot) -> bool:
        return all(condition(rolled_season) for condition in self.conditions)
    
    def __iadd__(self, result: tuple[SeasonSnapshot, tuple[TeamPair]]) -> "ScenarioOutcomes":
        season, ccg_teams = result
        if season in self:
            self.total_seasons += 1
            self.ccg_participants[ccg_teams] += 1
        return self

    def prob_in_ccg(self, team: TeamName):
        return sum(count for ccg_teams, count in self.ccg_participants.items() if any(team in ccg_matchup for ccg_matchup in ccg_teams)) / (self.total_seasons or 1)


@dataclass
class WeekOutcomes:
    games: list[TeamPair]
    total_count: int = 0
    permutations: dict[TeamNames, dict[TeamPair, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(lambda: 0)))

    def __iadd__(self, conference: ConferenceSnapshot) -> "WeekOutcomes":
        winners = []
        for team in conference.teams:
            for seek_game in self.games:
                if seek_game[0] == team.name:
                    for game in team.games:
                        if seek_game[1] in game:
                            winner = game.winner
                            if not winner:
                                raise ValueError(f"{seek_game} has no winner")
                            winners.append(winner)
        
        if len(winners) != len(self.games):
            raise ValueError(f"Not all of {self.games} found")
        
        self.permutations[tuple(sorted(winners))][conference.championship_game_participants] += 1
        self.total_count += 1

        return self

    def prob_in_ccg_given_winners(self, winners: set[TeamName], ccg_target: TeamName) -> float:
        count = 0
        in_ccg = 0
        for all_winners, results in self.permutations.items():
            if winners.issubset(all_winners):
                count += sum(results.values())
                in_ccg += sum(c for ccg_teams, c in results.items() if ccg_target in ccg_teams)
        return in_ccg / (count or 1)
    
    def prob_of_winners(self, winners: set[TeamNames]) -> float:
        count = 0
        for all_winners, results in self.permutations.items():
            if winners.issubset(all_winners):
                count += sum(results.values())
        return count / self.total_count
