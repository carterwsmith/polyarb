"""
Main entry point for making Polymarket wagers.
"""

import os
import time
from typing import List, Optional

import pandas as pd

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.games import get_live_teams
from src.constants import (
    WAGERS_PATH,
    PolymarketWagerStatus,
)
from src.draftkings import (
    DraftKingsElement,
    init_draftkings_session,
)
from src.polymarket import (
    get_polymarket,
    find_team_polymarket_price,
    init_polymarket_session,
    place_wagers,
    PolymarketOdds,
)
from src.utils import (
    american_odds_to_probability,
    kelly_criterion,
    probability_to_american_odds,
    should_wager,
)


def process_odds_data(
    book_odds: List[DraftKingsElement],
    polymarket_odds: List[PolymarketOdds],
    teams_list: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Process book odds and polymarket data into a unified DataFrame of opportunities.

    Args:
        book_odds (pd.DataFrame): DataFrame of scraped book odds
        polymarket_odds (List[PolymarketOdds]): List of scraped PolymarketOdds objects
        teams_list (Optional[List[str]]): List of teams to include

    Returns:
        pd.DataFrame: DataFrame of opportunities
    """
    rows = []
    for i in book_odds:
        if teams_list and i.team not in teams_list:
            # print(f"Skipping {i.team}, not in teams")
            continue

        team: str = i.team

        try:
            book_odds_val: int = i.moneyline()
            assert book_odds_val
        except:
            # print(f"Skipping {i.team}, invalid odds", i.odds_element.text) # can cause stale exc
            continue
        price: float | None = find_team_polymarket_price(
            team=team,
            listings=polymarket_odds,
        )
        if price is None or price > 1 or price == 0:
            # print(f"Skipping {i.team}, invalid price")
            continue
        price_as_odds: int = probability_to_american_odds(price)

        diff = abs(book_odds_val - price_as_odds)
        book_probability = american_odds_to_probability(book_odds_val)
        win_proportion = (1 - price) / price
        kelly_size = (
            kelly_criterion(book_probability, win_proportion)
            if should_wager(book_odds_val, price_as_odds)
            else 0
        )
        rows.append(
            {
                "Team": team,
                "Diff": diff,
                "Book Odds": book_odds_val,
                "Polymarket Odds": price_as_odds,
                "Kelly Size": round(kelly_size * 100, 2),
                "Polymarket Price": price,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Team",
                "Wager",
                "Kelly Size",
                "Diff",
                "Book Odds",
                "Polymarket Odds",
                "Polymarket Price",
            ]
        )

    diffs = pd.DataFrame(rows)
    diffs["Wager"] = diffs.apply(
        lambda x: should_wager(x["Book Odds"], x["Polymarket Odds"]), axis=1
    )
    diffs = diffs[
        [
            "Team",
            "Wager",
            "Kelly Size",
            "Diff",
            "Book Odds",
            "Polymarket Odds",
            "Polymarket Price",
        ]
    ]
    diffs.sort_values(by="Kelly Size", ascending=False, inplace=True)

    return diffs


def main(teams_list: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Console-friendly single run of scraping and processing.

    Args:
        teams_list (Optional[List[str]]): List of teams to include

    Returns:
        pd.DataFrame: DataFrame of opportunities
    """
    console = Console()

    with init_polymarket_session(
        manual=False
    ) as context, init_draftkings_session() as dk_context:
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=console,
        ) as progress:
            poly_task = progress.add_task("Scraping Polymarket...", total=1)
            polymarket_odds = get_polymarket(context)
            progress.advance(poly_task)
            progress.update(poly_task, description="[green]✓ [white]Scraped Polymarket")

            book_task = progress.add_task("Scraping DraftKings...", total=1)
            book_odds = dk_context.game_elements
            progress.advance(book_task)
            progress.update(book_task, description="[green]✓ [white]Scraped DraftKings")

            return process_odds_data(book_odds, polymarket_odds, teams_list)


