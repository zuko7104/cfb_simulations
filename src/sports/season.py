from collections import defaultdict
from dataclasses import dataclass
import datetime
from functools import cached_property
from itertools import combinations
from typing import Callable, Iterable, TypeAlias


TeamName: TypeAlias = str
"""The unambiguous common name for a team (e.g. "SMU", "BYU", "Alabama")"""
ConferenceName: TypeAlias = str
"""The abreviated name of a conference (e.g. "B12")"""
TeamPair: TypeAlias = tuple[TeamName, TeamName]
"""A pair of team names"""
TeamNames: TypeAlias = tuple[TeamName, ...]
"""A tuple of team names"""
Standing: TypeAlias = tuple[int, int]
"""The standing of a team in a conference, of the form (position, tied_team_count)"""


BinaryRoller: TypeAlias = Callable[[float], bool]
"""A function that draws from the binary distribution with p(success) given by
the parameter to the function."""
UniformRoller: TypeAlias = Callable[[], float]
"""A function that draws from the uniform(0, 1) distribution"""


def _bool_from_string(b: str) -> bool:
    return b.strip() in ["t", "1", "true", "T", "True", "TRUE"]
def _string_from_bool(b: bool) -> str:
    return "True" if b else "False"
def _score_from_string(s: str) -> tuple[int, int] | None:
    s = s.strip()
    if s in ["", None, "None", "none"]:
        return None
    s = s.strip("()")
    parts = [p.strip() for p in s.split(",")]
    return int(parts[0]), int(parts[1])
def _string_from_score(s: tuple[int, int] | None):
    if s is None:
        return "None"
    return f"({s[0]},{s[1]})"
def _probability_from_string(p: str) -> tuple[int, int] | None:
    p = p.strip()
    if p in ["", None, "None", "none"]:
        return None
    return float(p)
def _string_from_probability(p: float | None) -> str:
    if p is None:
        return "None"
    return str(p)


@dataclass
class Game:
    """A game between two teams"""
    date: datetime.date
    """The date of the game"""
    team_a: TeamName
    """Away team (if not neutral)"""
    team_b: TeamName
    """Home team (if not neutral)"""
    neutral: bool
    """Game played at a neutral site"""
    final_score: tuple[int, int] | None
    """Final score, if over"""
    team_a_win_probability: float | None
    """Win probability of team a, if not over"""
    @cached_property
    def team_b_win_probability(self) -> float | None:
        """Win probability of team b, if """
        return 1 - self.team_a_win_probability if self.team_a_win_probability is not None else None
    @cached_property
    def is_over(self) -> bool:
        """Whether the game is over"""
        return self.final_score is not None
    @cached_property
    def winner(self) -> TeamName | None:
        """Winner, if not a tie and game is over"""
        if self.is_over:
            if self.final_score[0] > self.final_score[1]:
                return self.team_a
            elif self.final_score[1] > self.final_score[0]:
                return self.team_b
        return None
    @cached_property
    def is_tie(self) -> bool | None:
        """Whether the game ended in a tie, if game is over"""
        if self.is_over:
            return self.final_score[0] == self.final_score[1]
        return None
    
    def __contains__(self, team: TeamName | Iterable[TeamName]) -> bool:
        if isinstance(team, TeamName):
            return team == self.team_a or team == self.team_b
        else:
            return any(t in self for t in team)
    
    def win_probability(self, team: TeamName) -> float:
        """
        Returns the win probability of the indicated team
        
        The win probability for a team that won is 1, for a team that lost is 0.
        """
        if team not in self:
            raise ValueError("No such team in this game")
        if self.is_over:
            return 1 if self.winner == team else 0
        else:
            if team == self.team_a:
                return self.team_a_win_probability
            else:
                return self.team_b_win_probability
    
    def opponent(self, team: TeamName) -> TeamName:
        if team not in self:
            raise ValueError("No such team in this game")
        return self.team_a if team == self.team_b else self.team_b
    
    def clone(self) -> "Game":
        return Game(self.date, self.team_a, self.team_b, self.neutral, self.final_score, self.team_a_win_probability)
    
    def __clone_with_score(self, final_score: tuple[int, int]) -> "Game":
        return Game(self.date, self.team_a, self.team_b, self.neutral, final_score, None)

    def roll(self, roller: BinaryRoller, *, force_winners: list[TeamName] | None = None, force_losers: list[TeamName] | None = None) -> "Game":
        if self.is_over:
            return self
        for winner in force_winners or {}:
            if winner in self:
                return self.force_outcome_if_not_over(winner, True)
        for loser in force_losers or {}:
            if loser in self:
                return self.force_outcome_if_not_over(loser, False)
        final_score = (1, 0) if roller(self.team_a_win_probability) else (0, 1)
        return self.__clone_with_score(final_score)
    
    def force_outcome_if_not_over(self, team: TeamName, win: bool) -> "Game":
        if self.is_over:
            return self
        if team not in self:
            raise ValueError(f"Can't make {team} win {self}")
        if (win and team == self.team_a) or (not win and team == self.team_b):
            score = (1, 0)
        else:
            score = (0, 1)
        return self.__clone_with_score(score)
    
    @staticmethod
    def deserialize(serialized: str) -> "Game":
        d, team_a, team_b, n, s, p = serialized.split("*")
        date = datetime.datetime.strptime(d, "%Y-%m-%d").date()
        neutral = _bool_from_string(n)
        score = _score_from_string(s)
        prob = _probability_from_string(p)
        return Game(date, team_a.strip(), team_b.strip(), neutral, score, prob)
    
    def serialize(self) -> str:
        return "*".join((str(self.date), self.team_a, self.team_b, _string_from_bool(self.neutral), _string_from_score(self.final_score), _string_from_probability(self.team_a_win_probability)))
    
    def __hash__(self) -> int:
        return hash(self.date) * hash(self.team_a) * hash(self.team_b)
    


