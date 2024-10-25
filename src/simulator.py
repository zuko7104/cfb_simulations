from scraper import get_season_snapshot, get_team_ids, scrape_win_probability
from sports.season import TeamName, SeasonSnapshot
import random
from collections import defaultdict
import os
import datetime
from dataclasses import dataclass, field
from typing import TypeAlias, Callable

import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox


today = datetime.date.today()

TeamNames: TypeAlias = tuple[TeamName, ...]
Standing: TypeAlias = tuple[int, int]


@dataclass
class BasicTeamSeasonOutcomes:
    total_seasons: int = 0
    made_ccg: int = 0
    standing: dict[Standing, int] = field(default_factory=lambda: defaultdict(lambda: 0))
    ccg_participants: dict[TeamNames, int] = field(default_factory=lambda: defaultdict(lambda: 0))


@dataclass
class TeamSeasonOutcomes:
    total_seasons: int = 0
    win_counts: dict[int, int] = field(default_factory=lambda: defaultdict(lambda: 0))
    win_counts_in_ccg: dict[int, int] = field(default_factory=lambda: defaultdict(lambda: 0))
    made_ccg: int = 0
    standing: dict[Standing, int] = field(default_factory=lambda: defaultdict(lambda: 0))
    lost_to: dict[TeamNames, BasicTeamSeasonOutcomes] = field(default_factory=lambda: defaultdict(lambda: BasicTeamSeasonOutcomes()))


@dataclass
class ConferenceSeasonOutcomes:
    total_seasons: int = 0
    teams: dict[TeamName, TeamSeasonOutcomes] = field(default_factory=lambda: defaultdict(lambda: TeamSeasonOutcomes()))
    ccg_participants: dict[TeamNames, int] = field(default_factory=lambda: defaultdict(lambda: 0))

@dataclass
class ScenarioOutcomes:
    description: str
    conditions: list[Callable[[SeasonSnapshot], bool]]
    total_seasons: int = 0
    ccg_participants: dict[TeamNames, int] = field(default_factory=lambda: defaultdict(lambda: 0))

    def __contains__(self, rolled_season: SeasonSnapshot) -> bool:
        return all(condition(rolled_season) for condition in self.conditions)



def get_team_logo(team: TeamName):
    return plt.imread(f"assets/{team.lower().replace(" ", "_")}.png") 



simulation_tag = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
simulation_dir = f"results/{simulation_tag}"


original_season = get_season_snapshot(2024)
season = original_season.filter("B12")
original_b12 = season.conference("B12")

def win_exactly(team: TeamName, wins: int) -> Callable[[SeasonSnapshot], bool]:
    return lambda roll: roll.team(team).wins == wins

def win_at_least(team: TeamName, wins: int) -> Callable[[SeasonSnapshot], bool]:
    return lambda roll: roll.team(team).wins >= wins

def win_out(team: TeamName) -> Callable[[SeasonSnapshot], bool]:
    original_team = original_season.team(team)
    loss_count = original_team.losses
    return lambda roll: roll.team(team).losses == loss_count

def beat(winner: TeamName, loser: TeamName) -> Callable[[SeasonSnapshot], bool]:
    return lambda roll: loser in roll.team(winner).wins_against

def win_out_except_possibly(team: TeamName, possible_losses: list[TeamName]) -> Callable[[SeasonSnapshot], bool]:
    original_team = original_season.team(team)
    allowed_losses = set(possible_losses) | original_team.losses_against
    return lambda roll: roll.team(team).losses_against.issubset(allowed_losses)

# iterations = 1000000
iterations = 100000
# iterations = 10000
# iterations = 1000
def percent(count: int, total: int = ...) -> str:
    if total is ...:
        total = iterations
    return f"{int((count/total)*1000)/10}%"

