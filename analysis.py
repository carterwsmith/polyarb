import json
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd

team_ignore_list = ()

def load_outcomes() -> dict:
    """
    Load outcomes from JSON file.
    """
    with open('outcomes.json', 'r') as f:
        return json.load(f)

def row_to_outcome(row: pd.Series) -> int:
    """
    Return the outcome of a row based on the outcomes file.

    Args:
        row (pd.Series): Row of the DataFrame

    Returns:
        int: 1 if team won, 0 if lost
    """
    outcomes = load_outcomes()
    date = datetime.fromtimestamp(row['Timestamp']).strftime('%Y-%m-%d')
    return outcomes[date][row['Team']]

def load() -> pd.DataFrame:
    """
    Load the wagers CSV file into a DataFrame.
    """
    data = pd.read_csv('wagers.csv')
    return data

def formatted_df() -> pd.DataFrame:
    """
    Return a formatted DataFrame with additional columns for analysis.
    """
    df = load()
    df = df[~df['Team'].isin(team_ignore_list)]
    df['price'] = df['Polymarket Odds'].apply(odds_to_price)
    df['outcome'] = df.apply(row_to_outcome, axis=1)
    return df

def kelly_sim(df: pd.DataFrame) -> None:
    """
    Simulate different maximums for bet sizing and graph the results.
    """
    df = df.sort_values('Timestamp')
    caps = [1, 2, 5, 10, 20, 30, float('inf')]  # inf for uncapped
    
    plt.figure(figsize=(12,8))
    
    for cap in caps:
        running_pl = 0
        pl_values = []
        
        for _, row in df.iterrows():
            # Cap the Kelly Size
            kelly_size = min(row['Kelly Size'], cap) if cap != float('inf') else row['Kelly Size']
            
            if row['outcome'] == 1:
                running_pl += kelly_size
            running_pl -= kelly_size * row['price']
            pl_values.append(running_pl)
        
        label = f'Kelly Cap {cap}' if cap != float('inf') else 'Kelly Uncapped'
        plt.plot(range(len(pl_values)), pl_values, label=label)

    plt.title('Running P/L with Different Kelly Caps')
    plt.xlabel('Number of Bets')
    plt.ylabel('Profit/Loss')
    plt.legend()
    plt.grid(True)
    plt.show()

def calculate_sharpe_ratio(df: pd.DataFrame) -> dict:
    """
    Calculate Sharpe ratio for each strategy.
    Uses current risk-free rate of 4.6%. (1/5/25)

    Returns:
        dict: Sharpe ratios by strategy
    """
    RISK_FREE_RATE = 0.046
    
    # Calculate returns for each bet
    kelly_returns = []
    equal_weight_returns = []
    
    for _, row in df.iterrows():
        # Kelly returns
        kelly_return = row['Kelly Size'] * (row['outcome'] - row['price'])
        kelly_returns.append(kelly_return)
        
        # Equal weight returns (1 unit bet)
        equal_return = row['outcome'] - row['price']
        equal_weight_returns.append(equal_return)
    
    kelly_returns = pd.Series(kelly_returns)
    equal_returns = pd.Series(equal_weight_returns)
    
    # Calculate Sharpe ratios with risk-free rate
    kelly_sharpe = (kelly_returns.mean() - RISK_FREE_RATE) / kelly_returns.std()
    equal_sharpe = (equal_returns.mean() - RISK_FREE_RATE) / equal_returns.std()
    
    return {
        'kelly': kelly_sharpe,
        'equal': equal_sharpe
    }

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

def graph(df: pd.DataFrame) -> None:
    """
    Graph results according to different strategies.
    Current strategies: Kelly criterion, equal weight

    Args:
        df (pd.DataFrame): Formatted DataFrame of wagers
    """
    df = df.sort_values('Timestamp')
    
    # Calculate running profit/loss
    kelly_pl = []
    running_pl = 0
    dates = []
    for _, row in df.iterrows():
        if row['outcome'] == 1:
            running_pl += row['Kelly Size']
        running_pl -= row['Kelly Size'] * row['price']
        kelly_pl.append(running_pl)
        dates.append(datetime.fromtimestamp(row['Timestamp']).strftime('%Y-%m-%d'))
    
    # Calculate running total of equal weight profit/loss
    equal_weight_pl = []
    running_equal_weight_pl = 0
    for _, row in df.iterrows():
        running_equal_weight_pl += row['outcome'] - row['price']
        equal_weight_pl.append(running_equal_weight_pl)

    plt.figure(figsize=(10,6))
    plt.plot(range(len(kelly_pl)), kelly_pl, label='Kelly Criterion Profit/Loss')
    plt.plot(range(len(equal_weight_pl)), equal_weight_pl, label='Equal Weight Profit/Loss', color='orange')  # Different color for equal weight

    # Add vertical lines for each new day
    current_date = None
    for i, date in enumerate(dates):
        if date != current_date:
            plt.axvline(x=i, color='gray', linestyle='--', alpha=0.6)
            current_date = date

    plt.title(f'Running Profit/Loss Using Kelly Criterion and Equal Weight')
    plt.xlabel('Number of Bets')
    plt.ylabel('Profit/Loss')
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    df = formatted_df()

    # Prediction count
    correct_predictions = df['outcome'].sum()
    total_predictions = len(df)
    accuracy = correct_predictions / total_predictions

    # Calculate profit (equal weight)
    equal_weight_profit = df['outcome'].sum() - df['price'].sum()
    equal_weight_risked = total_predictions

    # Calculate profit (Kelly criterion)
    kelly_earnings = df[df['outcome'] == 1]['Kelly Size'].sum()
    kelly_price = (df['Kelly Size'] * df['price']).sum()
    kelly_weight_profit = kelly_earnings - kelly_price
    kelly_risked = df['Kelly Size'].sum()

    # Calculate Sharpe by strategy
    sharpe_ratios = calculate_sharpe_ratio(df)

    print(f"n={total_predictions}")
    print(f"Accuracy: {accuracy:.2f}")
    print(f"Equal weight profit: {equal_weight_profit:.2f}, risked {equal_weight_risked:.2f}, ROI {equal_weight_profit/equal_weight_risked:.2f}, Sharpe {sharpe_ratios['equal']:.2f}")
    print(f"Kelly weight profit: {kelly_weight_profit:.2f}, risked {kelly_risked:.2f}, ROI {kelly_weight_profit/kelly_risked:.2f}, Sharpe {sharpe_ratios['kelly']:.2f}")

    graph(df)
