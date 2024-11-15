from sports.season import TeamName, TeamSnapshot
from collections import defaultdict
from typing import TypeVar, Iterable, Callable
import random

_T = TypeVar("_T")
_U = TypeVar("_U")

def sorted_with_ties(a: Iterable[_T], *, key: Callable[[_T], _U], reverse: bool = False) -> list[set[_T]]:
    key_to_tiers: defaultdict[_U, set[_T]] = defaultdict(set)
    for item in a:
        key_to_tiers[key(item)].add(item)
    return [item[1] for item in sorted(key_to_tiers.items(), key=lambda item: item[0], reverse=reverse)]

def head_to_head(all_team_names: set[TeamName], all_teams: set[TeamSnapshot], tied_teams: set[TeamSnapshot], standings: list[set[TeamSnapshot]]) -> list[set[TeamSnapshot]]:
    del all_team_names, all_teams, standings
    names = {team.name for team in tied_teams}
    for tied_team in tied_teams:
        if tied_team.has_played(names - {tied_team.name}):
            if tied_team.filtered_record(names - {tied_team.name})[0] == len(names) - 1:
                return [{tied_team}, tied_teams - {tied_team}]
    if not all(team.has_played(names - {team.name}) for team in tied_teams):
        return [tied_teams]
    return sorted_with_ties(tied_teams, key=lambda team: team.filtered_win_percentage(names), reverse=True)

def _all_common_opponents(all_team_names: set[TeamName], teams: set[TeamSnapshot]) -> set[TeamName]:
    common = set(all_team_names)
    # TODO This is only for 2024
    for team in teams:
        common &= team.played_opponents
    if {"Arizona", "Kansas St"} & {team.name for team in teams}:
        common -= {"Arizona", "Kansas St"}
    if {"Baylor", "Utah"} & {team.name for team in teams}:
        common -= {"Baylor", "Utah"}
    return common

def against_highest_common_opponent(all_team_names: set[TeamName], all_teams: set[TeamSnapshot], tied_teams: set[TeamSnapshot], standings: list[set[TeamSnapshot]]) -> list[set[TeamSnapshot]]:
    del all_teams
    all_common_opponents = _all_common_opponents(all_team_names, tied_teams)
    untied = []
    for tier in standings:
        tier_common_opponents = {team.name for team in tier if team.name in all_common_opponents}
        tier_results = sorted_with_ties(tied_teams, key=lambda team: team.filtered_win_percentage(tier_common_opponents), reverse=True)
        if len(tier_results) > 1:
            if len(tier_results[0]) < 3:
                return tier_results + untied
            else:
                tied_teams = tier_results[0]
                untied = tier_results[1:] + untied
                all_common_opponents = _all_common_opponents(all_team_names, tied_teams)
    return [tied_teams] + untied

def against_all_common_opponents(all_team_names: set[TeamName], all_teams: set[TeamSnapshot], tied_teams: set[TeamSnapshot], standings: list[set[TeamSnapshot]]) -> list[set[TeamSnapshot]]:
    del all_teams, standings
    all_common_opponents = _all_common_opponents(all_team_names, tied_teams)
    return sorted_with_ties(tied_teams, key=lambda team: team.filtered_win_percentage(all_common_opponents), reverse=True)

def strength_of_conference_schedule(all_team_names: set[TeamName], all_teams: set[TeamSnapshot], tied_teams: set[TeamSnapshot], standings: list[set[TeamSnapshot]]) -> list[set[TeamSnapshot]]:
    del standings
    def conf_sos(team: TeamSnapshot) -> float:
        conference_opponents = all_team_names & team.played_opponents
        # TODO this is only for the 2024 season
        if team.name == "Kansas St":
            conference_opponents -= {"Arizona"}
        elif team.name == "Arizona":
            conference_opponents -= {"Kansas St"}
        elif team.name == "Utah":
            conference_opponents -= {"Baylor"}
        elif team.name == "Baylor":
            conference_opponents -= {"Utah"}

        wins = 0
        played = 0
        for opponent in filter(lambda team: team.name in conference_opponents, all_teams):
            w, l, t = opponent.filtered_record(all_team_names)
            wins += w
            played += w + l + t
        return wins / max(played, 1)
    return sorted_with_ties(tied_teams, key=conf_sos, reverse=True)