win_counts = defaultdict(lambda: 0)
win_counts_in_ccg = defaultdict(lambda: 0)
rankings = defaultdict(lambda: 0)
tied_rankings = defaultdict(lambda: 0)
ccg_outcomes = defaultdict(lambda: 0)
losses = defaultdict(lambda: defaultdict(lambda: 0))

interesting_scenarios = [
    ScenarioOutcomes("BYU 11-1\nISU, KSU win until their game", [win_exactly("BYU", 11), win_out_except_possibly("Kansas St", ["Iowa St"]), win_out_except_possibly("Iowa St", ["Kansas St"])]),
    ScenarioOutcomes("BYU 10-2\nISU, KSU win until their game", [win_exactly("BYU", 10), win_out_except_possibly("Kansas St", ["Iowa St"]), win_out_except_possibly("Iowa St", ["Kansas St"])]),
    ScenarioOutcomes("BYU 11-1\nISU win out", [win_exactly("BYU", 11), win_out("Iowa St")]),
    ScenarioOutcomes("BYU 10-2\nISU win out", [win_exactly("BYU", 10), win_out("Iowa St")]),
    ScenarioOutcomes("BYU 10-2\nISU win out\nKSU only lose to ISU", [win_exactly("BYU", 10), win_out("Iowa St"), win_exactly("Kansas St", 10)]),
    ScenarioOutcomes("BYU 11-1\nKSU win out", [win_exactly("BYU", 11), win_out("Kansas St")]),
    ScenarioOutcomes("BYU 11-1\nKSU win out\nISU only lose to KSU", [win_exactly("BYU", 11), win_out("Kansas St"), win_exactly("Iowa St", 11)]),
    ScenarioOutcomes("BYU 10-2\nKSU win out\nISU only lose to KSU", [win_exactly("BYU", 10), win_out("Kansas St"), win_exactly("Iowa St", 11)]),
    ScenarioOutcomes("BYU 10-2\nKSU 10-2, beat ISU\nISU only lose to KSU", [win_exactly("BYU", 10), win_exactly("Iowa St", 11), win_exactly("Kansas St", 10), beat("Kansas St", "Iowa St")]),
    ScenarioOutcomes("BYU 10-2\nKSU 10-2\nISU 10-2", [win_exactly("BYU", 10), win_exactly("Iowa St", 10), win_exactly("Kansas St", 10)]),
    ScenarioOutcomes("CO win out", [win_out("Colorado")]),
    ScenarioOutcomes("CO win out\nBYU 11-1", [win_out("Colorado"), win_exactly("BYU", 11)]),
    ScenarioOutcomes("CO win out\nBYU 10-2", [win_out("Colorado"), win_exactly("BYU", 10)]),
    ScenarioOutcomes("CO win out\nBYU 11-1\nISU win out", [win_out("Colorado"), win_exactly("BYU", 11), win_out("Iowa St")]),
    ScenarioOutcomes("CO win out\nBYU 11-1\nKSU win out", [win_out("Colorado"), win_exactly("BYU", 11), win_out("Kansas St")]),
    ScenarioOutcomes("CO win out\nBYU, ISU 11-1\nKSU win out", [win_out("Colorado"), win_exactly("BYU", 11), win_exactly("Iowa St", 11), win_out("Kansas St")]),
]

overall_outcomes = ConferenceSeasonOutcomes()

