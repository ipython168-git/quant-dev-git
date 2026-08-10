# src/quant_dev/strategies/golden_and_death_cross.py
"""
黃金交叉/死亡交叉策略
"""
import pandas as pd
import numpy as np
from typing import Optional

from ..backtest.strategy import Strategy, StrategyOption


def create_golden_and_death_cross_strategy( 
    ticker: str,
    sma_fast: int = 20,
    sma_slow: int = 50,
    direction: str = "buy",
    entry_order_type: str = "stop",
    exit_order_type: str = "stop",
    gap_entry: str = "open",
    gap_exit: str = "open",
) -> Strategy:
    """
    建立黃金交叉/死亡交叉策略

    信號邏輯（用 shift 避免未來數據）：
    - 黃金交叉 (buy): 今日 fast > slow，昨日 fast <= slow
    - 死亡交叉 (sell): 今日 fast < slow，昨日 fast >= slow

    Args: 
        ticker: 股票代號
        sma_fast: 短期均線週期 (default: 20)
        sma_slow: 長期均線週期 (default: 50)
        direction: "buy" / "sell" (default: "buy")
        entry_order_type: "market" / "limit" / "stop" (default: "stop")
        exit_order_type: "market" / "limit" / "stop" (default: "stop")
        gap_entry: "open" / "close" / "give_up" / "wait_close" / "wait_give_up"
        gap_exit: "open" / "close" / "give_up" / "wait_close" / "wait_give_up"

    Returns:
        已 run 嘅 Strategy 物件
    """
    # 建立 Strategy
    option = StrategyOption(
        ticker=ticker,
        direction=direction,
        entry_order_type=entry_order_type,
        exit_order_type=exit_order_type,
        gap_entry=gap_entry,
        gap_exit=gap_exit, 
    )
    strat = Strategy(option)
    df = strat.df

    # 1. 計算 SMA
    df[f'SMA_{sma_fast}'] = df['Close'].rolling(sma_fast).mean()
    df[f'SMA_{sma_slow}'] = df['Close'].rolling(sma_slow).mean()

    # 2. 產生信號（用 shift(1) 同 shift(2) 避免未來數據）
    # 黃金交叉：shift(1) = 今日，shift(2) = 昨日
    # 今日 fast > slow，昨日 fast <= slow
    df['signal_b'] = (
        (df[f'SMA_{sma_fast}'].shift(1) > df[f'SMA_{sma_slow}'].shift(1)) &
        (df[f'SMA_{sma_fast}'].shift(2) <= df[f'SMA_{sma_slow}'].shift(2))
    )
    # 死亡交叉：今日 fast < slow，昨日 fast >= slow
    df['signal_s'] = (
        (df[f'SMA_{sma_fast}'].shift(1) < df[f'SMA_{sma_slow}'].shift(1)) &
        (df[f'SMA_{sma_fast}'].shift(2) >= df[f'SMA_{sma_slow}'].shift(2))
    )

    # 3. 設定目標價（用前一日嘅 High/Low）
    df['entry_price'] = df['Low'].shift(1)
    df['exit_price'] = df['High'].shift(1)

    strat.run()
    return strat

