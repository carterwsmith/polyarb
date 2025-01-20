import pandas as pd
from typing import Optional

from src.analysis import odds_to_price

def visualize_by_day(u: Optional[float] = 1.0):
    """
    Analyze profit/loss and risk by day from wagers CSV.

    Args:
        u (float): Multiplier for P/L and risk amounts
    """
    # Load wagers
    df = pd.read_csv("tmp/wagers_b220417.csv")

    # Convert timestamp to datetime
    df["Date"] = pd.to_datetime(df["Timestamp"], unit="s").dt.date

    # Calculate risk for each bet
    df["price"] = df["Polymarket Odds"].apply(odds_to_price)
    df["Risk"] = df["Kelly Size"] * df["price"] * u

    # Group by date
    daily = df.groupby("Date").agg({"Risk": "sum", "Team": "count"}).round(2)

    daily.columns = ["Total Risk", "Number of Bets"]

    print(daily)

    print(f"\nTotal Risk: ${daily['Total Risk'].sum():,.2f}")
    print(f"Total Number of Bets: {daily['Number of Bets'].sum()}")