for i in range(iterations):
    if i % 1000 == 0:
        print("completed", i)
    rolled_season = season.roll(random.random)
    rolled_b12 = rolled_season.conference("B12")

    rolled_ccg_teams = tuple(sorted(rolled_b12.championship_game_participants))
    overall_outcomes.total_seasons += 1
    overall_outcomes.ccg_participants[rolled_ccg_teams] += 1

    for scenario in interesting_scenarios:
        if rolled_season in scenario:
            scenario.total_seasons += 1
            scenario.ccg_participants[rolled_ccg_teams] += 1
            if scenario.description == "CO win out\nBYU 11-1":
                print("-----------------------------------")
                print(rolled_ccg_teams, "in ccg")
                for team in sorted(rolled_b12.teams, key=lambda team: team.name):
                    print(team.name, team.record)
                for game in sorted(filter(lambda game: game.date >= today, rolled_season.games), key=lambda game: game.date):
                    print(game.winner, "over", game.opponent(game.winner))
                print("-----------------------------------")

    for team in rolled_b12.team_names:
        team_outcomes = overall_outcomes.teams[team]
        rolled_team = rolled_season.team(team)
        rolled_lost_to = tuple(sorted(rolled_team.losses_against))
        rolled_standing = rolled_b12.ranking(team)
        rolled_wins = rolled_team.wins
        
        lost_to_outcomes = team_outcomes.lost_to[rolled_lost_to]

        team_outcomes.total_seasons += 1
        lost_to_outcomes.total_seasons += 1

        team_outcomes.standing[rolled_standing] += 1
        lost_to_outcomes.standing[rolled_standing] += 1

        team_outcomes.win_counts[rolled_wins] += 1

        lost_to_outcomes.ccg_participants[rolled_ccg_teams] += 1

        if team in rolled_ccg_teams:
            team_outcomes.made_ccg += 1
            lost_to_outcomes.made_ccg += 1

            team_outcomes.win_counts_in_ccg[rolled_wins] += 1


    byu = rolled_season.team("BYU")
    win_counts[byu.wins] += 1
    ranking, tied_count = rolled_b12.ranking(byu.name)
    tied_rankings[(ranking, tied_count)] += 1
    rankings[ranking] += 1
    ccg_outcomes[tuple(sorted(rolled_b12.championship_game_participants))] += 1
    losses[tuple(sorted(byu.losses_against))]["total"] += 1
    losses[tuple(sorted(byu.losses_against))][ranking] += 1
    if byu.name in rolled_b12.championship_game_participants:
        win_counts_in_ccg[byu.wins] += 1
        losses[tuple(sorted(byu.losses_against))]["in_ccg"] += 1

os.mkdir(simulation_dir)

filename_start = f"{simulation_dir}/{simulation_tag}_"

def rounded_percent_str(probability: float | None) -> str:
    if probability is None:
        return  ""
    if probability > 1:
        probability = min(0.999, probability)
    return f"{round(probability * 1000) / 10}%"

def percent_to_color(percent: str, default: str="#555555"):
    if percent == "":
        return default
    try:
        prob = float(percent[:-1]) / 100
    except ValueError:
        return "w"

    red = round(0x33 * prob + 0xff * (1-prob))
    green = round(0xFF * prob + 0xff * (1-prob))
    blue = round(0x33 * prob + 0xff * (1-prob))
    color = f"#{red:02x}{green:02x}{blue:02x}"
    return color

def prob_in_ccg_given_specific_losses(team: TeamName, ccg_target: TeamName = ...) -> dict[TeamNames, float]:
    if ccg_target is ...:
        ccg_target = team
    team_outcomes = overall_outcomes.teams[team]
    result = {}
    for losses, outcomes in team_outcomes.lost_to.items():
        prob = sum(count for ccg_teams, count in outcomes.ccg_participants.items() if ccg_target in ccg_teams) / outcomes.total_seasons
        if prob > 0:
            result[losses] = prob
    return result

def prob_in_ccg_given_total_losses(team: TeamName, ccg_target: TeamName = ...) -> dict[int, float]:
    if ccg_target is ...:
        ccg_target = team
    team_outcomes = overall_outcomes.teams[team]
    ccg_made_counts: dict[int, int] = defaultdict(lambda: 0)
    losses_counts: dict[int, int] = defaultdict(lambda: 0)
    for losses, outcomes in team_outcomes.lost_to.items():
        count = sum(count for ccg_teams, count in outcomes.ccg_participants.items() if ccg_target in ccg_teams)
        ccg_made_counts[len(losses)] += count
        losses_counts[len(losses)] += outcomes.total_seasons
    return {total_losses: count / losses_counts[total_losses] for total_losses, count in ccg_made_counts.items()}

