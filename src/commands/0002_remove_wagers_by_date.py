from datetime import datetime
from typing import List, Optional

import pandas as pd


def remove_wagers_by_date(
    target_date: datetime,
    csv_path: str = "tmp/wagers_b220417.csv",
    teams: Optional[List[str]] = None,
) -> int:
    """
    Remove wagers from wagers.csv for a specific date.

    Args:
        target_date (datetime): Date to remove wagers from
        teams (Optional[List[str]]): List of teams to remove wagers for

    Returns:
        Number of wagers removed
    """
    # Read existing wagers
    df = pd.read_csv(csv_path)

    # Get start and end timestamps for the target date
    start_ts = int(
        datetime(target_date.year, target_date.month, target_date.day).timestamp()
    )
    end_ts = int(
        datetime(
            target_date.year, target_date.month, target_date.day, 23, 59, 59
        ).timestamp()
    )

    # Filter rows based on teams if provided
    if teams:
        removed_wagers = df[
            (df["Timestamp"].between(start_ts, end_ts)) & (df["Team"].isin(teams))
        ]
        df = df[
            ~((df["Timestamp"].between(start_ts, end_ts)) & (df["Team"].isin(teams)))
        ]
    else:
        removed_wagers = df[df["Timestamp"].between(start_ts, end_ts)]
        df = df[~df["Timestamp"].between(start_ts, end_ts)]

    # Save filtered dataframe to new CSV
    df.to_csv("tmp/wagers_modified.csv", index=False)

    return len(removed_wagers)