@dataclass
class Division:
    """A division of a conference"""
    name: str
    """The name of the division (e.g. "South")"""
    team_names: set[TeamName]
    """The teams in the division"""

    @staticmethod
    def deserialize(serialized: str) -> "Division":
        parts = [part.strip() for part in serialized.split(",")]
        return Division(parts[0], parts[1:])
        
    def serialize(self) -> str:
        return self.name + "," + ",".join(self.team_names)
    
    def __hash__(self) -> int:
        return hash(self.name)


@dataclass
class TeamSnapshot:
    """A team"""
    name: TeamName
    """The name of the team"""
    games: list[Game]
    """The games this season"""
    conference: ConferenceName | None
    """The name of the conference this team belongs to, if any"""
    @cached_property
    def played_games(self) -> list[Game]:
        return [game for game in self.games if game.is_over]
    @cached_property
    def remaining_games(self) -> list[Game]:
        return [game for game in self.games if not game.is_over]
    @cached_property
    def opponents(self) -> set[TeamName]:
        return {game.opponent(self.name) for game in self.games}
    @cached_property
    def played_opponents(self) -> set[TeamName]:
        return {game.opponent(self.name) for game in self.played_games}
    @cached_property
    def wins(self) -> int: 
        """The number of wins so far this season"""
        return sum(map(lambda game: 1 if game.winner == self.name else 0, self.played_games))
    @cached_property
    def losses(self) -> int:
        """The number of losses so far this season"""
        return sum(map(lambda game: 1 if game.winner != self.name and not game.is_tie else 0, self.played_games))
    @cached_property
    def wins_against(self) -> set[TeamName]:
        return {game.opponent(self.name) for game in self.played_games if game.winner == self.name}
    @cached_property
    def losses_against(self) -> set[TeamName]:
        return {game.opponent(self.name) for game in self.played_games if game.winner != self.name}
    @cached_property
    def ties(self) -> int:
        """The number of ties so far this season"""
        return sum(map(lambda game: 1 if game.is_tie else 0, self.played_games))
    @cached_property
    def win_percentage(self) -> float:
        """The win percentage this season"""
        wins = self.wins
        losses = self.losses
        ties = self.ties
        total = wins + losses + ties
        return wins / total if total > 0 else 1.0
    @cached_property
    def predicted_wins(self) -> float:
        """The total number of wins predicted this season"""
        return sum(map(lambda game: game.win_probability(self.name), self.games))
    @cached_property
    def predicted_losses(self) -> float:
        """The total number of losses predicted this season"""
        return sum(map(lambda game: 1 - game.win_probability(self.name) if not game.is_tie else 0, self.games))
    @cached_property
    def predicted_win_percentage(self) -> float:
        """The predicted win percentage this season"""
        wins = self.predicted_wins
        losses = self.predicted_losses
        ties = self.ties
        total = wins + losses + ties
        return wins / total if total > 0 else 1.0
    @cached_property
    def record(self) -> str:
        """The human-readable record of the team, e.g. '6-2'"""
        wins = self.wins
        losses = self.losses
        ties = self.ties
        return f"{wins}-{losses}" if ties <= 0 else f"{wins}-{losses}-{ties}"
    @cached_property
    def predicted_record(self) -> str:
        """The human-readable predicted record of the team, e.g. '6-2'"""
        wins = self.predicted_wins
        losses = self.predicted_losses
        ties = self.ties
        return f"{wins}-{losses}" if ties <= 0 else f"{wins}-{losses}-{ties}"
    
    def has_played(self, teams: set[TeamName]) -> bool:
        # TODO This is only for 2024
        if (self.name == "Kansas St" and "Arizona" in teams) or (self.name == "Arizona" and "Kansas St" in teams):
            return False
        if (self.name == "Utah" and "Baylor" in teams) or (self.name == "Baylor" and "Utah" in teams):
            return False
        return self.played_opponents.issuperset(teams)
    
    def plays_any(self, teams: set[TeamName]) -> bool:
        return len(self.opponents.intersection(teams)) > 0
    
    def filtered_record(self, teams: set[TeamName]) -> tuple[int, int, int]:
        # TODO This is only for 2024
        if self.name == "Kansas St":
            teams = teams.difference({"Arizona"})
        elif self.name == "Arizona":
            teams = teams.difference({"Kansas St"})
        elif self.name == "Utah":
            teams = teams.difference({"Baylor"})
        elif self.name == "Baylor":
            teams = teams.difference({"Utah"})

        wins = 0
        losses = 0
        ties = 0
        
        for game in filter(lambda game: game.is_over and game.opponent(self.name) in teams, self.games):
            if game.is_tie:
                ties += 1
            elif game.winner == self.name:
                wins += 1
            else:
                losses += 1

        return wins, losses, ties

    def filtered_win_percentage(self, teams: set[TeamName]) -> float:
        wins, losses, ties = self.filtered_record(teams)
        total = wins + losses + ties
        return wins / total if total > 0 else 1.0
    
    def __clone_with_games(self, games: set[Game]) -> "TeamSnapshot":
        return TeamSnapshot(self.name, games, self.conference)
    
    def clone(self) -> "TeamSnapshot":
        return self.__clone_with_games([game.clone() for game in self.games])

    def roll(self, roller: UniformRoller, *, force_future_loss_count: int | None = None) -> "TeamSnapshot":
        binary_roller = lambda p: roller() <= p
        if force_future_loss_count is None:
            return self.__clone_with_games([game.roll(binary_roller) for game in self.games])
        if force_future_loss_count < 0 or force_future_loss_count > len(self.remaining_games):
            raise ValueError(f"{self.name} cannot lose {force_future_loss_count} games")
        if force_future_loss_count == 0:
            return self.__clone_with_games([game.force_outcome_if_not_over(self.name, True) for game in self.games]) 
        if force_future_loss_count == len(self.remaining_games):
            return self.__clone_with_games([game.force_outcome_if_not_over(self.name, False) for game in self.games])
        
        games = [game for game in self.games if game.is_over]
        win_probabilities = [game.win_probability(self.name) for game in self.remaining_games]
        loss_combos = {combo for combo in combinations(list(range(len(self.remaining_games))), force_future_loss_count)}
        combo_probabilities = []
        for loss_combo in loss_combos:
            p = 1.0
            for i, win_probability in enumerate(win_probabilities):
                p *= (1 - win_probability) if i in loss_combo else win_probability
            combo_probabilities.append(p)
        total = sum(combo_probabilities)
        buckets: list[float] = []
        running_total = 0.0
        for prob in combo_probabilities:
            running_total += prob
            buckets.append(running_total / total)
        buckets[-1] = 1.0
        
        roll = roller()
        for combo, bucket in zip(loss_combos, buckets):
            if roll <= bucket:
                losses = combo
                break
        else:
            raise ValueError(f"{roll} not in {buckets}")

        for i, game in enumerate(self.remaining_games):
            result = game.force_outcome_if_not_over(self.name, i not in losses)
            games.append(result)
        
        assert len(games) == len(self.games)
        return self.__clone_with_games(games)
    
    def __hash__(self) -> int:
        return hash(self.name)


