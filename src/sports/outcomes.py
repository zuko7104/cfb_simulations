from sports.season import Standing, TeamName, TeamNames, TeamPair, SeasonSnapshot, ConferenceSnapshot, TeamSnapshot, Game, UniformRoller
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, TypeAlias, Iterable, Any


def _zero():
    return 0


def _default_zero():
    return defaultdict(_zero)


def _default_default_zero():
    return defaultdict(_default_zero)


@dataclass
class BasicTeamSeasonOutcomes:
    total_seasons: int = 0
    made_ccg: int = 0
    standing: dict[Standing, int] = field(default_factory=_default_zero)
    ccg_participants: dict[TeamPair, int] = field(default_factory=_default_zero)

    def __iadd__(self, result: tuple[TeamSnapshot, Standing, TeamPair]) -> "BasicTeamSeasonOutcomes":
        team, standing, ccg_teams = result
        self.total_seasons += 1
        self.standing[standing] += 1
        self.ccg_participants[ccg_teams] += 1
        if team.name in ccg_teams:
            self.made_ccg += 1
        return self

    def __ior__(self, other: "BasicTeamSeasonOutcomes") -> "BasicTeamSeasonOutcomes":
        self.total_seasons += other.total_seasons
        self.made_ccg += other.made_ccg
        for s, count in other.standing.items():
            self.standing[s] += count
        for matchup, count in other.ccg_participants.items():
            self.ccg_participants[matchup] += count
        return self


def _basic_team_season_outcomes():
    return BasicTeamSeasonOutcomes()


def _default_basic_team_season_outcomes():
    return defaultdict(_basic_team_season_outcomes)


@dataclass
class TeamSeasonOutcomes:
    total_seasons: int = 0
    win_counts: dict[int, int] = field(default_factory=_default_zero)
    win_counts_in_ccg: dict[int, int] = field(default_factory=_default_zero)
    made_ccg: int = 0
    standing: dict[Standing, int] = field(default_factory=_default_zero)
    lost_to: dict[TeamNames, BasicTeamSeasonOutcomes] = field(default_factory=_default_basic_team_season_outcomes)

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

    def __ior__(self, other: "TeamSeasonOutcomes") -> "TeamSeasonOutcomes":
        self.total_seasons += other.total_seasons
        for wins, count in other.win_counts.items():
            self.win_counts[wins] += count
        for wins, count in other.win_counts_in_ccg.items():
            self.win_counts_in_ccg[wins] += count
        self.made_ccg += other.made_ccg
        for s, count in other.standing.items():
            self.standing[s] += count
        for lost, outcomes in other.lost_to.items():
            self.lost_to[lost] |= outcomes
        return self


def _team_season_outcomes():
    return TeamSeasonOutcomes()


def _default_team_season_outcomes():
    return defaultdict(_team_season_outcomes)


@dataclass
class ConferenceSeasonOutcomes:
    total_seasons: int = 0
    teams: dict[TeamName, TeamSeasonOutcomes] = field(default_factory=_default_team_season_outcomes)
    ccg_participants: dict[TeamPair, int] = field(default_factory=_default_zero)
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
        ccg_made_counts: dict[int, int] = defaultdict(_zero)
        losses_counts: dict[int, int] = defaultdict(_zero)
        for losses, outcomes in team_outcomes.lost_to.items():
            count = sum(count for ccg_teams, count in outcomes.ccg_participants.items() if ccg_target in ccg_teams)
            ccg_made_counts[len(losses)] += count
            losses_counts[len(losses)] += outcomes.total_seasons
        return {total_losses: count / losses_counts[total_losses] for total_losses, count in ccg_made_counts.items()}

    def prob_final_win_count(self, team: TeamName) -> dict[int, float]:
        team_outcomes = self.teams[team]
        losses_counts: dict[int, int] = defaultdict(_zero)
        for losses, outcomes in team_outcomes.lost_to.items():
            losses_counts[len(losses)] += outcomes.total_seasons
        return {12 - losses: count / self.total_seasons for losses, count in losses_counts.items()}

    def __ior__(self, other: "ConferenceSeasonOutcomes") -> "ConferenceSeasonOutcomes":
        self.total_seasons += other.total_seasons
        for team, outcomes in other.teams.items():
            self.teams[team] |= outcomes
        for matchup, count in other.ccg_participants.items():
            self.ccg_participants[matchup] += count
        return self


