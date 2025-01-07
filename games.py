from datetime import datetime
import json
from typing import Dict, List, Optional

from nba_api.live.nba.endpoints.scoreboard import ScoreBoard

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

from constants import OUTCOMES_PATH


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
    def __init__(self, date: datetime, results: List[NBATeamGameResult], incomplete_games: Optional[List[NBAGame]] = None):
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
                "date": self.date.strftime('%Y-%m-%d'),
                "results": [
                    {
                        "team": result.team_name,
                        "result": "win" if result.result == 1 else "loss"
                    } for result in self.results
                ],
                "incomplete_games": [
                    {
                        "away_team": game.away_team,
                        "home_team": game.home_team,
                        "time": game.time.strftime('%I:%M %p')
                    } for game in self.incomplete_games
                ]
            }
        )
    
def get_live_teams() -> List[str]:
    """
    Get list of teams playing right now.
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
    """
    results: List[NBATeamGameResult] = []
    incomplete_games: List[NBAGame] = []

    for i, scoreboard in enumerate(scoreboards):
        #print(i)
        time = scoreboard.find_element(By.CLASS_NAME, "ScoreboardScoreCell__Time").text
        game = scoreboard.find_element(By.CLASS_NAME, "ScoreboardScoreCell__Competitors")
        teams = game.find_elements(By.TAG_NAME, "li")

        if 'final' in time.lower():
            for team in teams:
                team_name = team.find_element(By.CLASS_NAME, "ScoreCell__TeamName").text.strip()
                result = 0 if "ScoreboardScoreCell__Item--loser" in team.get_attribute("class") else 1
                results.append(NBATeamGameResult(team_name, result))
            continue

        # Add retry logic for parsing game time
        attempts = 0
        while attempts < 3:
            try:
                game_time = datetime.strptime(time, '%I:%M %p').time()
                game_dt = datetime.combine(datetime.today(), game_time)
                break
            except ValueError:
                attempts += 1
                if attempts == 3:
                    raise ValueError(f"Failed to parse game time after 3 attempts: {time}")
                continue

        if len(teams) != 2:
            continue

        away_team_name = teams[0].find_element(By.CLASS_NAME, "ScoreCell__TeamName").text.strip()
        home_team_name = teams[1].find_element(By.CLASS_NAME, "ScoreCell__TeamName").text.strip()
        incomplete_games.append(NBAGame(away_team_name, home_team_name, game_dt))
            

    return NBASlate(
        date,
        results,
        incomplete_games,
    )

def scrape_espn(date: datetime = datetime.today()) -> NBASlate:
    """
    Scrape ESPN NBA scoreboard page into an NBASlate object using headless Chrome.
    """
    espn_url = build_espn_url(date)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(espn_url)
        # Wait for scoreboards to load
        scoreboards = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "ScoreboardScoreCell"))
        )
        return clean_espn(date, scoreboards)
    finally:
        driver.quit()

def save_slate_outcomes(slate: NBASlate, path: str = OUTCOMES_PATH) -> None:
    """
    Updates outcomes file to include daily slate data.
    """
    with open(path, 'r') as f:
        outcomes: dict = json.load(f)
    
    outcomes.update(slate._format_outcomes())
    
    with open(path, 'w') as f:
        json.dump(outcomes, f, indent=4)

def verify_outcomes(date: datetime, path: str = OUTCOMES_PATH) -> bool:
    """
    Utility function used to verify stored outcomes of a previous date.
    """
    slate_of_date: NBASlate = scrape_espn(date)
    date_key: str = date.strftime('%Y-%m-%d')

    with open(path, 'r') as f:
        all_outcomes: dict = json.load(f)
    
    if not all_outcomes[date_key] == slate_of_date._format_outcomes()[date_key]:
        print(all_outcomes[date_key])
        print(slate_of_date._format_outcomes()[date_key])
        return False
    return True

def main():
    results = scrape_espn()
    save_slate_outcomes(results)
    return results