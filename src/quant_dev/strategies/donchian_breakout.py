# quant_dev/strategies/donchian_breakout.py
"""
Donchian Channel breakout strategy.
"""
import pandas as pd
import numpy as np
from typing import Optional

from ..backtest.strategy import Strategy, StrategyOption


def create_donchian_breakout_strategy( 
    ticker: str,
    period: int = 20,
    direction: str = "buy",
    entry_order_type: str = "stop",
    exit_order_type: str = "stop",
    gap_entry: str = "open",
    gap_exit: str = "open",
) -> Strategy:
    """
    Create a Donchian Channel breakout strategy.

    Args: 
        ticker: Stock symbol
        period: Donchian Channel period (default: 20)
        direction: "buy" / "sell"
        entry_order_type: "market" / "limit" / "stop"
        exit_order_type: "market" / "limit" / "stop"
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
        #df=df,
    ) 
    strat = Strategy(option)
    df = strat.df

    # 1. Calculate Donchian Channel
    df['HIGH_DONCHIAN'] = df['High'].rolling(period).max()
    df['LOW_DONCHIAN'] = df['Low'].rolling(period).min()

    # 2. Generate signals (using shift to avoid look-ahead bias)
    # Break above upper band: today's High > yesterday's upper band
    df['signal_b'] = df['High'] > df['HIGH_DONCHIAN'].shift(1)
    # Break below lower band: today's Low < yesterday's lower band
    df['signal_s'] = df['Low'] < df['LOW_DONCHIAN'].shift(1)

    # 3. Set target prices
    df['entry_price'] = df['HIGH_DONCHIAN'].shift(1)
    df['exit_price'] = df['LOW_DONCHIAN'].shift(1)

    strat.run()
    return strat