def _short_name(team: TeamName) -> str:
    short_names = {"Arizona": "AZ", "Arizona St": "ASU", "BYU": "BYU", "Baylor": "BAY", "Colorado": "CO", "UCF": "UCF", "Cincinnati": "Cinci", "Houston": "UH", "Iowa St": "ISU", "Kansas St": "KSU", "Kansas": "KS", "Oklahoma State": "OKST", "TCU": "TCU", "Texas Tech": "TTech", "Utah": "Utah", "West Virginia": "WVU"}
    return short_names.get(team, team)


ScenarioConditionCallable: TypeAlias = Callable[[SeasonSnapshot], bool]
ScenarioForcer: TypeAlias = Callable[[UniformRoller, SeasonSnapshot], Iterable[Game]]

class ScenarioCondition:
    def __init__(self, condition: ScenarioConditionCallable, forcer: ScenarioForcer, args: list[Any], description: str, probability: float, probability_factors: dict[TeamPair, float]):
        self.__description = description
        self.__condition = condition
        self.__forcer = forcer
        self.__args = args
        self.__probability = probability
        self.__probability_factors = probability_factors

    def __call__(self, roller: UniformRoller, season: SeasonSnapshot) -> Iterable[Game]:
        return self.__forcer(roller, season, *self.__args)

    def __contains__(self, season: SeasonSnapshot) -> bool:
        return self.__condition(season, *self.__args)

    def __str__(self) -> str:
        return self.__description

    @property
    def probability(self) -> float:
        return self.__probability

    @property
    def probability_factors(self) -> dict[TeamPair, float]:
        return self.__probability_factors


def _win_exactly_condition(season: SeasonSnapshot, team_name: TeamName, win_count: int, wins: set[TeamName] = set(), losses: set[TeamName] = set()) -> bool:
    team = season.team(team_name)
    if wins or losses:
        return team.wins == win_count and team.wins_against.issuperset(wins) and team.losses_against.issuperset(losses)
    else:
        return team.wins == win_count


def _win_exactly_forcer(roller: UniformRoller, season: SeasonSnapshot, team_name: TeamName, win_count: int, wins: set[TeamName] = set(), losses: set[TeamName] = set()) -> Iterable[Game]:
    return season.team(team_name).roll(roller, force_total_wins=win_count, force_wins_against=wins, force_losses_against=losses).games


def win_exactly(season: SeasonSnapshot, team_name: TeamName, win_count: int, wins: set[TeamName] = set(), losses: set[TeamName] = set(), description: str | None = None):
    if not description:
        description = f"{_short_name(team_name)} {win_count}-{12-win_count}"
        if wins:
            description += f", beat {', '.join(map(_short_name, wins))}"
        if losses:
            description += f", lost to {', '.join(map(_short_name, losses))}"
    return ScenarioCondition(
        _win_exactly_condition, _win_exactly_forcer, [team_name, win_count, wins, losses],
        # description or f"{_short_name(team_name)} {win_count}-{12-win_count}\n({('beat ' + ', '.join(map(_short_name, wins))) if wins else ''}{'; ' if wins and losses else ''}{('lost to ' + ', '.join(map(_short_name, losses))) if losses else ''})",
        description,
        *season.team(team_name).probability_of(win_count, wins, losses),
    )


# def win_at_least(team: TeamName, wins: int) -> ScenarioCondition:
#     return ScenarioCondition(
#         lambda season: season.team(team).wins >= wins,
#         lambda roller, season: season.team(team).roll(roller, force_min_wins=wins).games,
#         f"{_short_name(team)} {wins}-{12-wins} or better"
#     )