def table_in_ccg_prob_given_total_wins(ccg_target: TeamName = ...):
    team_probs = {team: prob_in_ccg_given_total_losses(team, ccg_target=ccg_target) for team in original_b12.team_names}
    max_losses = max(max(probs.keys()) for probs in team_probs.values())

    wins = [12 - losses for losses in range(max_losses + 1)]
    sorted_teams = sorted(original_b12.team_names, key=lambda team: overall_outcomes.teams[team].made_ccg, reverse=True)
    cells = [[rounded_percent_str(team_probs[team].get(losses)) for losses in range(max_losses + 1)] for team in sorted_teams]

    if ccg_target is ...:
        wins.append("Total")
        for team, row in zip(sorted_teams, cells):
            row.append(rounded_percent_str(overall_outcomes.teams[team].made_ccg / overall_outcomes.total_seasons))
    
    colors = [[percent_to_color(percent) for percent in row] for row in cells]
    
    fig = plt.figure(figsize=(15, 7))
    ax = plt.gca()
    fig.patch.set_visible(False)
    ax.set_title(f"Probability of {'Each Team' if ccg_target is ... else ccg_target} Making the CCG Given Total Wins")
    ax.axis("off")
    ax.axis("tight")
    table = ax.table(cells, colLabels=wins, rowLabels=sorted_teams, loc="center", cellColours=colors)
    table.scale(1.0, 1.5)
    fig.savefig(filename_start + f"{'all' if ccg_target is ... else ccg_target}-ccg-probs-given-total-wins-table.png")

def table_in_ccg_prob_given_specific_losses(ccg_target: TeamName = ...):
    # interesting_teams = ["BYU", "Iowa St", "Kansas St", "Texas Tech", "Cincinnati", "Colorado"]
    interesting_teams = ["BYU", "Iowa St", "Kansas St"]
    team_probs = {team: prob_in_ccg_given_specific_losses(team, ccg_target=ccg_target) for team in interesting_teams}

    sorted_team_probs = {team: [(teams, prob) for teams, prob in sorted(probs.items(), key=lambda item: 10 * len(item[0]) + (1 - item[1])) if prob > 0.01 and len(teams) <= 4] for team, probs in team_probs.items()}
    max_rows = max(len(probs) for probs in sorted_team_probs.values())

    cells = []
    for i in range(max_rows):
        row = []
        for team in interesting_teams:
            sorted_probs = sorted_team_probs[team]
            losses, prob = sorted_probs[i] if i < len(sorted_probs) else (("",), None)
            row += [", ".join(losses), rounded_percent_str(prob)]
        cells.append(row)
    colors = [[percent_to_color(percent, default="w") for percent in row] for row in cells]

    col_labels = []
    for team in interesting_teams:
        col_labels += [f"{team} Losses", f"{team if ccg_target is ... else ccg_target} CCG Prob"]

    fig = plt.figure(figsize=(30, 15))
    ax = plt.gca()
    fig.patch.set_visible(False)
    ax.set_title(f"Probability of {'Each Team' if ccg_target is ... else ccg_target} Making the CCG Given Specific Losses")
    ax.axis("off")
    ax.axis("tight")
    table = ax.table(cells, loc="center", colLabels=col_labels, cellColours=colors)
    table.scale(1.0, 1.5)
    fig.savefig(filename_start + f"{'all' if ccg_target is ... else ccg_target}-ccg-probs-given-specific-losses-table.png")