ChampionshipSeeder: TypeAlias = Callable[[set[TeamName], set[TeamSnapshot], list[set[TeamSnapshot]]], TeamPair]


@dataclass
class Conference:
    """A conference of teams"""
    name: ConferenceName
    """The name of the conference"""
    teams: set[TeamName]
    """The teams in the conference"""
    divisions: set[Division] | None
    """The divisions in the conference, if applicable"""
    has_championship_game: bool
    """Whether the conference has a championship game"""
    championship_seeder: ChampionshipSeeder | None

    @staticmethod
    def deserialize(serialized: list[str], championship_seeder_getter: Callable[[ConferenceName], ChampionshipSeeder | None]) -> "Conference":
        name = serialized[0].strip()
        has_championship_game = _bool_from_string(serialized[1])
        teams = {team.strip() for team in serialized[2].split(",")}
        divisions = {Division.deserialize(part) for part in serialized[3].split("&") if part}
        championship_seeder = championship_seeder_getter(name)
        return Conference(name, teams, divisions, has_championship_game, championship_seeder)
    
    def serialize(self) -> list[str]:
        return [
            self.name,
            _string_from_bool(self.has_championship_game),
            ",".join(self.teams),
            "&".join(division.serialize() for division in self.divisions) if self.divisions else "",
        ]
    
    def __hash__(self) -> int:
        return hash(self.name)


