"""
Constants used in the project.
"""

from enum import StrEnum

from src.utils import get_git_revision_short_hash_or_latest


class PolymarketWagerStatus(StrEnum):
    PLACED = "Placed"
    TEAM_NOT_SELECTED = "Team not selected"
    WAGER_TOO_SMALL = "Wager too small"
    PRICE_CHANGED = "Price changed"
    DRY_RUN = "Dry run"
    INSUFFICIENT_BALANCE = "Insufficient balance"
    SIGNATURE_FAILED = "Signature failed"
    EXCEPTION = "Exception"


SUCCESS_STATUSES = [
    PolymarketWagerStatus.PLACED,
]

OUTCOMES_PATH = "tmp/outcomes.json"
WAGERS_PATH = f"tmp/wagers_{get_git_revision_short_hash_or_latest()}.csv"

POLYMARKET_URL = "https://polymarket.com/sports/nba/games"
ODDS_URL = "https://sportsbook.draftkings.com/leagues/basketball/nba"

NBA_TEAM_TO_POLYMARKET_ABBREVIATION = {
    "Cavaliers": "CLE",
    "Thunder": "OKC",
    "Celtics": "BOS",
    "Rockets": "HOU",
    "Knicks": "NYK",
    "Grizzlies": "MEM",
    "Nuggets": "DEN",
    "Mavericks": "DAL",
    "Magic": "ORL",
    "Lakers": "LAL",
    "Bucks": "MIL",
    "Timberwolves": "MIN",
    "Clippers": "LAC",
    "Heat": "MIA",
    "Pacers": "IND",
    "Warriors": "GSW",
    "Pistons": "DET",
    "Hawks": "ATL",
    "Spurs": "TOT",  # might change?
    "Kings": "SAC",
    "Suns": "PHX",
    "Bulls": "CHI",
    "76ers": "PHI",
    "Nets": "BKN",
    "Trail Blazers": "POR",
    "Jazz": "UTA",
    "Hornets": "CHA",
    "Raptors": "TOR",
    "Pelicans": "NOP",
    "Wizards": "WAS",
}
