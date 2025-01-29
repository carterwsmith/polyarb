import json
import os
import subprocess


def get_git_revision_short_hash_or_latest(dir: str = "tmp") -> str:
    path = f"{dir}/wagers_{get_git_revision_short_hash()}.csv"
    if os.path.exists(path):
        return get_git_revision_short_hash()
    else:
        files = [
            f for f in os.listdir(dir) if f.startswith("wagers_") and f.endswith(".csv")
        ]
        if not files:
            return "latest"
        return sorted(files)[-1].replace("wagers_", "").replace(".csv", "")


def get_git_revision_short_hash() -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        .decode("ascii")
        .strip()
    )


def prettify(json_data: str) -> str:
    """
    Prettify JSON data for output.

    Args:
        json_data (str): JSON data

    Returns:
        str: Prettified JSON data
    """
    return json.dumps(json_data, indent=4)


def probability_to_american_odds(probability) -> int:
    """
    Convert a probability to American odds.

    Args:
        probability (float): Probability between 0 and 1

    Returns:
        int: American odds (positive or negative)

    Raises:
        ValueError: If probability is not between 0 and 1
    """
    if not 0 < probability < 1:
        raise ValueError(f"Probability {probability} must be between 0 and 1")

    if probability >= 0.5:
        # Favorite: negative odds
        american_odds = -100 * (probability / (1 - probability))
        # Round to nearest whole number
        return int(round(american_odds))
    else:
        # Underdog: positive odds
        american_odds = 100 * ((1 - probability) / probability)
        # Round to nearest whole number
        return int(round(american_odds))


def american_odds_to_probability(odds: int) -> float:
    """
    Convert American odds to probability.

    Args:
        odds (int): American odds (positive or negative)

    Returns:
        float: Probability between 0 and 1
    """
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def kelly_criterion(p: float, b: float) -> float:
    """
    Calculate Kelly Criterion bet size.

    Args:
        p: Probability of winning (from sportsbook odds)
        b: Proportion of bet gained (e.g. 2-to-1 = 2)

    Returns:
        float: Fraction of bankroll to bet (0 to 1)
    """
    return max(0, p - ((1 - p) / b))


def should_wager(book_odds: int, polymarket_odds: int) -> bool:
    """
    Determine if a wager should be made.
    If the book odds are NEGATIVE, and Polymarket odds are higher, return True.
    If the book odds are POSITIVE, and Polymarket odds are lower, return True.
    Otherwise, return False.

    Args:
        book_odds (int): Book odds
        polymarket_odds (int): Polymarket odds

    Returns:
        bool: True if a wager should be made
    """

    if book_odds < 0 and polymarket_odds > book_odds:
        return True
    elif book_odds > 0 and polymarket_odds > book_odds:
        return True
    else:
        return False
