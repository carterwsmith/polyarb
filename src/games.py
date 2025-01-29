"""
Interaction with ESPN and NBA API to scrape NBA data.
"""

from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional

from nba_api.live.nba.endpoints.scoreboard import ScoreBoard

from rich.progress import Progress, SpinnerColumn, TextColumn

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

from src.constants import OUTCOMES_PATH


class NBAGame:
    """
    Holds data for an NBA game at some time.
    """

    def __init__(self, away_team: str, home_team: str, time: datetime):
        self.away_team = away_team
        self.home_team = home_team
        self.time = time


class NBATeamGameResult:
    """
    Holds data for a single team and a binary result.
    """

    def __init__(self, team_name: str, result: int):
        self.team_name = team_name
        self.result = result


class NBASlate:
    """
    Holds data for a single day's NBA games, including single-team results of completed games.
    """

    def __init__(
        self,
        date: datetime,
        results: List[NBATeamGameResult],
        incomplete_games: Optional[List[NBAGame]] = None,
    ):
        self.date = date
        self.results = results
        self.incomplete_games = incomplete_games

    def _format_outcomes(self) -> Dict:
        return {
            f"{self.date.strftime('%Y-%m-%d')}": {
                final.team_name: final.result for final in self.results
            }
        }

    def outcomes(self) -> str:
        return json.dumps(self._format_outcomes(), indent=4)

    def __str__(self) -> str:
        return json.dumps(
            {
                "date": self.date.strftime("%Y-%m-%d"),
                "results": [
                    {
                        "team": result.team_name,
                        "result": "win" if result.result == 1 else "loss",
                    }
                    for result in self.results
                ],
                "incomplete_games": [
                    {
                        "away_team": game.away_team,
                        "home_team": game.home_team,
                        "time": game.time.strftime("%I:%M %p"),
                    }
                    for game in self.incomplete_games
                ],
            }
        )


def get_live_teams() -> List[str]:
    """
    Get list of teams playing right now (from NBA API).

    Returns:
        List[str]: List of team names
    """
    scoreboard_games = ScoreBoard().games.get_dict()
    teams = []
    for game in scoreboard_games:
        if game["gameStatus"] != 2:
            continue
        teams.append(game["homeTeam"]["teamName"])
        teams.append(game["awayTeam"]["teamName"])
    return teams


def build_espn_url(date: datetime = datetime.today()) -> str:
    """
    Build ESPN URL for a given date.

    Args:
        date (datetime): Date to build URL for, defaults to today

    Returns:
        str: URL for ESPN
    """
    return f"https://www.espn.com/nba/scoreboard/_/date/{date.strftime('%Y%m%d')}"


def clean_espn(date: datetime, scoreboards: List[WebElement]) -> NBASlate:
    """
    Helper function to clean ESPN data into an NBASlate object.

    Args:
        date (datetime): Date to scrape
        scoreboards (List[WebElement]): List of scoreboards to clean

    Returns:
        NBASlate: Cleaned slate object
    """
    results: List[NBATeamGameResult] = []
    incomplete_games: List[NBAGame] = []

    for i, scoreboard in enumerate(scoreboards):
        # print(i)
        time = scoreboard.find_element(By.CLASS_NAME, "ScoreboardScoreCell__Time").text
        game = scoreboard.find_element(
            By.CLASS_NAME, "ScoreboardScoreCell__Competitors"
        )
        teams = game.find_elements(By.TAG_NAME, "li")

        if "final" in time.lower():
            for team in teams:
                team_name = team.find_element(
                    By.CLASS_NAME, "ScoreCell__TeamName"
                ).text.strip()
                result = (
                    0
                    if "ScoreboardScoreCell__Item--loser" in team.get_attribute("class")
                    else 1
                )
                results.append(NBATeamGameResult(team_name, result))
            continue

        # Game in progress (ignore)
        if "1st" or "2nd" or "3rd" or "4th" in time.lower():
            continue

        # Add retry logic for parsing game time
        attempts = 0
        while attempts < 3:
            try:
                game_time = datetime.strptime(time, "%I:%M %p").time()
                game_dt = datetime.combine(datetime.today(), game_time)
                break
            except ValueError:
                attempts += 1
                if attempts == 3:
                    raise ValueError(
                        f"Failed to parse game time after 3 attempts: {time}"
                    )
                continue

        if len(teams) != 2:
            continue

        away_team_name = (
            teams[0].find_element(By.CLASS_NAME, "ScoreCell__TeamName").text.strip()
        )
        home_team_name = (
            teams[1].find_element(By.CLASS_NAME, "ScoreCell__TeamName").text.strip()
        )
        incomplete_games.append(NBAGame(away_team_name, home_team_name, game_dt))

    return NBASlate(
        date,
        results,
        incomplete_games,
    )


