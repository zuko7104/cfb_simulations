import scraper
from sports import outcomes
from sports.outcomes import win_exactly, win_out, win_out_except_possibly, beat, win_out_except, any_outcome, win_at_most
from sports.outcomes import ScenarioOutcomes
from simulator import Simulator
from figures import ConferenceFigures
from sports.season import ConferenceName
import datetime
import os
import argparse
import itertools
import concurrent.futures


def simulate_scenario(iterations: int, simulator: Simulator, scenario: ScenarioOutcomes) -> ScenarioOutcomes:
    try:
        result = simulator.simulate_scenario(scenario, iterations)
        return result
    except ValueError as e:
        print(f"ERROR: scenario failed: {scenario.description(", ")}")
        return None


def simulate_season(iterations: int, simulator: Simulator) -> Simulator:
    simulator.simulate(iterations)
    return simulator


def main(iterations: int = 100000, year: int = 2024, conference: ConferenceName = "B12", entire_season: bool = True, structured_scenarios: bool = True, save_figures: bool = True, show_figures: bool = True):
    season = scraper.get_season_snapshot(year)
    if conference:
        season = season.filter(conference)

    simulation_tag = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    simulation_dir = f"results/{simulation_tag}"

    scenarios = [
        ScenarioOutcomes(any_outcome()),
        ScenarioOutcomes(win_out(season, "Colorado")),
        ScenarioOutcomes(win_out(season, "Colorado"), win_out(season, "Kansas St"),),
        ScenarioOutcomes(win_exactly(season, "Colorado", 9), win_out(season, "Kansas St"),),
        ScenarioOutcomes(win_at_most(season, "Colorado", 8), win_out(season, "Kansas St"),),
        ScenarioOutcomes(win_out(season, "Colorado"), win_out(season, "Iowa St"),),
        ScenarioOutcomes(win_exactly(season, "Colorado", 9), win_out(season, "Iowa St"),),
        ScenarioOutcomes(win_at_most(season, "Colorado", 8), win_out(season, "Iowa St"),),
        ScenarioOutcomes(win_out(season, "Colorado"), win_out(season, "West Virginia"), win_at_most(season, "Kansas St", 9), win_at_most(season, "Iowa St", 9)),
        ScenarioOutcomes(win_exactly(season, "Colorado", 9), win_out(season, "West Virginia"), win_at_most(season, "Kansas St", 9), win_at_most(season, "Iowa St", 9)),
        ScenarioOutcomes(win_at_most(season, "Colorado", 8), win_out(season, "West Virginia"), win_at_most(season, "Kansas St", 9), win_at_most(season, "Iowa St", 9)),
        ScenarioOutcomes(win_out(season, "Colorado"), win_out(season, "Arizona St"), win_exactly(season, "Iowa St", 10)),
        ScenarioOutcomes(win_exactly(season, "Colorado", 9), win_out(season, "Arizona St"), win_exactly(season, "Iowa St", 10)),
        ScenarioOutcomes(win_at_most(season, "Colorado", 8), win_out(season, "Arizona St"), win_exactly(season, "Iowa St", 10)),
        ScenarioOutcomes(win_out(season, "Colorado"), win_out(season, "Arizona St"), win_at_most(season, "Iowa St", 9)),
        ScenarioOutcomes(win_exactly(season, "Colorado", 9), win_out(season, "Arizona St"), win_at_most(season, "Iowa St", 9)),
        ScenarioOutcomes(win_at_most(season, "Colorado", 8), win_out(season, "Arizona St"), win_at_most(season, "Iowa St", 9)),
    ]

    simulator = Simulator(season, scenarios)

    if entire_season:
        with concurrent.futures.ProcessPoolExecutor() as executor:
            groups = os.process_cpu_count()
            args = ([iterations // groups] * groups, [simulator.shallow_clone() for _ in range(groups)])
            args[0][-1] += iterations % groups
            for simulated in executor.map(simulate_season, *args):
                simulator |= simulated

    figs = ConferenceFigures(conference, simulator.conference_outcomes[conference], simulator.scenarios, simulator.week_outcomes[conference])

    if entire_season:
        figs.all_figures(["BYU", "Colorado", "Kansas St", "Iowa St", "West Virginia", "Arizona St"], "BYU")
        figs.table_week("Colorado")
        figs.table_week("Texas Tech")
        figs.table_week("Iowa St")
        figs.table_week("Kansas St")

    if structured_scenarios:
        opponent_condition_lists = [
            [any_outcome()],
            [win_out(season, "Colorado")],
            [win_out(season, "Colorado"), win_out(season, "Kansas St"),],
            [win_exactly(season, "Colorado", 9), win_out(season, "Kansas St"),],
            [win_at_most(season, "Colorado", 8), win_out(season, "Kansas St"),],
            [win_out(season, "Colorado"), win_out(season, "Iowa St"),],
            [win_exactly(season, "Colorado", 9), win_out(season, "Iowa St"),],
            [win_at_most(season, "Colorado", 8), win_out(season, "Iowa St"),],
            [win_out(season, "Colorado"), win_out(season, "West Virginia"), win_at_most(season, "Kansas St", 9), win_at_most(season, "Iowa St", 9)],
            [win_exactly(season, "Colorado", 9), win_out(season, "West Virginia"), win_at_most(season, "Kansas St", 9), win_at_most(season, "Iowa St", 9)],
            [win_at_most(season, "Colorado", 8), win_out(season, "West Virginia"), win_at_most(season, "Kansas St", 9), win_at_most(season, "Iowa St", 9)],
            [win_out(season, "Colorado"), win_out(season, "Arizona St"), win_exactly(season, "Iowa St", 10)],
            [win_exactly(season, "Colorado", 9), win_out(season, "Arizona St"), win_exactly(season, "Iowa St", 10)],
            [win_at_most(season, "Colorado", 8), win_out(season, "Arizona St"), win_exactly(season, "Iowa St", 10)],
            [win_out(season, "Colorado"), win_out(season, "Arizona St"), win_at_most(season, "Iowa St", 9)],
            [win_exactly(season, "Colorado", 9), win_out(season, "Arizona St"), win_at_most(season, "Iowa St", 9)],
            [win_at_most(season, "Colorado", 8), win_out(season, "Arizona St"), win_at_most(season, "Iowa St", 9)],
        ]
        byu_conditions = [
            any_outcome(),
            win_exactly(season, "BYU", 12),
            win_exactly(season, "BYU", 11),
            win_exactly(season, "BYU", 10),
        ]
        byu = season.team("BYU")
        for losses in sorted(list(itertools.combinations(byu.remaining_opponents, 2)), key=lambda ls: f"{len(ls)}{','.join(ls)}"):
            byu_conditions.append(win_out_except(season, "BYU", set(losses)))

        byu_conditions_count = len(byu_conditions)
        opponent_conditions_count = len(opponent_condition_lists)

        conditions_table: list[list[ScenarioOutcomes]] = [[... for _ in range(opponent_conditions_count)] for _ in range(byu_conditions_count)]
        conditions_rows: list[str] = list(map(str, byu_conditions))
        conditions_columns: list[str] = ["\n".join(map(str, conditions)) for conditions in opponent_condition_lists]

        args = ([], [], [])
        indices_list = []
        for i, byu_condition in enumerate(byu_conditions):
            for j, opponent_conditions in enumerate(opponent_condition_lists):
                scenario = ScenarioOutcomes(byu_condition, *opponent_conditions)
                indices_list.append((i, j))
                args[0].append(iterations)
                args[1].append(simulator)
                args[2].append(scenario)
        with concurrent.futures.ProcessPoolExecutor() as executor:
            for indices, scenario in zip(indices_list, executor.map(simulate_scenario, *args)):
                i, j = indices
                conditions_table[i][j] = scenario
        # figs.table_structured_scenarios("BYU", conditions_table, conditions_rows, conditions_columns)
        figs.table_structured_scenarios("BYU", [row[:6] for row in conditions_table], conditions_rows, conditions_columns[:6])
        figs.table_structured_scenarios("BYU", [row[6:12] for row in conditions_table], conditions_rows, conditions_columns[6:12])
        figs.table_structured_scenarios("BYU", [row[12:] for row in conditions_table], conditions_rows, conditions_columns[12:])
        # figs.table_structured_scenarios("Iowa St", conditions_table, conditions_rows, conditions_columns, False)
        # figs.table_structured_scenarios("Kansas St", conditions_table, conditions_rows, conditions_columns, False)
        # figs.table_structured_scenarios("Colorado", conditions_table, conditions_rows, conditions_columns, False)

    if save_figures:
        os.mkdir(simulation_dir)
        filename_start = f"{simulation_dir}/{simulation_tag}_"
        figs.save(filename_start)

    if show_figures:
        figs.show()


def parse_args(args: list[str] | None = None) -> tuple[int, int, ConferenceName, bool]:
    parser = argparse.ArgumentParser()

    parser.add_argument("--iterations", type=int, default=100000, help="The number of simulation iterations to run (default: 100000)")
    parser.add_argument("--no-save-figs", dest="save_figs", action="store_false", help="Don't save the figures (default: save them)")
    parser.add_argument("--show-figs", action="store_true", help="Show the figures")
    parser.add_argument("--tiebreakers", action="store_true", help="Simulate the tiebreaker scenarios")
    parser.add_argument("--no-season-outcomes", dest="season_outcomes", action="store_false", help="Don't simulate the regular season outcomes")
    # TODO Other options are not implemented
    # parser.add_argument("--year", default=2024, type=int, help="The season to run simulations on (default: 2024)")
    # parser.add_argument("--conference", default="B12", help="The conference to run simulations on (default: B12)")

    parsed = parser.parse_args(args)
    return parsed.iterations, 2024, "B12", parsed.season_outcomes, parsed.tiebreakers, parsed.save_figs, parsed.show_figs


if __name__ == "__main__":
    main(*parse_args())
