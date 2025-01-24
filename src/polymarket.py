"""
Selenium resources for interacting with the Polymarket NBA page.
"""

from datetime import datetime
import math
import random
import time
from typing import List, Tuple

import pandas as pd

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.browser import (
    BrowserContext,
    init_browser_context,
)
from src.constants import (
    NBA_TEAM_TO_POLYMARKET_ABBREVIATION,
    PolymarketWagerStatus,
    POLYMARKET_URL,
)


class PolymarketBetPanelDOMElement:
    """
    Holds data for the bet panel on the Polymarket NBA page.
    """

    def __init__(
        self,
        root: WebElement,
        order_toggle: WebElement,
        amount_field: WebElement,
        price_field: WebElement,
        buy_button: WebElement,
    ):
        self.root = root
        self.order_toggle = order_toggle
        self.amount_field = amount_field
        self.price_field = price_field
        self.buy_button = buy_button


class PolymarketGameDOMElement:
    """
    Holds data for a single game on the Polymarket NBA page.
    """

    def __init__(
        self,
        away_team_abbr: str,
        home_team_abbr: str,
        away_team_button: WebElement,
        home_team_button: WebElement,
    ):
        self.away_team_abbr = away_team_abbr
        self.home_team_abbr = home_team_abbr
        self.away_team_button = away_team_button
        self.home_team_button = home_team_button

    def prices(self) -> Tuple[float, float]:
        """
        Extract the current prices for the game (in $) as floats.

        Returns:
            Tuple[float, float]: (away price, home price)
        """
        away_price_text = self.away_team_button.text
        home_price_text = self.home_team_button.text

        away_price = float(
            away_price_text[3:].replace("¢", "")
        )  # Extract number after abbreviation
        home_price = float(home_price_text[3:].replace("¢", ""))

        return away_price / 100, home_price / 100

    def button_from_full_team_name(self, full_team_name: str) -> WebElement:
        """
        Return the button element for the provided team.

        Args:
            full_team_name (str): Full team name

        Returns:
            WebElement: Button element for the team
        """
        polymarket_abbr = NBA_TEAM_TO_POLYMARKET_ABBREVIATION[full_team_name]
        if polymarket_abbr == self.away_team_abbr:
            return self.away_team_button
        elif polymarket_abbr == self.home_team_abbr:
            return self.home_team_button
        else:
            return None

    def __str__(self) -> str:
        prices = self.prices()
        return f"{self.away_team_abbr} ({prices[0]}¢) at {self.home_team_abbr} ({prices[1]}¢)"


class PolymarketBrowserContext(BrowserContext):
    """
    Holds the browser context for the Polymarket NBA page.
    """

    def __init__(
        self,
        browser: webdriver.Chrome,
        game_elements: List[PolymarketGameDOMElement],
        bet_panel: PolymarketBetPanelDOMElement,
    ):
        super().__init__(browser)
        self.game_elements = game_elements
        self.bet_panel = bet_panel

    def refresh(self) -> None:
        """Override refresh to click first game element."""
        super().refresh()
        new_context = extract_polymarket_context(self.browser)
        self.game_elements = new_context.game_elements
        self.bet_panel = new_context.bet_panel
        if self.game_elements:
            self.game_elements[0].away_team_button.click()


def get_date_section_text(datetime: datetime = datetime.today()) -> str:
    """
    Return text in the format "Thu, January 9", no 0 before the 9.

    Args:
        datetime (datetime, optional): Date to format. Defaults to datetime.today().

    Returns:
        str: Formatted date string
    """
    return datetime.strftime("%a, %B %-d")


def does_li_contain_date(li: WebElement) -> bool:
    """
    Check if the text of the li element contains a date.
    Used in determining today's markets.

    Args:
        li (WebElement): li element

    Returns:
        bool: True if the text contains a date
    """
    text = li.text.strip()
    try:
        date = datetime.strptime(text, "%a, %B %d")
        return True
    except ValueError:
        return False


def float_to_cents(f: float) -> int:
    """
    Convert a float to cents.

    Args:
        f (float): Float to convert

    Returns:
        int: Cents
    """
    return math.floor(int(f * 100))