@dataclass
class ConferenceSnapshot:
    name: ConferenceName
    """The name of the conference"""
    teams: set[TeamSnapshot]
    @cached_property
    def team_names(self) -> set[TeamName]:
        return {team.name for team in self.teams}
    divisions: set[Division] | None
    has_championship_game: bool
    championship_seeder: ChampionshipSeeder | None

    @cached_property
    def standings(self) -> list[set[TeamSnapshot]]:
        win_percentage_to_teams: defaultdict[float, set[TeamSnapshot]] = defaultdict(set)
        team_names = self.team_names
        for team in self.teams:
            win_percentage_to_teams[team.filtered_win_percentage(team_names)].add(team)
        return list(map(lambda item: item[1], sorted(win_percentage_to_teams.items(), key=lambda a: a[0], reverse=True)))

    @cached_property
    def championship_game_participants(self) -> TeamPair | None:
        if not self.has_championship_game or self.championship_seeder is None:
            return None
        return self.championship_seeder(self.team_names, self.teams, self.standings)

    @cached_property
    def champion(self) -> TeamName | None:
        if self.has_championship_game or self.championship_seeder is None:
            return None
        return self.championship_seeder(self.team_names, self.teams, self.standings)[0]
    
    def standing(self, team: TeamName) -> Standing:
        if team not in self.team_names:
            raise ValueError(f"{self.name} does not contain {team}")
        teams_above = 0
        for tier in self.standings:
            for t in tier:
                if t.name == team:
                    return teams_above + 1, len(tier)
            teams_above += len(tier)
        raise ValueError("Impossible to be here")
    
    @staticmethod
    def from_conference(conference: Conference, teams: set[TeamSnapshot]):
        return ConferenceSnapshot(conference.name, teams, conference.divisions, conference.has_championship_game, conference.championship_seeder)
    
    
