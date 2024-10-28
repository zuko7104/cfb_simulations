import scraper
from sports import outcomes
from sports.outcomes import ScenarioOutcomes
from simulator import Simulator
from figures import ConferenceFigures
from sports.season import ConferenceName
import datetime
import os
import argparse


def main(iterations: int = 100000, year: int = 2024, conference: ConferenceName = "B12", save_figures: bool = True, show_figures: bool = True):
    season = scraper.get_season_snapshot(year)
    if conference:
        season = season.filter(conference)

    simulation_tag = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    simulation_dir = f"results/{simulation_tag}"

    scenarios = [
        ScenarioOutcomes("BYU 11-1\nISU, KSU win until their game", [outcomes.win_exactly("BYU", 11), outcomes.win_out_except_possibly(season, "Kansas St", ["Iowa St"]), outcomes.win_out_except_possibly(season, "Iowa St", ["Kansas St"])]),
        ScenarioOutcomes("BYU 10-2\nISU, KSU win until their game", [outcomes.win_exactly("BYU", 10), outcomes.win_out_except_possibly(season, "Kansas St", ["Iowa St"]), outcomes.win_out_except_possibly(season, "Iowa St", ["Kansas St"])]),
        ScenarioOutcomes("BYU 11-1\nISU win out", [outcomes.win_exactly("BYU", 11), outcomes.win_out(season, "Iowa St")]),
        ScenarioOutcomes("BYU 10-2\nISU win out", [outcomes.win_exactly("BYU", 10), outcomes.win_out(season, "Iowa St")]),
        ScenarioOutcomes("BYU 10-2\nISU win out\nKSU only lose to ISU", [outcomes.win_exactly("BYU", 10), outcomes.win_out(season, "Iowa St"), outcomes.win_exactly("Kansas St", 10)]),
        ScenarioOutcomes("BYU 11-1\nKSU win out", [outcomes.win_exactly("BYU", 11), outcomes.win_out(season, "Kansas St")]),
        ScenarioOutcomes("BYU 11-1\nKSU win out\nISU only lose to KSU", [outcomes.win_exactly("BYU", 11), outcomes.win_out(season, "Kansas St"), outcomes.win_exactly("Iowa St", 11)]),
        ScenarioOutcomes("BYU 10-2\nKSU win out\nISU only lose to KSU", [outcomes.win_exactly("BYU", 10), outcomes.win_out(season, "Kansas St"), outcomes.win_exactly("Iowa St", 11)]),
        ScenarioOutcomes("BYU 10-2\nKSU 10-2, beat ISU\nISU only lose to KSU", [outcomes.win_exactly("BYU", 10), outcomes.win_exactly("Iowa St", 11), outcomes.win_exactly("Kansas St", 10), outcomes.beat("Kansas St", "Iowa St")]),
        ScenarioOutcomes("BYU 10-2\nKSU 10-2\nISU 10-2", [outcomes.win_exactly("BYU", 10), outcomes.win_exactly("Iowa St", 10), outcomes.win_exactly("Kansas St", 10)]),
        ScenarioOutcomes("CO win out", [outcomes.win_out(season, "Colorado")]),
        ScenarioOutcomes("CO win out\nBYU 11-1", [outcomes.win_out(season, "Colorado"), outcomes.win_exactly("BYU", 11)]),
        ScenarioOutcomes("CO win out\nBYU 10-2", [outcomes.win_out(season, "Colorado"), outcomes.win_exactly("BYU", 10)]),
        ScenarioOutcomes("CO win out\nBYU 11-1\nISU win out", [outcomes.win_out(season, "Colorado"), outcomes.win_exactly("BYU", 11), outcomes.win_out(season, "Iowa St")]),
        ScenarioOutcomes("CO win out\nBYU 11-1\nKSU win out", [outcomes.win_out(season, "Colorado"), outcomes.win_exactly("BYU", 11), outcomes.win_out(season, "Kansas St")]),
        ScenarioOutcomes("CO win out\nBYU, ISU 11-1\nKSU win out", [outcomes.win_out(season, "Colorado"), outcomes.win_exactly("BYU", 11), outcomes.win_exactly("Iowa St", 11), outcomes.win_out(season, "Kansas St")]),
    ]

    simulator = Simulator(season, scenarios)

    simulator.simulate(iterations)

    figs = ConferenceFigures(conference, simulator.conference_outcomes[conference], simulator.scenarios, simulator.week_outcomes[conference])

    figs.all_figures(["BYU", "Iowa St", "Kansas St", "Colorado"], "BYU")

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
    # TODO Other options are not implemented
    # parser.add_argument("--year", default=2024, type=int, help="The season to run simulations on (default: 2024)")
    # parser.add_argument("--conference", default="B12", help="The conference to run simulations on (default: B12)")

    parsed = parser.parse_args(args)
    return parsed.iterations, 2024, "B12", parsed.save_figs, parsed.show_figs


if __name__ == "__main__":
    main(*parse_args())