def sign_wager(
    context: PolymarketBrowserContext,
) -> bool:
    desired_title = "MetaMask"

    # Find the signature window and switch to it
    for wh in context.browser.window_handles:
        context.browser.switch_to.window(wh)
        try:
            if context.browser.title == desired_title:
                break
        except Exception:
            # print('1')
            return False

    # Click button with aria-label "Scroll down"
    try:
        context.browser.execute_script(
            """
            const buttons = document.getElementsByTagName('button');
            for (let button of buttons) {
                if (button.getAttribute('aria-label') === 'Scroll down') {
                    button.click();
                    break;
                }
            }
        """
        )
        time.sleep(1)
    except Exception:
        # print('2')
        return False

    # Click the button with data-testid "confirm-footer-button"
    try:
        context.browser.execute_script(
            """
            const buttons = document.getElementsByTagName('button');
            for (let button of buttons) {
                if (button.getAttribute('data-testid') === 'confirm-footer-button') {
                    button.click();
                    break;
                }
            }
        """
        )
        time.sleep(5)
    except Exception:
        # print('3')
        return False

    desired_main_title = "Polymarket"
    # Find the main window and switch to it
    for wh in context.browser.window_handles:
        context.browser.switch_to.window(wh)
        try:
            if desired_main_title in context.browser.title:
                break
        except Exception:
            # print('4')
            return False

    # Wait until "bought" is in buy button text (timeout 5 seconds)
    attempts = 0
    try:
        while attempts < 5:
            time.sleep(1)
            if "bought" in context.bet_panel.buy_button.text.lower():
                return True
            attempts += 1
        return False
    except Exception:
        # print('5')
        return False


def place_wagers(
    df: pd.DataFrame,
    context: PolymarketBrowserContext,
    unit: float = 1.0,
    dry_run: bool = True,
) -> List[PolymarketWagerStatus]:
    """
    From a df with these columns:
        Team  Wager  Kelly Size  Diff  Book Odds  Polymarket Odds  Polymarket Price  Timestamp
    interact with the elements on the Polymarket page to place wagers.

    Args:
        df (pd.DataFrame): DataFrame of wagers
        context (PolymarketBrowserContext): Browser context
        unit (float, optional): Unit size for wagers. Defaults to 1.0
        dry_run (bool, optional): If True, don't actually place wagers. Defaults to True

    Returns:
        List[PolymarketWagerStatus]: List of strings indicating if each wager was successfully placed
    """
    results = []
    for _, row in df.iterrows():
        # If wager shouldn't be made, skip it
        if not row["Wager"]:
            continue

        # Find the button for the team and click it
        team_found = False
        for g in context.game_elements:
            if g.button_from_full_team_name(row["Team"]):
                g.button_from_full_team_name(row["Team"]).click()
                team_found = True
                break

        if not team_found:
            results.append(PolymarketWagerStatus.TEAM_NOT_SELECTED)
            continue

        # Calculate amount to wager and enter in field
        amount_dollars = unit * row["Kelly Size"] * row["Polymarket Price"]
        # per_wager_max_dollars = 5
        if amount_dollars < 1 or amount_dollars < row["Polymarket Price"]:
            results.append(PolymarketWagerStatus.WAGER_TOO_SMALL)
            continue
        # if amount_dollars > per_wager_max_dollars:
        #     amount_dollars = per_wager_max_dollars
        context.bet_panel.amount_field.send_keys(str(amount_dollars))

        # Assert the team and price is correct
        try:
            if not row["Team"] in context.bet_panel.root.text:
                results.append(PolymarketWagerStatus.TEAM_NOT_SELECTED)
                continue
            if not (
                str(float_to_cents(row["Polymarket Price"]))
                in context.bet_panel.price_field.text
            ):
                # TODO: recalculate a fair price and check if available
                results.append(PolymarketWagerStatus.PRICE_CHANGED)
                continue
            # Click the buy button
            if dry_run:
                results.append(PolymarketWagerStatus.DRY_RUN)
                continue
            context.bet_panel.buy_button.click()
            time.sleep(1)
            if "insufficient balance" in context.bet_panel.root.text.lower():
                results.append(PolymarketWagerStatus.INSUFFICIENT_BALANCE)
                continue

            if not sign_wager(context):
                results.append(PolymarketWagerStatus.SIGNATURE_FAILED)
                continue
            else:
                results.append(PolymarketWagerStatus.PLACED)
        except:
            # TODO: size down bet to match desired price, change field in saved wager
            results.append(PolymarketWagerStatus.EXCEPTION)

    return results