def live(
    unit_size: float = 0.25,
    refresh_interval: int = 60,
    csv_path: str = WAGERS_PATH,
    teams_list: Optional[List[str]] = None,
    dry_run: bool = True,
    timeout: int | None = None,
) -> None:
    """
    Continuously monitor Polymarket and sportsbook for arbitrage opportunities.

    Args:
        unit_size (float): Fraction of recommended size to wager
        refresh_interval (int): Seconds to wait between checks
        csv_path (str): Path to save wagers to
        teams_list (Optional[List[str]]): List of teams to monitor
        dry_run (bool): If True, do not place wagers
        timeout (int): Number of consecutive checks to wait before exiting
    """
    console = Console()

    if not os.path.exists(csv_path):
        pd.DataFrame(
            columns=[
                "Team",
                "Wager",
                "Kelly Size",
                "Diff",
                "Book Odds",
                "Polymarket Odds",
                "Polymarket Price",
                "Timestamp",
                "Wager Placed",
            ]
        ).to_csv(csv_path, index=False)

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        console=console,
    )

    status_task = progress.add_task("Initializing...", total=1)

    layout = Layout()
    layout.split(Layout(progress, name="status"), Layout(name="table"))
    layout["status"].size = 1

    i = 0
    no_games_count = 0
    refresh_count = 0
    latest_wagers_table = None
    needs_login = not dry_run

    with init_polymarket_session(
        needs_login
    ) as context, init_draftkings_session() as dk_context:
        with Live(layout, console=console, refresh_per_second=4) as live:
            while True:
                try:
                    i += 1

                    if teams_list:
                        live_teams = [
                            team for team in get_live_teams() if team in teams_list
                        ]
                    else:
                        live_teams = get_live_teams()

                    if not live_teams:
                        no_games_count += 1
                        if timeout and no_games_count >= timeout:
                            console.print(
                                f"[red]No live games found for {timeout} consecutive checks. Exiting..."
                            )
                            live.stop()
                            context.close()
                            return
                        for remaining in range(refresh_interval, 0, -1):
                            incr_str = (
                                f"[red]Waiting to retry (no games found) - {remaining}s - {no_games_count}/{timeout}"
                                if timeout
                                else f"[red]Waiting to retry (no games found) - {remaining}s"
                            )
                            progress.update(status_task, description=incr_str)
                            time.sleep(1)
                        continue

                    no_games_count = 0

                    if refresh_count >= 2:
                        progress.update(
                            status_task, description="Refreshing browser..."
                        )
                        context.refresh()
                        dk_context.refresh()
                        refresh_count = 0

                    progress.update(status_task, description="Scraping Polymarket...")
                    polymarket_odds = get_polymarket(context)

                    progress.update(status_task, description="Scraping DraftKings...")
                    book_odds = dk_context.game_elements

                    refresh_count += 1

                    diffs = process_odds_data(book_odds, polymarket_odds, live_teams)
                    opportunities = diffs[diffs["Wager"] == True].copy()
                    teams_evaluated = len(
                        [game for game in book_odds if game.team in live_teams]
                    )

                    if not opportunities.empty:
                        existing = pd.read_csv(csv_path)
                        opportunities["Timestamp"] = time.time()

                        # Get most recent wager for each team
                        latest_wagers = (
                            existing.sort_values("Timestamp")
                            .groupby("Team")
                            .last()
                            .reset_index()
                        )

                        # Filter out opportunities where the most recent wager has the same odds
                        new_opps = opportunities[
                            ~opportunities.apply(
                                lambda row: any(
                                    (latest_wagers["Team"] == row["Team"])
                                    & (latest_wagers["Book Odds"] == row["Book Odds"])
                                    & (
                                        latest_wagers["Polymarket Price"]
                                        == row["Polymarket Price"]
                                    )
                                ),
                                axis=1,
                            )
                        ]

                        if dry_run:
                            # TODO: swallow SettingWithCopyWarning
                            new_opps["Wager Placed"] = (
                                PolymarketWagerStatus.DRY_RUN.value
                            )
                        else:
                            progress.update(
                                status_task, description="Placing wagers..."
                            )
                            # Place wagers
                            did_place = place_wagers(
                                df=new_opps,
                                context=context,
                                unit=unit_size,
                                dry_run=dry_run,
                            )
                            new_opps["Wager Placed"] = [
                                status.value for status in did_place
                            ]

                        if not new_opps.empty:
                            new_opps.to_csv(
                                csv_path, mode="a", header=False, index=False
                            )

                            # Create rich table
                            table = Table(title="Latest Wagers")
                            table.add_column("Team")
                            table.add_column("Kelly Size")
                            table.add_column("Book Odds")
                            table.add_column("Polymarket Price")
                            table.add_column("Wager Placed")

                            for _, row in new_opps.iterrows():
                                table.add_row(
                                    str(row["Team"]),
                                    str(row["Kelly Size"]),
                                    str(row["Book Odds"]),
                                    str(row["Polymarket Price"]),
                                    str(row["Wager Placed"]),
                                )

                            latest_wagers_table = table
                            layout["table"].update(latest_wagers_table)
                        else:
                            empty_table = Table(title="Latest Wagers")
                            empty_table.add_column("Status")
                            empty_table.add_row("No new wagers found")
                            layout["table"].update(empty_table)

                    # Countdown timer
                    for remaining in range(refresh_interval, 0, -1):
                        progress.update(
                            status_task,
                            description=f"Found {len(new_opps) if 'new_opps' in locals() else 0} wagers / {teams_evaluated} evaluated ({i} iter) - {remaining}s",
                        )
                        time.sleep(1)
                except KeyboardInterrupt:
                    live.stop()
                    context.close()
                    return
                except Exception as e:
                    for remaining in range(refresh_interval, 0, -1):
                        progress.update(
                            status_task,
                            description=f"[red]Waiting to retry (error: {str(e)}) - {remaining}s",
                        )
                        time.sleep(1)


if __name__ == "__main__":
    pass
