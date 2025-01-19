import pandas as pd


def backfill_wager_placed_column(csv_path):
    df = pd.read_csv(csv_path)

    if "Wager Placed" not in df.columns:
        df["Wager Placed"] = False
        df.to_csv("tmp/wagers_modified.csv", index=False)