def init_polymarket_session() -> PolymarketBrowserContext:
    context: PolymarketBrowserContext = init_browser_context(
        extract=extract_polymarket_context,
        start_url=POLYMARKET_URL,
    )

    return context


def extract_polymarket_context(browser: webdriver.Chrome) -> PolymarketBrowserContext:
    """
    Extract the browser context from the Polymarket NBA page.

    Args:
        browser (webdriver.Chrome): Chrome browser with remote debugging enabled

    Returns:
        PolymarketBrowserContext: Browser context
    """
    today_text = get_date_section_text()

    # get div with today_text in text, don't use xpath
    lis = WebDriverWait(browser, 10).until(
        EC.presence_of_all_elements_located((By.TAG_NAME, "li"))
    )

    found_today_text = False
    game_lis: List[WebElement] = []
    for li in lis:
        if today_text in li.text:
            found_today_text = True
            continue

        if found_today_text and does_li_contain_date(li):
            break

        if found_today_text:
            game_lis.append(li)

    if not game_lis:
        print(f"Failed to find games for {today_text}")
        return
    else:
        print(f"Found {len(game_lis)} games for {today_text}")

    # Parse games
    game_elements: List[PolymarketGameDOMElement] = []
    for li in game_lis:
        wager_buttons = [
            b for b in li.find_elements(By.CSS_SELECTOR, "button") if "¢" in b.text
        ]
        obj = PolymarketGameDOMElement(
            away_team_abbr=wager_buttons[0].text[:3],
            home_team_abbr=wager_buttons[1].text[:3],
            away_team_button=wager_buttons[0],
            home_team_button=wager_buttons[1],
        )
        game_elements.append(obj)

    # Locate bet panel features
    try:  # try to find by id
        container = browser.find_element(By.ID, "event-layout-buy-sell-widget")
    except (
        NoSuchElementException
    ):  # get the last div in the div with id 'column-wrapper'
        column_wrapper = browser.find_element(By.ID, "column-wrapper")
        immediate_children = column_wrapper.find_elements(By.XPATH, "./div")
        container = immediate_children[-1]
    try:
        order_toggle = [
            b
            for b in container.find_elements(By.CSS_SELECTOR, "button")
            if "Market" in b.text or "Limit" in b.text
        ][0]
    except IndexError:
        # weird edge case where a game from yesterday shows up
        game_lis[0].click()
        game_lis[0].click()
        order_toggle = [
            b
            for b in container.find_elements(By.CSS_SELECTOR, "button")
            if "Market" in b.text or "Limit" in b.text
        ][0]
    assert order_toggle
    amount_field = container.find_element(By.CSS_SELECTOR, "input[placeholder='$0']")
    assert amount_field
    other_sections = ["Outcome", "Amount", "Shares", "Potential"]
    price_container = [
        c
        for c in container.find_elements(By.CSS_SELECTOR, "div")
        if "Avg price" in c.text
        and "¢" in c.text
        and not any([o in c.text for o in other_sections])
    ][0]
    price_field = price_container.find_element(By.CSS_SELECTOR, "span")
    assert price_field
    buy_button = [
        b
        for b in container.find_elements(By.CSS_SELECTOR, "button")
        if "Buy" in b.text or "log in" in b.text.lower()
    ][0]
    assert buy_button
    bet_panel = PolymarketBetPanelDOMElement(
        root=container,
        order_toggle=order_toggle,
        amount_field=amount_field,
        price_field=price_field,
        buy_button=buy_button,
    )

    return PolymarketBrowserContext(
        browser=browser,
        game_elements=game_elements,
        bet_panel=bet_panel,
    )
