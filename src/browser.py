"""
Manages Selenium webdrivers and browser sessions.
"""

from datetime import datetime
import os
import subprocess
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from src.constants import (
    BROWSER_LOG_PATH,
)


class BrowserContext:
    """
    Holds data for a browser context.
    """

    def __init__(self, browser: webdriver.Chrome):
        self.browser = browser
        self.process = None

    def set_process(self, process: subprocess.Popen) -> None:
        """Store the Chrome process handle"""
        self.process = process

    def refresh(self) -> None:
        """Refresh the browser"""
        self.browser.refresh()

    def close(self) -> None:
        """Close both browser and process"""
        self.browser.quit()
        if self.process:
            self.process.kill()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.browser.close()


def get_browser(
    headless: bool = False, debug_port: int = 9222
) -> tuple[webdriver.Chrome, subprocess.Popen]:
    """
    Get a Chrome browser with remote debugging enabled.

    Args:
        headless (bool): Whether to run Chrome in headless mode
        debug_port (int): Port to use for remote debugging

    Returns:
        webdriver.Chrome: Chrome browser
    """
    os.makedirs(BROWSER_LOG_PATH, exist_ok=True)
    timestamp: int = int(datetime.now().timestamp())
    log_file = os.path.join(BROWSER_LOG_PATH, f"chrome_{timestamp}.log")

    # Start Chrome process
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    with open(log_file, "w") as f:
        process = subprocess.Popen(
            [
                chrome_path,
                f"--remote-debugging-port={debug_port}",
                "--no-first-run",  # Skip first run dialogs
                "--no-default-browser-check",
                "--headless" if headless else "",
            ],
            stdout=f,
            stderr=f,
        )

    # Wait for Chrome to start
    time.sleep(2)

    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    return webdriver.Chrome(options=chrome_options), process


def go_to_page(browser: webdriver.Chrome, url: str) -> None:
    """
    Navigate to a page.

    Args:
        browser (webdriver.Chrome): Browser to navigate
        url (str): URL to navigate to
    """
    browser.get(url)


def init_browser_context(
    extract: callable,
    start_url: str = None,
    headless: bool = False,
    manual: bool = True,
    debug_port: int = 9222,
) -> BrowserContext:
    """
    Return browser context extracted from a callable, which must accept a browser.

    Args:
        extract (callable): Function to extract browser context
        start_url (str): URL to start at
        headless (bool): Whether to run Chrome in headless mode
        manual (bool): Whether to pause for manual intervention
        debug_port (int): Port to use for remote debugging

    Returns:
        PolymarketBrowserContext: Browser context
    """
    browser, process = get_browser(headless, debug_port)

    if browser is None:
        print("Failed to get remote debugging browser.")
        exit(1)

    if start_url:
        if browser.current_url != start_url:
            # print("going to page", start_url, "from", browser.current_url)
            go_to_page(browser, start_url)

    if manual:
        i = input("Get the browser to a ready state then press (y) to continue ")
        if i != "y":
            i = input("Get the browser to a ready state then press (y) to continue ")

    context: BrowserContext = extract(browser)
    context.set_process(process)

    return context
