from io import StringIO
import pandas as pd
import re
from typing import Optional

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from src.browser import (
    BrowserContext,
)


class DraftKingsElement:
    """Represents a single game's odds from DraftKings."""
    def __init__(self, team: str, odds_element: WebElement, time: str):
        self.team = self._clean_team_name(team)
        self.odds_element = odds_element
        self.time = time

    def moneyline(self) -> Optional[int]:
        """Get current moneyline odds from the WebElement."""
        try:
            odds = self.odds_element.text
            return self._parse_moneyline(odds)
        except Exception:
            return None

    def _clean_team_name(self, team: str) -> str:
        """Clean team name by removing time, quarter info, and trailing numbers."""
        team = team.replace("−", "-")  # Standardize minus sign
        # Fix: Use re.sub instead of str.replace with regex
        team = re.sub(r"^\d+:\d+[AP]M\s*", "", team)  # remove time
        team = re.sub(r"^.*Quarter\s*", "", team)  # remove "Quarter" and text before
        team = re.sub(r"^.*OT\s*", "", team)  # remove "OT" and text before
        team = re.sub(r"\s*\d+$", "", team)  # remove trailing numbers
        team = re.sub(r"\bRegulation[^\s]*\b", "", team)  # remove Regulation text
        
        # Extract abbreviation and team name
        match = re.match(r"\s*(\w+)\s+(.*)", team.strip())
        if match:
            _, team_name = match.groups()
            return team_name
        return team.strip()
    
    def _parse_moneyline(self, odds: str) -> Optional[int]:
            """Convert moneyline string to integer, handling invalid values."""
            try:
                return int(odds.replace("−", "-"))
            except (ValueError, AttributeError):
                return None

class DraftKingsBrowserContext(BrowserContext):
    """
    Holds the browser context for the DraftKings NBA odds page.
    """

    def __init__(
        self,
        browser: webdriver.Chrome,
        game_elements: list[DraftKingsElement],
    ):
        super().__init__(browser)
        self.game_elements = game_elements

    def refresh(self) -> None:
        """Override refresh to update game elements."""
        super().refresh()
        new_context = extract_draftkings_context(self.browser)
        self.game_elements = new_context.game_elements

def extract_draftkings_context(browser: webdriver.Chrome) -> DraftKingsBrowserContext:
    """Extract game elements from DraftKings page and create browser context."""
    game_elements = []
    
    try:
        table = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "sportsbook-table"))
        )

        html = table.get_attribute("outerHTML")
        df = pd.read_html(StringIO(html))[0]
        rows = table.find_elements(By.TAG_NAME, "tr")

        for idx, row_data in df.iterrows():
            team = row_data.iloc[0]
            moneyline = row_data.get("Moneyline", None)
            time_match = re.search(r"(\d+:\d+[AP]M)", str(team)) if pd.notna(team) else None
            time = time_match.group(1) if time_match else "LIVE"
            
            if moneyline is not None and idx + 1 < len(rows):  # Add index check
                # Get the correct odds element for this row
                row_element = rows[idx + 1]  # +1 to skip header
                cells = row_element.find_elements(By.TAG_NAME, "td")
                if cells:
                    odds_element = cells[-1]  # Get last cell (moneyline) for this specific row
                    element = DraftKingsElement(team, odds_element, time)
                    game_elements.append(element)

        return DraftKingsBrowserContext(browser, game_elements)
    except Exception as e:
        browser.quit()
        raise e
