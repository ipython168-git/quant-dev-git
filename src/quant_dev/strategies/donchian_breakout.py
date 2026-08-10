# src/quant_dev/strategies/donchian_breakout.py
"""
突破新高策略
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
    建立 Donchian Channel 突破策略

    Args: 
        ticker: 股票代號
        period: Donchian 週期 (default: 20)
        direction: "buy" / "sell"
        entry_order_type: "market" / "limit" / "stop"
        exit_order_type: "market" / "limit" / "stop"
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
        #df=df,
    ) 
    strat = Strategy(option)
    df = strat.df

    # 1. 計算 Donchian Channel
    df['HIGH_DONCHIAN'] = df['High'].rolling(period).max()
    df['LOW_DONCHIAN'] = df['Low'].rolling(period).min()

    # 2. 產生信號（用 shift 避免未來數據）
    # 突破上軌：今日 High > 昨日上軌
    df['signal_b'] = df['High'] > df['HIGH_DONCHIAN'].shift(1)
    # 跌破下軌：今日 Low < 昨日下軌
    df['signal_s'] = df['Low'] < df['LOW_DONCHIAN'].shift(1)

    # 3. 設定目標價
    df['entry_price'] = df['HIGH_DONCHIAN'].shift(1)
    df['exit_price'] = df['LOW_DONCHIAN'].shift(1)

    strat.run()
    return strat