def table_interesting_scenarios(scenarios: list[ScenarioOutcomes] = ..., tag: str = "all"):
    if scenarios is ...:
        scenarios = interesting_scenarios
    interesting_teams = ["BYU", "Iowa St", "Kansas St", "Colorado"]

    cells = []
    cells.append([rounded_percent_str(scenario.total_seasons / overall_outcomes.total_seasons) for scenario in scenarios])
    for team in interesting_teams:
        row = []
        for scenario in scenarios:
            in_ccg = sum(count for ccg_teams, count in scenario.ccg_participants.items() if team in ccg_teams)
            row.append(rounded_percent_str(in_ccg / scenario.total_seasons))
        cells.append(row)
    colors = [[percent_to_color(percent, default="w") for percent in row] for row in cells]
    
    row_labels = ["Probability of Scenario"] + [f"{team} CCG Probability" for team in interesting_teams]
    col_labels = [scenario.description for scenario in scenarios]

    fig = plt.figure(figsize=(20, 4))
    ax = plt.gca()
    fig.patch.set_visible(False)
    ax.set_title(f"Interesting Scenarios")
    ax.axis("off")
    ax.axis("tight")
    table = ax.table(cells, colLabels=col_labels, rowLabels=row_labels, loc="lower center", cellColours=colors)
    table.scale(1.0, 1.5)
    table_cells = table.get_celld()
    for i in range(len(col_labels)):
        table_cells[(0,i)].set_height(3 * table_cells[(0,i)].get_height())
    fig.savefig(filename_start + f"{tag}-scenarios-table.png")


# table_in_ccg_prob_given_total_wins()
# table_in_ccg_prob_given_total_wins("BYU")
# table_in_ccg_prob_given_specific_losses()
# table_in_ccg_prob_given_specific_losses("BYU")
table_interesting_scenarios(interesting_scenarios[:5], "first")
table_interesting_scenarios(interesting_scenarios[5:10], "second")
table_interesting_scenarios(interesting_scenarios[10:], "colorado")

plt.show()
exit()

print("BYU Records:")
total_wins = 0
labels = []
win_labels = []
Y = []
for wins, count in sorted(win_counts.items(), key=lambda item: item[0]):
    labels.append(f"{wins}-{12-wins}")
    win_labels.append(f"{wins}")
    Y.append(round(count/iterations*1000)/10)
    total_wins += wins * count
    if count/iterations < 0.001:
        continue
    print(f"  {wins}-{12-wins}: {percent(count)}")
mean_wins = total_wins/iterations
mean_losses = 12 - mean_wins
mean_wins = round(mean_wins * 100) / 100
mean_losses = round(mean_losses * 100) / 100
print(f"  mean: {mean_wins}-{mean_losses}")

fig = plt.figure("BYU Record Probabilities")
ax = fig.add_axes((0.1, 0.2, 0.8, 0.7))
ax.set_title("BYU Record Probabilities")
ax.bar(labels, Y)
ax.bar_label(ax.containers[0], [f"{y}%" for y in Y])
ax.set_xlabel("Record")
ax.set_ylabel("Probability (%)")
ax.set_ylim(0, int((max(Y) + 12) / 10) * 10)
fig.text(0.5, 0.05, f"Regular season record probabilities. Mean: {mean_wins}-{mean_losses}", ha="center", fontsize=10)
fig.savefig(f"results/{simulation_tag}/{simulation_tag}_byu-record-probabilities.png")

fig = plt.figure("BYU Probability of Winning at Least N Games")
ax = fig.add_axes((0.1, 0.2, 0.8, 0.7))
ax.set_title("BYU Probability of Winning at Least N Games")
Y = [sum(Y[i:]) for i in range(len(Y))]
ax.bar(win_labels, Y)
ax.bar_label(ax.containers[0], [f"{y}%" for y in Y])
ax.set_xlabel("Minimum Wins")
ax.set_ylabel("Probability (%)")
ax.set_ylim(0, int((max(Y) + 12) / 10) * 10)
fig.text(0.5, 0.05, f"Probability of winning at least N games.", ha="center", fontsize=10)
fig.savefig(f"results/{simulation_tag}/{simulation_tag}_byu-min-wins-probabilities.png")

