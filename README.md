# polymarket-arb
Automatically bet discrepancies between Polymarket and sportsbook odds.

### Docs
`docs/index.html`

### Installation
`pip install -r requirements.txt`

`pip install -e .`

### Usage
For placing wagers when games are live: `python src/sandbox.py`

- You must activate a VPN extension on the Chrome debug browser before running the script
- The headless Chrome (for sportsbook odds) must run without the VPN, which it does automatically on Mac, not sure if this applies to other platforms

For scraping game outcomes: `python src/games.py`

- Run this the day after games are complete.

For analyzing results: `python src/analysis.py`