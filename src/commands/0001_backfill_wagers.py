"""
Used to backfill Polymarket Price column into previously recorded wagers.
"""

import pandas as pd


def odds_to_price(american_odds: int) -> float:
    """
    Convert American odds to probability.

    Args:
        american_odds (int): American odds (positive or negative)

    Returns:
        float: Probability between 0 and 1
    """
    if american_odds > 0:
        # Underdog: positive odds
        probability = 100 / (american_odds + 100)
    else:
        # Favorite: negative odds
        american_odds = abs(american_odds)
        probability = american_odds / (american_odds + 100)

    return probability


def update_wagers_csv():
    # Read existing CSV
    df = pd.read_csv("wagers.csv")

    # Add new Polymarket Price column
    df["Polymarket Price"] = df["Polymarket Odds"].apply(odds_to_price)

    # Reorder columns to match new structure
    new_columns = [
        "Team",
        "Wager",
        "Kelly Size",
        "Diff",
        "Book Odds",
        "Polymarket Odds",
        "Polymarket Price",
        "Timestamp",
    ]
    df = df[new_columns]

    # Save back to CSV
    df.to_csv("wagers2.csv", index=False)


if __name__ == "__main__":
    update_wagers_csv()