def total_wins_in_12_game_season(all_team_names: set[TeamName], all_teams: set[TeamSnapshot], tied_teams: set[TeamSnapshot], standings: list[set[TeamSnapshot]]) -> list[set[TeamSnapshot]]:
    del all_team_names, all_teams, standings
    def wins_in_12_game_season(team: TeamSnapshot) -> int:
        wins = 0
        for game in team.games:
            if not game.neutral and game.team_b == "Hawaii":
                continue
            # TODO somehow exclude "foreign tour" games
            if game.winner == team.name:
                wins += 1
        return wins
    return sorted_with_ties(tied_teams, key=wins_in_12_game_season, reverse=True)

def coin_toss(all_team_names: set[TeamName], all_teams: set[TeamSnapshot], tied_teams: set[TeamSnapshot], standings: list[set[TeamSnapshot]]) -> list[set[TeamSnapshot]]:
    del all_teams
    place = 0
    for tier in standings:
        place += 1
        if tied_teams & tier:
            break
    # if place > 1 or len(tied_teams) > 2:
        # print(f"WARN: coin toss decided winner of {[team.name for team in tied_teams]} for {place}: {[team.losses_against for team in tied_teams]}, {[team.name for team in standings[0]]} is first place")
        # for tier in standings:
        #     print("[")
        #     for team in tier:
        #         wins = team.filtered_record(all_team_names)[0]
        #         print("   ", team.name, wins, "wins:", team.wins_against & all_team_names, "losses:", team.losses_against & all_team_names)
        #     print("],")
    winner = random.choice(list(tied_teams))
    return [{winner}, tied_teams - {winner}]

def big12_championship_seeder(all_team_names: set[TeamName], all_teams: set[TeamSnapshot], standings: list[set[TeamSnapshot]]) -> tuple[TeamName, TeamName]:
    tiebreakers = [head_to_head, against_all_common_opponents, against_highest_common_opponent, strength_of_conference_schedule, total_wins_in_12_game_season, coin_toss]
    def two_team_tiebreaker(tied_teams: set[TeamSnapshot]) -> tuple[TeamSnapshot, TeamSnapshot]:
        for tiebreaker in tiebreakers:
            result = tiebreaker(all_team_names, all_teams, tied_teams, standings)
            if len(result) == 0:
                raise ValueError(f"Impossible tiebreaker result between {tied_teams}; standings are {standings}")
            elif len(result) > 1:
                (r1,) = result[0]
                (r2,) = result[1]
                return r1, r2
        raise ValueError(f"Unable to break tie between {tied_teams}; standings are {standings}")

    def multi_team_tiebreaker(tied_teams: set[TeamSnapshot]) -> TeamSnapshot | set[TeamSnapshot]: # -> list[set[TeamSnapshot]]:
        tiebroken_tiers = [tied_teams]
        for tiebreaker in tiebreakers:
            result = tiebreaker(all_team_names, all_teams, tiebroken_tiers[0], standings)
            if len(tiebroken_tiers) > 1:
                tiebroken_tiers = result + tiebroken_tiers[1:]
            else:
                tiebroken_tiers = result
            if len(tiebroken_tiers[0]) == 1:
                return next(iter(tiebroken_tiers[0]))
            elif len(tiebroken_tiers[0]) == 2:
                return tiebroken_tiers[0]
        raise ValueError(f"Unable to break tie between {tied_teams}; standings are {standings}")

    seed_1: TeamSnapshot | None = None
    seed_2: TeamSnapshot | None = None

    if len(standings[0]) == 1:
        (seed_1,) = standings[0]
        if len(standings[1]) == 1:
            (seed_2,) = standings[1]
        elif len(standings[1]) == 2:
            seed_2, _ = two_team_tiebreaker(standings[1])
        else:
            seed_2 = multi_team_tiebreaker(standings[1])
            if not isinstance(seed_2, TeamSnapshot):
                seed_2, _ = two_team_tiebreaker(seed_2)
    elif len(standings[0]) == 2:
        seed_1, seed_2 = two_team_tiebreaker(standings[0])
    else:
        seed_1 = multi_team_tiebreaker(standings[0])
        if not isinstance(seed_1, TeamSnapshot):
            seed_1, _ = two_team_tiebreaker(seed_1)
        remaining = {team for team in standings[0] if team.name != seed_1.name}
        if len(remaining) == 2:
            seed_2, _ = two_team_tiebreaker(remaining)
        else:
            seed_2 = multi_team_tiebreaker(remaining)
            if not isinstance(seed_2, TeamSnapshot):
                seed_2, _ = two_team_tiebreaker(seed_2)

    return seed_1.name, seed_2.name