print("BYU B12 Rankings:")
total_rankings = 0
labels = []
Y = []
for ranking, count in sorted(rankings.items(), key=lambda item: item[0]):
    labels.append(str(ranking))
    Y.append(round(count/iterations*1000)/10)
    total_rankings += ranking * count
    if count/iterations < 0.001:
        continue
    print(f"  {ranking}: {percent(count)}")
mean_ranking = round(total_rankings/iterations*100)/100
print(f"  mean: {mean_ranking}")

fig = plt.figure("BYU B12 Ranking Probabilities")
ax = fig.add_axes((0.1, 0.2, 0.8, 0.7))
ax.set_title("BYU B12 Ranking Probabilities")
ax.bar(labels, Y)
ax.bar_label(ax.containers[0], [f"{y}%" for y in Y])
ax.set_xlabel("Ranking")
ax.set_ylabel("Probability (%)")
ax.set_ylim(0, int((max(Y) + 12) / 10) * 10)
fig.text(0.5, 0.05, f"BYU's final B12 regular season ranking (no tiebreakers). Mean: {mean_ranking}", wrap=True, ha="center", fontsize=10)
fig.savefig(f"results/{simulation_tag}/{simulation_tag}_byu-b12-ranking-probabilities.png")

print("BYU B12 Rankings Detailed:")
for ranking_info, count in sorted(tied_rankings.items(), key=lambda item: 10*item[0][0] + item[0][1]):
    if count/iterations < 0.01:
        continue
    ranking, tied_count = ranking_info
    ranking_str = f"{ranking} outright" if tied_count == 1 else f"T{ranking}({tied_count})"
    print(f"  {ranking_str}: {percent(count)}")

print("B12 CCG participants:")
labels = []
Y = []
for teams, count in sorted(ccg_outcomes.items(), key=lambda item: item[1], reverse=True):
    if count/iterations < 0.01:
        continue
    labels.append(teams)
    Y.append(round(count/iterations*1000)/10)
    print(f"  {teams[0]} v {teams[1]}: {percent(count)}")

fig = plt.figure("B12 CCG Participants", (10, 6))
ax = fig.add_axes((0.05, 0.2, 0.9, 0.6))
ax.set_title("B12 CCG Participants")
bars = ax.bar([",".join(label) for label in labels], Y)
ax.bar_label(ax.containers[0], [f"{y}%" for y in Y])
for bar, teams in zip(bars, labels):
    for i, team in enumerate(teams):
        logo = get_team_logo(team)
        imagebox = OffsetImage(logo, zoom=40 / max(logo.shape))
        ab = AnnotationBbox(imagebox, (bar.get_x() + bar.get_width() / 2, 0), xybox=(0.0, -60.0 - i*30), boxcoords="offset points", pad=0, xycoords='data', box_alignment=(0.5, -0.5), frameon=False)
        ax.add_artist(ab)
ax.set_xticks([])
# ax.set_xlabel("Team")
ax.set_ylabel("Probability (%)")
ax.set_ylim(0, int((max(Y) + 12) / 10) * 10)
fig.text(0.5, 0.01, f"Probabilities of various CCG Matchups. Matchups with probability less than 1% are omitted.", wrap=True, ha="center", fontsize=10)
fig.savefig(f"results/{simulation_tag}/{simulation_tag}_b12-ccg-matchup-probabilities.png")

print("Probability of Making CCG:")
labels = []
Y = []
for team in sorted(original_b12.team_names):
    count = sum(c for teams, c in ccg_outcomes.items() if team in teams)
    labels.append(team)
    Y.append(round(count / iterations * 1000) / 10)
    print(f"  {team}: {percent(count)}")