@dataclass
class SeasonSnapshot:
    year: int
    conferences: set[Conference]
    games: set[Game]

    def __team_from_games_subset(self, name: TeamName, games: set[Game]) -> TeamSnapshot:
        for conf in self.conferences:
            if name in conf.teams:
                conference = conf.name
                break
        else:
            conference = None

        games = sorted(filter(lambda game: name in game, games), key=lambda game: game.date)
        
        return TeamSnapshot(name, games, conference)
    
    def filter(self, conference: ConferenceName) -> "SeasonSnapshot":
        for c in self.conferences:
            if c.name == conference:
                conf = c
                break
        else:
            raise ValueError(f"No such conference: {conference}")
        
        games = {game.clone() for game in self.games if conf.teams in game}
        conferences = {conf}
        return SeasonSnapshot(self.year, conferences, games)

    def team(self, name: TeamName) -> TeamSnapshot:
        """Get the data for one team"""
        return self.__team_from_games_subset(name, self.games)
    
    def conference(self, name: ConferenceName) -> ConferenceSnapshot:
        for c in self.conferences:
            if c.name == name:
                conf = c
                break
        else:
            raise ValueError(f"No such conference {name}")
        
        teams = {self.team(team) for team in conf.teams}
        if not teams:
            raise ValueError(f"Empty teams in conference {name}")

        return ConferenceSnapshot.from_conference(conf, teams)
    
    def __clone_with_games(self, games: set[Game]) -> "SeasonSnapshot":
        return SeasonSnapshot(self.year, self.conferences, games)

    def clone(self) -> "SeasonSnapshot":
        return self.__clone_with_games({game.clone() for game in self.games})

    def roll(self, roller: UniformRoller, *,
             force_future_loss_counts: dict[TeamName, int] | None = None,
             force_winners: list[TeamName] | None = None,
             force_losers: list[TeamName] | None = None) -> "SeasonSnapshot":
        force_winners = force_winners or []
        force_losers = force_losers or []
        binary_roller = lambda p: roller() <= p
        if not force_future_loss_counts:
            games = {game.roll(binary_roller, force_winners=force_winners, force_losers=force_losers) for game in self.games}
            return self.__clone_with_games(games)
        
        if any(losses < 0 for losses in force_future_loss_counts.values()):
            raise ValueError("Negative loss count")
        if not force_future_loss_counts.keys().isdisjoint(force_winners) or not force_future_loss_counts.keys().isdisjoint(force_losers):
            raise ValueError("Force future loss count not disjoint from forced winners and losers")
        
        games = {game.roll(binary_roller, force_winners=force_winners, force_losers=force_losers) for game in self.games if game.is_over or (force_winners in game or force_losers in game or force_future_loss_counts.keys() not in game)}
        remaining_games = {game for game in self.games if not game.is_over and force_future_loss_counts.keys() in game}
        teams = {self.__team_from_games_subset(team, remaining_games) for team in force_future_loss_counts.keys()}

        for team in teams:
            if force_future_loss_counts[team.name] > len(team.games):
                raise ValueError(f"{team.name} can't lose {force_future_loss_counts[team.name]} more games")
            if team.plays_any(teams):
                raise NotImplementedError(f"Forcing win counts for teams that play each other is not implemented: {teams}")

        assert(sum(len(team.games) for team in teams) == len(remaining_games))

        for team in teams:
            games.update(team.roll(roller, force_future_loss_count=force_future_loss_counts[team.name]).games)
        
        assert(len(games) == len(self.games))
        
        return self.__clone_with_games(games)
    
    @staticmethod
    def deserialize(lines: Iterable[str], championship_seeder_getter: Callable[[ConferenceName], ChampionshipSeeder | None]) -> "SeasonSnapshot":
        year: int | None = None
        conferences: set[Conference] | None = None
        games: set[Game] | None = None
        buffer = []

        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                continue
            if games is not None:
                games.add(Game.deserialize(line))
                continue
            if conferences is not None:
                if line.startswith("$"):
                    games = set()
                if line.startswith("%") or line.startswith("$"):
                    conferences.add(Conference.deserialize(buffer, championship_seeder_getter))
                    buffer.clear()
                    continue
                buffer.append(line)
                continue
            else:
                if year is None:
                    year = int(line.strip())
                    continue
                elif line.startswith("$"):
                    conferences = set()
                    buffer.clear()
                    continue
            print("unknown line:", line)

        return SeasonSnapshot(year, conferences, games)
    
    def serialize(self) -> list[str]:
        lines: list[str] = []
        lines.append(str(self.year))
        lines.append("$ conferences")
        for conference in self.conferences:
            lines += conference.serialize()
            lines.append("%")
        if self.conferences:
            lines.pop()
        lines.append("$ games")
        lines += [game.serialize() for game in self.games]
        return lines
