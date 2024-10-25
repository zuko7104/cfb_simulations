
import datetime
import requests
from bs4 import BeautifulSoup
import re
import datetime
from typing import Iterable, Callable

from sports.season import Game, TeamName, Conference, SeasonSnapshot
from sports import tiebreakers


_game_pattern = re.compile(r"(?P<date>[1-9][0-9]{3}-[0-1][0-9]-[0-3][0-9])\s*(?P<visit1>@?)(?P<name1>(?:[^ ]+ ??)+)\s*(?P<score1>[0-9]+)\s*(?P<visit2>@?)(?P<name2>(?:[^ ]+ ??)+)\s*(?P<score2>[0-9]+) *(?:(?P<overtime>O[1-9])|(?P<scheduled>Sch))? *(?P<neutralsite>[^\n]*)?")
_win_probability_pattern = re.compile(r"pwin=\[(?P<pwina>[0-9\.]+),.*?\]")
_championship_seeders = {"B12": tiebreakers.big12_championship_seeder}


def scrape_team_ids(year: int) -> dict[TeamName, int]:
    del year
    url = "https://masseyratings.com/json/namesearch.php?s=587076&ct=10&mhr=1"
    data = requests.get(url).json()

    team_ids: dict[TeamName, int] = {}
    for team in data.values():
        try:
            id = team["value"]
        except:
            continue
        team_data = BeautifulSoup(requests.get(f"https://masseyratings.com/school?t={id}").content, "html.parser")
        name = team_data.find(id="title0").find("a").text
        team_ids[name] = id
    return team_ids


def _serialize_team_ids(team_ids: dict[TeamName, int]) -> str:
    return "\n".join(f"{team},{id}" for team, id in team_ids.items())


def _deserialize_team_ids(lines: Iterable[str]) -> dict[TeamName, int]:
    team_ids: dict[TeamName, int] = {}
    for line in lines:
        name, id = line.strip().split(",")
        team_ids[name] = id
    return team_ids


def get_team_ids(year: int) -> dict[TeamName, int]:
    try:
        with open(f"data/{year}_team_ids.csv", "r") as f:
            return _deserialize_team_ids(f.readlines())
    except Exception:
        print("scraping team ids...")
        team_ids = scrape_team_ids(year)
        print("done")
        with open(f"data/{year}_team_ids.csv", "w") as f:
            f.write(_serialize_team_ids(team_ids))
        return team_ids


def scrape_win_probability(team_a: TeamName, team_b: TeamName, neutral: bool, team_ids: dict[TeamName, int]) -> float:
    h = 0 if neutral else -1
    url = f"https://masseyratings.com/game.php?s0=587076&oid0={team_ids[team_a]}&h={h}&s1=587076&oid1={team_ids[team_b]}"
    page = requests.get(url).text
    for pwin in _win_probability_pattern.findall(page):
        return float(pwin)


def scrape_games(year: int, get_win_probability: Callable[[TeamName, TeamName, bool], float]) -> set[Game]:
    url = f"https://masseyratings.com/scores.php?s=cf{year}&sub=fbs&all=1&sch=on"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    data = soup.find("pre").text
    games: set[Game] = set()
    for match in _game_pattern.findall(data):
        date, visit1, name1, score1, visit2, name2, score2, overtime, scheduled, neutralsite = match
        team_a, team_b = (name2, name1) if visit1 else (name1, name2)
        neutral = bool(neutralsite.strip())
        score = (int(score2), int(score1)) if visit1 else (int(score1), int(score2))
        team_a_win_probability = None
        if (0, 0) == score:
            score = None
            team_a_win_probability = get_win_probability(team_a, team_b, neutral)
        game = Game(datetime.datetime.strptime(date, "%Y-%m-%d").date(), team_a, team_b, neutral, score, team_a_win_probability)
        games.add(game)
    return games
    