def _win_at_most_condition(season: SeasonSnapshot, team_name: TeamName, max_win_count: int, wins: set[TeamName] = set(), losses: set[TeamName] = set()) -> bool:
    team = season.team(team_name)
    if wins or losses:
        return team.wins <= max_win_count and team.wins_against.issuperset(wins) and team.losses_against.issuperset(losses)
    else:
        return team.wins <= max_win_count


def _win_at_most_forcer(roller: UniformRoller, season: SeasonSnapshot, team_name: TeamName, max_win_count: int, wins: set[TeamName] = set(), losses: set[TeamName] = set()) -> bool:
    return season.team(team_name).roll(roller, force_max_wins=max_win_count, force_wins_against=wins, force_losses_against=losses).games


def win_at_most(season: SeasonSnapshot, team_name: TeamName, max_win_count: int, wins: set[TeamName] = set(), losses: set[TeamName] = set()) -> ScenarioCondition:
    description = f"{_short_name(team_name)} {max_win_count}-{12-max_win_count} or worse"
    if wins:
        description += f", beat {', '.join(map(_short_name, wins))}"
    if losses:
        description += f", lost to {', '.join(map(_short_name, losses))}"
    return ScenarioCondition(
        _win_at_most_condition,
        _win_at_most_forcer,
        [team_name, max_win_count, wins, losses],
        description,
        *season.team(team_name).probability_of(max_wins = max_win_count, wins_against=wins, losses_against=losses)
    )


def win_out(season: SeasonSnapshot, team: TeamName) -> ScenarioCondition:
    original_team = season.team(team)
    total_wins = original_team.wins + len(original_team.remaining_games)
    return win_exactly(season, team, total_wins)


def _beat_condition(season: SeasonSnapshot, winner: TeamName, loser: TeamName) -> bool:
    return loser in season.team(winner).wins_against


def _beat_forcer(roller: UniformRoller, season: SeasonSnapshot, winner: TeamName, loser: TeamName) -> Iterable[Game]:
    del roller
    return {season.team(winner).game_against(loser).force_outcome_if_not_over(winner, True)}


def beat(season: SeasonSnapshot, winner: TeamName, loser: TeamName) -> ScenarioCondition:
    probability = season.team(winner).game_against(loser).win_probability(winner)
    return ScenarioCondition(
        _beat_condition, _beat_forcer, [winner, loser],
        f"{_short_name(winner)} beat {_short_name(loser)}",
        probability,
        probability_factors={tuple(sorted([winner, loser])): probability}
    )


def _win_out_except_possibly_condition(season: SeasonSnapshot, team: TeamName, allowed_losses: set[TeamName]) -> bool:
    return season.team(team).losses_against.issubset(allowed_losses)


def _win_out_except_possibly_forcer(roller: UniformRoller, season: SeasonSnapshot, team: TeamName, allowed_losses: set[TeamName]) -> Iterable[Game]:
    return {game.force_outcome_if_not_over(team, True) if game.opponent(team) not in allowed_losses else game.roll(lambda p: roller() <= p) for game in season.team(team).games},


def win_out_except_possibly(season: SeasonSnapshot, team_name: TeamName, possible_losses: list[TeamName]) -> ScenarioCondition:
    team = season.team(team_name)
    allowed_losses = set(possible_losses) | team.losses_against
    prob = 1.0
    factors = {}
    for game in team.remaining_games:
        opponent = game.opponent(team_name)
        if opponent not in possible_losses:
            p = game.win_probability(team_name)
            prob *= p
            factors[tuple(sorted([team_name, opponent]))] = p
    return ScenarioCondition(
        _win_out_except_possibly_condition, _win_out_except_possibly_forcer, [team_name, allowed_losses],
        f"{_short_name(team_name)} only possible {'losses' if len(possible_losses) > 1 else 'loss'}: {', '.join(map(_short_name,possible_losses))}",
        prob,
        factors
    )


