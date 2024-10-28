from sports.season import TeamName, TeamNames, ConferenceName
from sports.outcomes import ConferenceSeasonOutcomes, ScenarioOutcomes, WeekOutcomes
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import math

def _get_team_logo(team: TeamName):
    return plt.imread(f"assets/{team.lower().replace(" ", "_")}.png") 

def _rounded_percent(probability: float) -> float:
    if probability < 1:
        probability = min(0.999, probability)
    return round(probability * 1000) / 10

def _rounded_percent_str(probability: float | None) -> str:
    if probability is None:
        return  ""
    if probability == 0:
        return "0.0%"
    if probability < 0.001:
        return "<0.1%"
    if probability < 1:
        probability = min(0.999, probability)
    return f"{round(probability * 1000) / 10}%"

def _percent_to_color(percent: str, default: str="#555555", target: tuple[int, int, int] = (0x33, 0xff, 0x33)):
    if percent == "":
        return default
    
    try:
        if percent[1] == "<":
            prob = 0.0005
        else:
            prob = float(percent[:-1]) / 100
    except ValueError:
        return "w"

    red = round(target[0] * prob + 0xff * (1-prob))
    green = round(target[1] * prob + 0xff * (1-prob))
    blue = round(target[2] * prob + 0xff * (1-prob))
    color = f"#{red:02x}{green:02x}{blue:02x}"
    return color

def _bar_graph(
        title: str,
        labels: list[str],
        Y: list[float],
        xlabel: str | None = None,
        ylabel: str = "Probability (%)",
        *,
        teams: list[TeamNames] | None = None,
        bar_label_postfix: str = "%",
        caption: str | None = None
    ) -> Figure:
    fig = plt.figure(title, (max(12 / 16 * len(Y), 7), 6))
    ax = fig.add_axes((0.1, 0.2, 0.8, 0.7) if not teams else (0.1, 0.1 + 0.08 * len(teams[0]), 0.8, 0.8 - 0.08 * len(teams[0])))
    ax.set_title(title)
    bars = ax.bar(labels, Y)
    ax.bar_label(ax.containers[0], [str(y) + bar_label_postfix for y in Y])
    if teams:
        for bar, team_names in zip(bars, teams):
            for i, team in enumerate(team_names):
                logo = _get_team_logo(team)
                imagebox = OffsetImage(logo, zoom=40 / max(logo.shape))
                ab = AnnotationBbox(imagebox, (bar.get_x() + bar.get_width() / 2, 0), xybox=(0.0, -60.0 - i*30), boxcoords="offset points", pad=0, xycoords='data', box_alignment=(0.5, -0.5), frameon=False)
                ax.add_artist(ab)
        ax.set_xticks([])
    else:
        ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, int((max(Y) + 12) / 10) * 10)
    if caption:
        fig.text(0.5, 0.05, caption, ha="center", fontsize=10)
    return fig

