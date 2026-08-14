# quant_dev/strategies/golden_and_death_cross.py
"""
Golden Cross / Death Cross strategy.
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
    Create a Golden Cross / Death Cross strategy.

    Signal logic (using shift to avoid look-ahead bias):
    - Golden Cross (buy): today fast > slow, yesterday fast <= slow
    - Death Cross (sell): today fast < slow, yesterday fast >= slow

    Args: 
        ticker: Stock symbol
        sma_fast: Short-term SMA period (default: 20)
        sma_slow: Long-term SMA period (default: 50)
        direction: "buy" / "sell" (default: "buy")
        entry_order_type: "market" / "limit" / "stop" (default: "stop")
        exit_order_type: "market" / "limit" / "stop" (default: "stop")
        gap_entry: "open" / "close" / "give_up" / "wait_close" / "wait_give_up"
        gap_exit: "open" / "close" / "give_up" / "wait_close" / "wait_give_up"

    Returns:
        Strategy object (already run)
    """
    # Create Strategy
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

    # 1. Calculate SMA
    df[f'SMA_{sma_fast}'] = df['Close'].rolling(sma_fast).mean()
    df[f'SMA_{sma_slow}'] = df['Close'].rolling(sma_slow).mean()

    # 2. Generate signals (using shift(1) and shift(2) to avoid look-ahead bias)
    # Golden Cross: shift(1) = today, shift(2) = yesterday
    # today fast > slow, yesterday fast <= slow
    df['signal_b'] = (
        (df[f'SMA_{sma_fast}'].shift(1) > df[f'SMA_{sma_slow}'].shift(1)) &
        (df[f'SMA_{sma_fast}'].shift(2) <= df[f'SMA_{sma_slow}'].shift(2))
    )
    # Death Cross: today fast < slow, yesterday fast >= slow
    df['signal_s'] = (
        (df[f'SMA_{sma_fast}'].shift(1) < df[f'SMA_{sma_slow}'].shift(1)) &
        (df[f'SMA_{sma_fast}'].shift(2) >= df[f'SMA_{sma_slow}'].shift(2))
    )

    # 3. Set target prices (using previous day's High/Low)
    df['entry_price'] = df['Low'].shift(1)
    df['exit_price'] = df['High'].shift(1)

    strat.run()
    return strat