def scrape_espn(date: datetime) -> NBASlate:
    """
    Scrape ESPN NBA scoreboard page into an NBASlate object using headless Chrome.
    Should be run after games have completed for the day.

    Args:
        date (datetime): Date to scrape outcomes for, defaults to today
    """
    espn_url = build_espn_url(date)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    attempts = 0
    while attempts < 3:
        try:
            driver.get(espn_url)
            # Wait for scoreboards to load
            scoreboards = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, "ScoreboardScoreCell")
                )
            )

            attempts += 1
            if attempts == 3:
                raise Exception("Failed to find scoreboards after 3 attempts.")

            return clean_espn(date, scoreboards)
        finally:
            driver.quit()


def save_slate_outcomes(slate: NBASlate, path: str = OUTCOMES_PATH) -> None:
    """
    Updates outcomes file to include daily slate data.

    Args:
        slate (NBASlate): Slate to save outcomes from
        path (str): Path to outcomes file, defaults to OUTCOMES_PATH
    """
    with open(path, "r") as f:
        outcomes: dict = json.load(f)

    outcomes.update(slate._format_outcomes())

    with open(path, "w") as f:
        json.dump(outcomes, f, indent=4)


def verify_outcomes(date: datetime, path: str = OUTCOMES_PATH) -> bool:
    """
    Utility function used to verify stored outcomes of a previous date.

    Args:
        date (datetime): Date to verify outcomes for
        path (str): Path to outcomes file, defaults to OUTCOMES_PATH

    Returns:
        bool: True if outcomes match, False otherwise
    """
    slate_of_date: NBASlate = scrape_espn(date)
    date_key: str = date.strftime("%Y-%m-%d")

    with open(path, "r") as f:
        all_outcomes: dict = json.load(f)

    if not all_outcomes[date_key] == slate_of_date._format_outcomes()[date_key]:
        print(all_outcomes[date_key])
        print(slate_of_date._format_outcomes()[date_key])
        return False
    return True


def main(date: datetime = datetime.today() - timedelta(days=1)) -> NBASlate:
    """
    Main function to scrape ESPN outcomes and save them to the outcomes file.

    Args:
        date (datetime): Date to scrape outcomes for, defaults to yesterday
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task(
            f"Scraping ESPN outcomes for {date.strftime('%Y-%m-%d')}"
        )
        results = scrape_espn(date)

        progress.update(task, description=f"Saving {len(results.results)} outcomes")
        save_slate_outcomes(results)

    return results


def scrape_missing_dates(path: str = OUTCOMES_PATH) -> None:
    """
    Scrapes all dates that don't have an entry in the outcomes file, working backwards from yesterday
    until finding the first existing entry.

    Args:
        path (str): Path to outcomes file, defaults to OUTCOMES_PATH
    """
    with open(path, "r") as f:
        outcomes = json.load(f)

    current = datetime.today() - timedelta(days=1)  # Start from yesterday

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("Checking for missing dates")

        while True:
            date_key = current.strftime("%Y-%m-%d")
            if date_key in outcomes:
                break

            progress.update(task, description=f"Scraping outcomes for {date_key}")
            try:
                slate = scrape_espn(current)
                if slate.results:  # Only save if there were games
                    progress.update(
                        task,
                        description=f"Saving {len(slate.results)} outcomes for {date_key}",
                    )
                    save_slate_outcomes(slate)
            except Exception as e:
                print(f"Failed to scrape {date_key}: {str(e)}")

            current -= timedelta(days=1)


if __name__ == "__main__":
    main()
