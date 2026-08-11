# quant_dev/backtest/metrics.py
"""
績效指標計算模組
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


def calc_metrics(
    df: pd.DataFrame,
    initial_capital: float = 100000.0,
) -> Dict[str, Any]:
    """
    計算策略績效指標（用 position shift 1 避免未來數據）

    Args:
        df: 包含 position, Close 嘅 DataFrame
        initial_capital: 初始資金

    Returns:
        績效指標 dict
    """
    df = df.copy()

    # 1. 計 equity curve
    df['daily_return'] = df['Close'].pct_change().fillna(0)
    df['strategy_return'] = df['position'].shift(1).fillna(0) * df['daily_return']
    df['equity'] = initial_capital * (1 + df['strategy_return']).cumprod()

    # 2. 基本指標
    total_ret = (df['equity'].iloc[-1] / initial_capital) - 1
    n = len(df)
    annual_ret = (1 + total_ret) ** (252 / n) - 1 if n > 0 else 0
    volatility = df['strategy_return'].std() * np.sqrt(252) if n > 1 else 0
    sharpe = annual_ret / volatility if volatility > 0 else 0

    # 3. 最大回撤
    max_dd = (df['equity'].cummax() - df['equity']).max() / df['equity'].max() if df['equity'].max() > 0 else 0

    # 4. 勝率（用 entry/exit 計）
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
    從 Strategy 物件計算績效指標（方便 API call）

    Args:
        strat: Strategy 物件（已 run）
        initial_capital: 初始資金

    Returns:
        績效指標 dict
    """
    return calc_metrics(strat.df, initial_capital)


def _calc_win_rate(df: pd.DataFrame) -> tuple:
    """
    從 entry/exit 計算勝率（內部 function）
    假設 entry 係負數（俾錢），exit 係正數（收錢）
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
            # entry 負數，exit 正數
            profit = abs(row['exit']) - abs(entry_val)
            profits.append(profit)
            entry_val = None  # reset

    win_rate = (sum(1 for p in profits if p > 0) / len(profits) * 100) if profits else 0.0

    return round(win_rate, 2), total_trades