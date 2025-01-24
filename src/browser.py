import subprocess
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class BrowserContext:
    """
    Holds data for a browser context.
    """

    def __init__(self, browser: webdriver.Chrome):
        self.browser = browser

    def refresh(self) -> None:
        """
        Refresh the browser context.
        """
        self.browser.refresh()

    def close(self) -> None:
        """
        Close the browser.
        """
        self.browser.quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.browser.quit()


def get_browser(headless: bool = False, debug_port: int = 9222) -> webdriver.Chrome:
    """
    Get a Chrome browser with remote debugging enabled.

    Returns:
        webdriver.Chrome: Chrome browser
    """
    # Start Chrome process
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    subprocess.Popen(
        [
            chrome_path,
            f"--remote-debugging-port={debug_port}",
            "--no-first-run",  # Skip first run dialogs
            "--no-default-browser-check",
            "--headless" if headless else "",
        ]
    )

    # Wait for Chrome to start
    time.sleep(2)

    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    return webdriver.Chrome(options=chrome_options)


def go_to_page(browser: webdriver.Chrome, url: str) -> None:
    """
    Navigate to a page.
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

    Returns:
        PolymarketBrowserContext: Browser context
    """
    browser = get_browser(headless, debug_port)

    if browser is None:
        print("Failed to get remote debugging browser.")
        exit(1)

    if start_url:
        if browser.current_url != start_url:
            #print("going to page", start_url, "from", browser.current_url)
            go_to_page(browser, start_url)

    if manual:
        i = input("Get the browser to a ready state then press (y) to continue ")
        if i != "y":
            i = input("Get the browser to a ready state then press (y) to continue ")

    context = extract(browser)

    return context