fig = plt.figure("Probability of Making CCG", (10, 6))
ax = fig.add_axes((0.05, 0.2, 0.9, 0.7))
ax.set_title("Probability of Making CCG")
bars = ax.bar(labels, Y)
ax.bar_label(ax.containers[0], [f"{y}%" for y in Y])
for bar, team in zip(bars, labels):
    logo = get_team_logo(team)
    imagebox = OffsetImage(logo, zoom=40 / max(logo.shape))
    ab = AnnotationBbox(imagebox, (bar.get_x() + bar.get_width() / 2, 0), xybox=(0.0, -60.0), boxcoords="offset points", pad=0, xycoords='data', box_alignment=(0.5, -0.5), frameon=False)
    ax.add_artist(ab)
ax.set_xticks([])
# ax.set_xlabel("Team")
ax.set_ylabel("Probability (%)")
ax.set_ylim(0, int((max(Y) + 12) / 10) * 10)
fig.text(0.5, 0.05, f"Probability of each team making the CCG", wrap=True, ha="center", fontsize=10)
fig.savefig(f"results/{simulation_tag}/{simulation_tag}_b12-team-ccg-probabilities.png")

team_ids = get_team_ids(2024)
win_conference_counts = defaultdict(lambda: 0)
for teams, count in ccg_outcomes.items():
    pwin = scrape_win_probability(*teams, True, team_ids)
    win_conference_counts[teams[0]] += count * pwin
    win_conference_counts[teams[1]] += count * (1 - pwin)

print("Probability of Winning Conference:")
labels = []
Y = []
for team in sorted(original_b12.team_names):
    labels.append(team)
    Y.append(round(win_conference_counts[team]/iterations*1000)/10)
    print(f"  {team}: {percent(win_conference_counts[team])}")

fig = plt.figure("Probability of Winning B12", (10, 6))
ax = fig.add_axes((0.05, 0.2, 0.9, 0.7))
ax.set_title("Probability of Winning B12")
bars = ax.bar(labels, Y)
ax.bar_label(ax.containers[0], [f"{y}%" for y in Y])
for bar, team in zip(bars, labels):
    logo = get_team_logo(team)
    imagebox = OffsetImage(logo, zoom=40 / max(logo.shape))
    ab = AnnotationBbox(imagebox, (bar.get_x() + bar.get_width() / 2, 0), xybox=(0.0, -60.0), boxcoords="offset points", pad=0, xycoords='data', box_alignment=(0.5, -0.5), frameon=False)
    ax.add_artist(ab)
ax.set_xticks([])
# ax.set_xlabel("Team")
ax.set_ylabel("Probability (%)")
ax.set_ylim(0, int((max(Y) + 12) / 10) * 10)
fig.text(0.5, 0.05, f"Probability of each team winning the B12", wrap=True, ha="center", fontsize=10)
fig.savefig(f"results/{simulation_tag}/{simulation_tag}_b12-winner-probabilities.png")

total_wins = 0
total_count = sum(count for count in win_counts_in_ccg.values())
print(f"BYU Regular Season Record when Made CCG:")
for wins, count in sorted(win_counts_in_ccg.items(), key=lambda item: item[0]):
    total_wins += wins * count
    print(f"  {wins}-{12-wins}: {percent(count, total_count)}")
mean_wins = total_wins/total_count
print(f"  mean: {mean_wins}-{12-mean_wins}")

print(f"BYU Probability of Making CCG Given Record:")
labels = []
Y = []
for wins, ccg_count in sorted(win_counts_in_ccg.items(), key=lambda item: item[0]):
    total_count = win_counts[wins]
    labels.append(f"{wins}-{12-wins}")
    Y.append(round(ccg_count/total_count*1000)/10)
    print(f"  {wins}-{12-wins}: {int(1000*(ccg_count/total_count))/10}%")

fig = plt.figure("BYU Probability of Making CCG Given Record")
ax = fig.add_axes((0.1, 0.2, 0.8, 0.7))
ax.set_title("BYU Probability of Making CCG Given Record")
ax.bar(labels, Y)
ax.bar_label(ax.containers[0], [f"{y}%" for y in Y])
ax.set_xlabel("Record")
ax.set_ylabel("Probability (%)")
ax.set_ylim(0, int((max(Y) + 12) / 10) * 10)
fig.text(0.5, 0.05, f"BYU's probability of making the CCG with different regular season records", wrap=True, ha="center", fontsize=10)
fig.savefig(f"results/{simulation_tag}/{simulation_tag}_byu-ccg-probabilities-given-record.png")