class ConferenceFigures:
    def __init__(self, conference_name: ConferenceName, conference_outcomes: ConferenceSeasonOutcomes, scenarios: list[ScenarioOutcomes], week_outcomes: WeekOutcomes):
        self.__conference_name = conference_name
        self.__conference = conference_outcomes
        self.__scenarios = scenarios
        self.__week = week_outcomes
        self.__figures: dict[str, Figure] = {}
    
    def save(self, path_prefix: str = ""):
        for path, fig in self.__figures.items():
            fig.savefig(path_prefix + path + ".png")
    
    def show(self):
        plt.show()
    
    def all_figures(self, interesting_teams: list[TeamName], ccg_target: str | None = None):
        self.bars_ccg_probabilities()
        self.bars_ccg_matchups()
        if ccg_target:
            self.table_week(ccg_target)
        self.table_in_ccg_prob_given_total_wins()
        self.table_record_probabilities()
        self.table_scenarios(interesting_teams)
        self.table_in_ccg_prob_given_specific_losses(interesting_teams)
        if ccg_target:
            self.table_in_ccg_prob_given_total_wins(ccg_target)
            self.table_in_ccg_prob_given_specific_losses(interesting_teams, ccg_target)
    
    def table_week(self, ccg_target: TeamName):
        cells = []
        for matchup in self.__week.games:
            prob_if_away_win = self.__week.prob_in_ccg_given_winners({matchup[0]}, ccg_target)
            prob_if_home_win = self.__week.prob_in_ccg_given_winners({matchup[1]}, ccg_target)
            preferred_team = matchup[0] if prob_if_away_win > prob_if_home_win else matchup[1]
            cells.append([_rounded_percent_str(prob_if_away_win), _rounded_percent_str(prob_if_home_win), preferred_team])
        matchups = [f"{matchup[0]} @ {matchup[1]}" for matchup in self.__week.games]
        col_labels = ["If Away Team Wins", "If Home Team Wins", "Preferred Team"]
        colors = [[_percent_to_color(percent) for percent in row] for row in cells]

        title = f"Probability of {ccg_target} Making the CCG Given This Week's Matchup Results"
        fig = plt.figure(title, figsize=(20, 4))
        ax = plt.gca()
        fig.patch.set_visible(False)
        ax.set_title(title)
        ax.axis("off")
        ax.axis("tight")
        table = ax.table(cells, colLabels=col_labels, rowLabels=matchups, loc="center", cellColours=colors)
        table.scale(1.0, 1.5)
        self.__figures[f"{ccg_target.lower()}-ccg-probs-given-week-results"] = fig

        best_winners = None
        best_ccg_prob = 0
        best_prob = 0
        most_realistic_winners = None
        most_realistic_score = 0
        most_realistic_ccg_prob = 0
        most_realistic_prob = 0
        def index_lookup(team: TeamName) -> int:
            for i, matchup in enumerate(self.__week.games):
                if team in matchup:
                    return i
            return -1
        def pad(s: str) -> str:
            return f"{s:11}"
        
        # TODO Calculate best 2, 3, 4 winner combinations

        print("Possible weekly outcomes")
        for winners in self.__week.permutations.keys():
            ccg_prob = self.__week.prob_in_ccg_given_winners(set(winners), ccg_target)
            prob = self.__week.prob_of_winners(set(winners))
            score = ccg_prob * prob
            print(f"{','.join(pad(winner) for winner in sorted(winners, key=index_lookup))}, P(winners): {_rounded_percent_str(prob):>5} P(CCG): {_rounded_percent_str(ccg_prob):>5} score: {_rounded_percent(score)}")
            if ccg_prob > best_ccg_prob:
                best_winners = winners
                best_ccg_prob = ccg_prob
                best_prob = prob
            if score > most_realistic_score:
                most_realistic_winners = winners
                most_realistic_score = score
                most_realistic_ccg_prob = ccg_prob
                most_realistic_prob = prob
            
        cells = [
            [", ".join(best_winners), _rounded_percent_str(best_prob), _rounded_percent_str(best_ccg_prob)],
            [", ".join(most_realistic_winners), _rounded_percent_str(most_realistic_prob), _rounded_percent_str(most_realistic_ccg_prob)]
        ]
        row_labels = ["Best Outcome", "Most Realistic Good Outcome"]
        col_labels = ["Winners", "Scenario Probability", f"{ccg_target} CCG Probability"]
        colors = [[_percent_to_color(percent) for percent in row] for row in cells]

        title = f"Best Week Results for {ccg_target}"
        fig = plt.figure(title, figsize=(20, 4))
        ax = plt.gca()
        fig.patch.set_visible(False)
        ax.set_title(title)
        ax.axis("off")
        ax.axis("tight")
        table = ax.table(cells, colLabels=col_labels, rowLabels=row_labels, loc="center", cellColours=colors)
        table.scale(1.0, 1.5)
        self.__figures[f"{ccg_target.lower()}-best-week-results"] = fig
    
    def table_in_ccg_prob_given_total_wins(self, ccg_target: TeamName = ...):
        team_probs = {team: self.__conference.prob_in_ccg_given_total_losses(team, ccg_target=ccg_target) for team in self.__conference.team_names}
        max_losses = max(max(probs.keys()) for probs in team_probs.values())

        wins = [12 - losses for losses in range(max_losses + 1)]
        sorted_teams = sorted(self.__conference.team_names, key=lambda team: self.__conference.teams[team].made_ccg, reverse=True)
        cells = [[_rounded_percent_str(team_probs[team].get(losses)) for losses in range(max_losses + 1)] for team in sorted_teams]

        if ccg_target is ...:
            wins.append("Total")
            for team, row in zip(sorted_teams, cells):
                row.append(_rounded_percent_str(self.__conference.teams[team].made_ccg / self.__conference.total_seasons))
        
        colors = [[_percent_to_color(percent) for percent in row] for row in cells]
        
        title = f"Probability of {'Each Team' if ccg_target is ... else ccg_target} Making the CCG Given Total Wins"
        fig = plt.figure(title, figsize=(15, 7))
        ax = plt.gca()
        fig.patch.set_visible(False)
        ax.set_title(title)
        ax.axis("off")
        ax.axis("tight")
        table = ax.table(cells, colLabels=wins, rowLabels=sorted_teams, loc="center", cellColours=colors)
        table.scale(1.0, 1.5)
        self.__figures[f"{'all' if ccg_target is ... else ccg_target.lower()}-ccg-probs-given-total-wins-table"] = fig

    def table_in_ccg_prob_given_specific_losses(self, teams: list[TeamName], ccg_target: TeamName = ...):
        # interesting_teams = ["BYU", "Iowa St", "Kansas St", "Texas Tech", "Cincinnati", "Colorado"]
        # teams = ["BYU", "Iowa St", "Kansas St"]
        team_probs = {team: self.__conference.prob_in_ccg_given_specific_losses(team, ccg_target=ccg_target) for team in teams}

        sorted_team_probs = {team: [(teams, prob) for teams, prob in sorted(probs.items(), key=lambda item: 10 * len(item[0]) + (1 - item[1])) if prob > 0.01 and len(teams) <= 4] for team, probs in team_probs.items()}
        max_rows = max(len(probs) for probs in sorted_team_probs.values())

        cells = []
        for i in range(max_rows):
            row = []
            for team in teams:
                sorted_probs = sorted_team_probs[team]
                losses, prob = sorted_probs[i] if i < len(sorted_probs) else (("",), None)
                row += [", ".join(losses), _rounded_percent_str(prob)]
            cells.append(row)
        colors = [[_percent_to_color(percent, default="w") for percent in row] for row in cells]

        col_labels = []
        for team in teams:
            col_labels += [f"{team} Losses", f"{team if ccg_target is ... else ccg_target} CCG Prob"]

        title = f"Probability of {'Each Team' if ccg_target is ... else ccg_target} Making the CCG Given Specific Losses"
        fig = plt.figure(f"Probability of {'Each Team' if ccg_target is ... else ccg_target} Making the CCG Given Specific Losses", figsize=(30, 15))
        ax = plt.gca()
        fig.patch.set_visible(False)
        ax.set_title(title)
        ax.axis("off")
        ax.axis("tight")
        table = ax.table(cells, loc="center", colLabels=col_labels, cellColours=colors)
        table.scale(1.0, 1.5)
        self.__figures[f"{'all' if ccg_target is ... else ccg_target.lower()}-ccg-probs-given-specific-losses-by-{'-'.join(teams)}-table"] = fig

    def __scenarios_table_data(self, scenarios: list[ScenarioOutcomes], teams: list[TeamName]):
        cells = []
        cells.append([_rounded_percent_str(scenario.total_seasons / self.__conference.total_seasons) for scenario in scenarios])
        for team in teams:
            row = []
            for scenario in scenarios:
                prob_in_ccg = scenario.prob_in_ccg(team)
                row.append(_rounded_percent_str(prob_in_ccg))
            cells.append(row)
        colors = [[_percent_to_color(percent, default="w") for percent in row] for row in cells]
        row_labels = ["Probability of Scenario"] + [f"{team} CCG Probability" for team in teams]
        col_labels = [scenario.description for scenario in scenarios]
        return cells, row_labels, col_labels, colors

    def table_scenarios(self, teams: list[TeamName]):
        # teams = ["BYU", "Iowa St", "Kansas St", "Colorado"]
        max_group_size = 6
        scenario_groups = []
        group_count = int(math.ceil(len(self.__scenarios) / max_group_size))
        min_group_size = len(self.__scenarios) // group_count
        leftover = len(self.__scenarios) % group_count
        start = 0
        end = 0
        for i in range(group_count):
            start = end
            end += min_group_size
            if i < leftover:
                end += 1
            if i == group_count - 1:
                end = len(self.__scenarios)
            scenario_groups.append(self.__scenarios[start:end])

        for i, scenarios in enumerate(scenario_groups):
            cells, row_labels, col_labels, colors = self.__scenarios_table_data(scenarios, teams)

            title = f"Interesting Scenarios {i + 1}"
            fig = plt.figure(title, figsize=(20, 4))
            ax = plt.gca()
            fig.patch.set_visible(False)
            ax.set_title(title)
            ax.axis("off")
            ax.axis("tight")
            table = ax.table(cells, colLabels=col_labels, rowLabels=row_labels, loc="lower center", cellColours=colors)
            table.scale(1.0, 1.5)
            table_cells = table.get_celld()
            for i in range(len(col_labels)):
                table_cells[(0,i)].set_height(3 * table_cells[(0,i)].get_height())
            self.__figures[f"scenarios-table-{i}"] = fig

    def table_record_probabilities(self):
        team_probs = {team: self.__conference.prob_final_win_count(team) for team in self.__conference.team_names}
        min_wins = min(min(probs.keys()) for probs in team_probs.values())
        mean_wins = {team: sum(wins * prob for wins, prob in probs.items()) for team, probs in team_probs.items()}

        wins = list(range(min_wins, 13))[::-1]
        sorted_teams = sorted(self.__conference.team_names, key=lambda team: mean_wins[team], reverse=True)
        cells = [[_rounded_percent_str(team_probs[team].get(win_count)) for win_count in wins] for team in sorted_teams]
        for team, row in zip(sorted_teams, cells):
            row.append(round(mean_wins[team] * 100) / 100)
        wins.append("Mean")

        colors = [[_percent_to_color(percent) for percent in row[:-1]] + ["w"] for row in cells]
        
        title = f"Final Win Count Probabilities for Each Team"
        fig = plt.figure(title, figsize=(15, 7))
        ax = plt.gca()
        fig.patch.set_visible(False)
        ax.set_title(title)
        ax.axis("off")
        ax.axis("tight")
        table = ax.table(cells, colLabels=wins, rowLabels=sorted_teams, loc="center", cellColours=colors)
        table.scale(1.0, 1.5)
        self.__figures["win-count-probs-table"] = fig
    
    def bars_ccg_probabilities(self):
        teams = sorted(self.__conference.team_names)
        Y = [_rounded_percent(self.__conference.prob_in_ccg(team)) for team in teams]
        fig = _bar_graph(f"{self.__conference_name} Team CCG Probabilities", teams, Y, teams=[(team,) for team in teams], caption="Probability of each team making the CCG")
        self.__figures[self.__conference_name.lower() + "-team-ccg-probabilities"] = fig
    
    def bars_ccg_matchups(self):
        matchups = []
        Y = []
        for matchup, count in sorted(self.__conference.ccg_participants.items(), key=lambda item: item[1], reverse=True):
            if count / self.__conference.total_seasons < 0.01:
                continue
            matchups.append(matchup)
            Y.append(_rounded_percent(count / self.__conference.total_seasons))
        fig = _bar_graph(f"{self.__conference_name} CCG Matchups", [",".join(matchup) for matchup in matchups], Y, teams=matchups, caption="Probabilities of various CCG Matchups. Matchups with probability less than 1% are omitted.")
        self.__figures[self.__conference_name.lower() + "-ccg-matchups"] = fig

    # TODO consider making a B12 rankings table
    # total_rankings = 0
    # labels = []
    # Y = []
    # for ranking, count in sorted(rankings.items(), key=lambda item: item[0]):
    #     labels.append(str(ranking))
    #     Y.append(round(count/iterations*1000)/10)
    #     total_rankings += ranking * count
    #     if count/iterations < 0.001:
    #         continue
    #     print(f"  {ranking}: {percent(count)}")
    # mean_ranking = round(total_rankings/iterations*100)/100
    # print(f"  mean: {mean_ranking}")
    # bar_graph("BYU B12 Ranking Probabilities", labels, Y, "Ranking", caption=f"BYU's final B12 regular season ranking (no tiebreakers). Mean: {mean_ranking}")
    # print("BYU B12 Rankings Detailed:")
    # for ranking_info, count in sorted(tied_rankings.items(), key=lambda item: 10*item[0][0] + item[0][1]):
    #     if count/iterations < 0.01:
    #         continue
    #     ranking, tied_count = ranking_info
    #     ranking_str = f"{ranking} outright" if tied_count == 1 else f"T{ranking}({tied_count})"
    #     print(f"  {ranking_str}: {percent(count)}")

    # TODO consider making a P(win B12) bar chart
    # team_ids = get_team_ids(2024)
    # win_conference_counts = defaultdict(lambda: 0)
    # for teams, count in ccg_outcomes.items():
    #     pwin = scrape_win_probability(*teams, True, team_ids)
    #     win_conference_counts[teams[0]] += count * pwin
    #     win_conference_counts[teams[1]] += count * (1 - pwin)

    # print("Probability of Winning Conference:")
    # labels = []
    # Y = []
    # for team in sorted(original_b12.team_names):
    #     labels.append(team)
    #     Y.append(round(win_conference_counts[team]/iterations*1000)/10)
    #     print(f"  {team}: {percent(win_conference_counts[team])}")

    # bar_graph("B12 Winner Probabilities", labels, Y, teams=[(team,) for team in labels], caption="Probability of each team winning the B12")
