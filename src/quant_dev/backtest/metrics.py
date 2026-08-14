# quant_dev/backtest/metrics.py
"""
Performance metrics calculation module.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


def calc_metrics(
    df: pd.DataFrame,
    initial_capital: float = 100000.0,
) -> Dict[str, Any]:
    """
    Calculate strategy performance metrics (uses position shift 1 to avoid look-ahead bias).

    Args:
        df: DataFrame containing position and Close columns
        initial_capital: Initial capital amount

    Returns:
        Performance metrics dict
    """
    df = df.copy()

    # 1. Calculate equity curve
    df['daily_return'] = df['Close'].pct_change().fillna(0)
    df['strategy_return'] = df['position'].shift(1).fillna(0) * df['daily_return']
    df['equity'] = initial_capital * (1 + df['strategy_return']).cumprod()

    # 2. Basic metrics
    total_ret = (df['equity'].iloc[-1] / initial_capital) - 1
    n = len(df)
    annual_ret = (1 + total_ret) ** (252 / n) - 1 if n > 0 else 0
    volatility = df['strategy_return'].std() * np.sqrt(252) if n > 1 else 0
    sharpe = annual_ret / volatility if volatility > 0 else 0

    # 3. Maximum drawdown
    max_dd = (df['equity'].cummax() - df['equity']).max() / df['equity'].max() if df['equity'].max() > 0 else 0

    # 4. Win rate (calculated from entry/exit)
    win_rate, total_trades = _calc_win_rate(df)

    return {
        "total_return": round(total_ret * 100, 2),
        "annual_return": round(annual_ret * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_dd * 100, 2),
        "win_rate": round(win_rate, 2),
        "total_trades": total_trades,
        "nav_final": round(df['equity'].iloc[-1], 2),
    }


def calc_metrics_from_strat(
    strat,
    initial_capital: float = 100000.0,
) -> Dict[str, Any]:
    """
    Calculate performance metrics from a Strategy object (convenience for API calls).

    Args:
        strat: Strategy object (already run)
        initial_capital: Initial capital amount

    Returns:
        Performance metrics dict
    """
    return calc_metrics(strat.df, initial_capital)


def _calc_win_rate(df: pd.DataFrame) -> tuple:
    """
    Calculate win rate from entry/exit (internal function).
    Assumes entry is negative (paying), exit is positive (receiving).
    """
    trades = df[df['entry'].notna() | df['exit'].notna()]
    total_trades = len(trades)

    if total_trades == 0:
        return 0.0, 0

    profits = []
    entry_val = None

    for idx in trades.index:
        row = trades.loc[idx]
        if not pd.isna(row['entry']):
            entry_val = row['entry']
        if not pd.isna(row['exit']) and entry_val is not None:
            # entry is negative, exit is positive
            profit = abs(row['exit']) - abs(entry_val)
            profits.append(profit)
            entry_val = None  # reset

    win_rate = (sum(1 for p in profits if p > 0) / len(profits) * 100) if profits else 0.0

    return round(win_rate, 2), total_trades