print(f"BYU Probability of Making CCG Given Losses Against:")
for losses_against, details in sorted(losses.items(), key=lambda item: f"{len(item[0])}{"".join(item[0])}"):
    print(f"  {', '.join(losses_against)}: {percent(details["in_ccg"], details["total"])} ({details["total"]} occurrences)")

labels = []
Y = []
for losses_against, details in sorted(filter(lambda item: len(item[0]) == 1, losses.items()), key=lambda item: f"{len(item[0])}{"".join(item[0])}"):
    labels.append(losses_against[0])
    Y.append(round(details["in_ccg"]/details["total"]*1000)/10)

fig = plt.figure("1-Loss BYU Probability of Making CCG Given Loss", (7, 6))
ax = fig.add_axes((0.1, 0.2, 0.8, 0.7))
ax.set_title("1-Loss BYU Probability of Making CCG Given Loss")
bars = ax.bar(labels, Y)
ax.bar_label(ax.containers[0], [f"{y}%" for y in Y])
for bar, team in zip(bars, labels):
    logo = get_team_logo(team)
    imagebox = OffsetImage(logo, zoom=40 / max(logo.shape))
    ab = AnnotationBbox(imagebox, (bar.get_x() + bar.get_width() / 2, 0), xybox=(0.0, -60.0), boxcoords="offset points", pad=0, xycoords='data', box_alignment=(0.5, -0.5), frameon=False)
    ax.add_artist(ab)
ax.set_xticks([])
# ax.set_xlabel("Team")
ax.set_ylabel("Probability (%)")
ax.set_ylim(0, int((max(Y) + 12) / 10) * 10)
fig.text(0.5, 0.05, f"BYU's probability of making the CCG given a single loss against different teams", wrap=True, ha="center", fontsize=10)
fig.savefig(f"results/{simulation_tag}/{simulation_tag}_1-loss-byu-ccg-probabilities.png")

labels = []
Y = []
for losses_against, details in sorted(filter(lambda item: len(item[0]) == 2, losses.items()), key=lambda item: f"{len(item[0])}{"".join(item[0])}"):
    labels.append(losses_against)
    Y.append(round(details["in_ccg"]/details["total"]*1000)/10)

fig = plt.figure("2-Loss BYU Probability of Making CCG Given Losses", (10, 6))
ax = fig.add_axes((0.05, 0.2, 0.9, 0.6))
ax.set_title("2-Loss BYU Probability of Making CCG Given Losses")
bars = ax.bar([",".join(label) for label in labels], Y)
ax.bar_label(ax.containers[0], [f"{y}%" for y in Y])
for bar, teams in zip(bars, labels):
    for i, team in enumerate(teams):
        logo = get_team_logo(team)
        imagebox = OffsetImage(logo, zoom=40 / max(logo.shape))
        ab = AnnotationBbox(imagebox, (bar.get_x() + bar.get_width() / 2, 0), xybox=(0.0, -60.0 - i*30), boxcoords="offset points", pad=0, xycoords='data', box_alignment=(0.5, -0.5), frameon=False)
        ax.add_artist(ab)
ax.set_xticks([])
# ax.set_xlabel("Team")
ax.set_ylabel("Probability (%)")
ax.set_ylim(0, int((max(Y) + 12) / 10) * 10)
fig.text(0.5, 0.01, f"BYU's probability of making the CCG given two losses against different teams", wrap=True, ha="center", fontsize=10)
fig.savefig(f"results/{simulation_tag}/{simulation_tag}_2-loss-byu-ccg-probabilities.png")

plt.show()