def get_conferences(year: int) -> set[Conference]:
    del year
    # name_to_url = {
    #     "CUSA": "https://masseyratings.com/cf2024/11312",
    #     "MAC": "https://masseyratings.com/cf2024/12526",
    #     "MWC": "https://masseyratings.com/cf2024/12734",
    #     "AAC": "https://masseyratings.com/cf2024/200137",
    #     "SBC": "https://masseyratings.com/cf2024/14238",
    #     "ACC": "https://masseyratings.com/cf2024/10423",
    #     "P12": "https://masseyratings.com/cf2024/107818",
    #     "B12": "https://masseyratings.com/cf2024/10686",
    #     "B10": "https://masseyratings.com/cf2024/10678",
    #     "SEC": "https://masseyratings.com/cf2024/14028",
    # }
    name_to_teams = {
        "CUSA": ["Liberty", "WKU", "Sam Houston St", "Jacksonville St", "Florida Intl", "New Mexico St", "Louisiana Tech", "MTSU", "UTEP", "Kennesaw"],
        "MAC": ["Toledo", "Ohio", "N Illinois", "Miami OH", "Buffalo", "E Michigan", "W Michigan", "Bowling Green", "C Michigan", "Ball St", "Akron", "Kent"],
        "MWC": ["Boise St", "UNLV", "Fresno St", "San Jose St", "Nevada", "San Diego St", "Colorado St", "Air Force", "Wyoming", "New Mexico", "Hawaii", "Utah St"],
        "AAC": ["Memphis", "Tulane", "Army", "Navy", "North Texas", "East Carolina", "South Florida", "UT San Antonio", "Charlotte", "FL Atlantic", "Rice", "Tulsa", "UAB", "Temple"],
        "SBC": ["James Madison", "Louisiana", "Coastal Car", "Ga Southern", "Texas St", "ULM", "Marshall", "South Alabama", "Arkansas St", "Old Dominion", "Appalachian St", "Georgia St", "Troy", "Southern Miss"],
        "ACC": ["Clemson", "Miami FL", "Pittsburgh", "SMU", "Louisville", "Georgia Tech", "Duke", "Syracuse", "Boston College", "California", "Virginia", "Virginia Tech", "North Carolina", "Florida St", "NC State", "Stanford", "Wake Forest"],
        "P12": ["Washington St", "Oregon St"],
        "B12": ["Iowa St", "BYU", "Kansas St", "Texas Tech", "Arizona St", "Utah", "West Virginia", "Oklahoma St", "Cincinnati", "Colorado", "Arizona", "TCU", "UCF", "Baylor", "Houston", "Kansas"],
        "B10": ["Oregon", "Penn St", "Ohio St", "Michigan", "Indiana", "Iowa", "USC", "Wisconsin", "Illinois", "Washington", "Nebraska", "Minnesota", "Rutgers", "Michigan St", "Maryland", "Northwestern", "UCLA", "Purdue"],
        "SEC": ["Texas", "Georgia", "Alabama", "Tennessee", "LSU", "Texas A&M", "Mississippi", "Oklahoma", "Missouri", "Arkansas", "South Carolina", "Kentucky", "Florida", "Vanderbilt", "Auburn", "Mississippi St"],
    }


    conferences: set[Conference] = set()
    for name, teams in name_to_teams.items():
        conferences.add(Conference(name, teams, None, True, _championship_seeders.get(name)))
    return conferences


def get_season_snapshot(year: int) -> SeasonSnapshot:
    date = datetime.date.today()

    try:
        with open(f"data/{str(date)}_season.txt", "r") as f:
            season = SeasonSnapshot.deserialize(f.readlines(), lambda conf: _championship_seeders.get(conf))
    except Exception:
        print("constructing season...")
        team_ids = get_team_ids(year)
        def get_win_probability(team_a: TeamName, team_b: TeamName, neutral: bool) -> float:
            return scrape_win_probability(team_a, team_b, neutral, team_ids)
        games = scrape_games(year, get_win_probability)
        conferences = get_conferences(year)
        season = SeasonSnapshot(year, conferences, games)
        print("done")
        with open(f"data/{str(date)}_season.txt", "w") as f:
            f.write("\n".join(season.serialize()))

    return season


# months = {
#     "january": 1,
#     "february": 2,
#     "march": 3,
#     "april": 4,
#     "may": 5,
#     "june": 6,
#     "july": 7,
#     "august": 8,
#     "september": 9,
#     "october": 10,
#     "november": 11,
#     "december": 12,
# }
# dated_tables = soup.find_all(class_="ResponsiveTable")
# print(len(dated_tables), "dates to inspect")

# for dated_table in dated_tables:
#     date_str = dated_table.find(class_="Table__Title").text.strip()
#     parts = [part.strip() for part in date_str.split(" ")]
#     year = int(parts[-1])
#     day = int(parts[-2].strip(","))
#     month = months[parts[-3].lower()]
#     date = datetime.date(year, month, day)
#     print("----------")
#     print(str(date))

#     game_rows = dated_table.find_all(class_="Table__TR--sm")
#     print(len(game_rows), "games to inspect")
#     for game_row in game_rows:
#         team_a = game_row.find(class_="Table__Team away").find_all(class_="AnchorLink")[1].text.strip()
#         team_b = game_row.find_all(class_="Table__Team")[-1].find_all(class_="AnchorLink")[1].text.strip()
#         neutral = False
#         game_url = game_row.find(class_="teams__col").find(class_="AnchorLink")["href"]
#         # team_b = game_row.find(class_="home").find_all(class_="AnchorLink")[1].text.strip()
#         # away_cell = game_row.find(class_="away")
#         # away_name = away_cell.find_all(class_="AnchorLink")[1].text.strip()
#         print(team_a, "@", team_b, ":", game_url)
    
#     break


# url = "https://www.espn.com/college-football/schedule/_/week/1/year/2024/seasontype/2"
# page = requests.get(url)

# print(page.text)