def win_out_except(season: SeasonSnapshot, team_name: TeamName, losses: set[TeamName]) -> ScenarioCondition:
    team = season.team(team_name)
    # expected_losses = set(losses) | original_team.losses_against
    win_count = team.wins + len(team.remaining_games) - len(losses)
    return win_exactly(season, team_name, win_count, losses=losses, description=f"{_short_name(team_name)} lose to {', '.join(map(_short_name, losses))}")
    # return ScenarioCondition(
    #     _win_exactly_with_condition, _win_exactly_with_forcer, [team_name, win_count, set(), set(losses)],
        # lambda season: season.team(team_name).losses_against == expected_losses,
        # lambda _, season: {game.force_outcome_if_not_over(team_name, game.opponent(team_name) not in losses) for game in season.team(team_name).games},
        # f"{_short_name(team_name)} lose to {', '.join(map(_short_name, losses))}"
    # )


def _any_outcome_condition(season: SeasonSnapshot) -> bool:
    del season
    return True


def _any_outcome_forcer(roller: UniformRoller, season: SeasonSnapshot) -> set[Game]:
    del roller, season
    return set()


def any_outcome() -> ScenarioCondition:
    return ScenarioCondition(_any_outcome_condition, _any_outcome_forcer, [], "Overall", 1.0, {})


class ScenarioOutcomes:
    def __init__(self, *conditions: ScenarioCondition, description_override: str | None = None):
        self.__conditions = list(conditions)
        self.__description_override = description_override
        self.__total_seasons = 0
        self.__ccg_participants: dict[tuple[TeamPair, ...], int] = defaultdict(_zero)

    @property
    def total_seasons(self) -> int:
        return self.__total_seasons

    @property
    def ccg_participants(self) -> dict[tuple[TeamPair, ...], int]:
        return self.__ccg_participants

    @property
    def game_forcers(self) -> list[ScenarioForcer]:
        return self.__conditions

    @property
    def probability(self) -> float:
        prob = 1.0
        factors = set()
        for condition in self.__conditions:
            prob *= condition.probability
            for matchup, p in condition.probability_factors.items():
                if matchup in factors:
                    prob /= p
                factors.add(matchup)
        return prob

    def __contains__(self, rolled_season: SeasonSnapshot) -> bool:
        return all(rolled_season in condition for condition in self.__conditions)

    def __iadd__(self, result: tuple[SeasonSnapshot, tuple[TeamPair, ...]]) -> "ScenarioOutcomes":
        season, ccg_teams = result
        if season in self:
            self.__total_seasons += 1
            self.__ccg_participants[ccg_teams] += 1
        return self

    def prob_in_ccg(self, team: TeamName):
        return sum(count for ccg_teams, count in self.__ccg_participants.items() if any(team in ccg_matchup for ccg_matchup in ccg_teams)) / (self.__total_seasons or 1)

    def description(self, separator="\n"):
        if self.__description_override:
            return self.__description_override
        return separator.join(map(str, self.__conditions))

    def __ior__(self, other: "ScenarioOutcomes") -> "ScenarioOutcomes":
        self.__total_seasons += other.__total_seasons
        for matchups, count in other.__ccg_participants.items():
            self.__ccg_participants[matchups] += count
        return self

    def __str__(self) -> str:
        return self.description()


@dataclass
class WeekOutcomes:
    games: list[TeamPair]
    total_count: int = 0
    permutations: dict[TeamNames, dict[TeamPair, int]] = field(default_factory=_default_default_zero)

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

    def __ior__(self, other: "WeekOutcomes") -> "WeekOutcomes":
        self.total_count += other.total_count
        for winners, matchups in other.permutations.items():
            for matchup, count in matchups.items():
                self.permutations[winners][matchup] += count
        return self

    def shallow_clone(self) -> "WeekOutcomes":
        return WeekOutcomes(games=self.games)
