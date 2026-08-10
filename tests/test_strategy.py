# tests/test_strategy.py
"""
單元測試：Strategy 回測引擎 (CV 版)
專為 quant-dev 精簡版 Strategy 設計
"""
import pytest
import pandas as pd
import numpy as np
from src.quant_dev.backtest.strategy import Strategy, StrategyOption


# ============================================================
# 測試輔助函數
# ============================================================

def _make_test_data(
    opens: list, highs: list, lows: list, closes: list,
    signals_b: list = None, signals_s: list = None,
    entry_prices: list = None, exit_prices: list = None
) -> pd.DataFrame:
    """建立測試用 OHLC DataFrame + 必要 columns"""
    n = len(opens)
    df = pd.DataFrame({
        "Open": opens,
        "High": highs,
        "Low": lows,
        "Close": closes,
        "Volume": [1000] * n,
    })
    
    # 如果冇提供 signal，預設全部 False
    if signals_b is None:
        signals_b = [False] * n
    if signals_s is None:
        signals_s = [False] * n
    if entry_prices is None:
        entry_prices = [np.nan] * n
    if exit_prices is None:
        exit_prices = [np.nan] * n
    
    df["signal_b"] = signals_b
    df["signal_s"] = signals_s
    df["entry_price"] = entry_prices
    df["exit_price"] = exit_prices
    
    return df


def _create_strategy(df, **kwargs) -> Strategy:
    """建立 Strategy 實例"""
    option = StrategyOption(
        ticker="TEST",
        direction=kwargs.get("direction", "buy"),
        entry_order_type=kwargs.get("entry_order_type", "stop"),
        exit_order_type=kwargs.get("exit_order_type", "stop"),
        gap_entry=kwargs.get("gap_entry", "open"),
        gap_exit=kwargs.get("gap_exit", "open"),
        market_tz="America/New_York",
        timeframe="1d",
        df=df,
    )
    # 使用用戶傳入嘅 df（已包含 signal_b, signal_s, entry_price, exit_price）
    return Strategy(option)


# ============================================================
# 測試 Cases
# ============================================================

class TestStrategy:
    """Strategy 核心功能測試"""

    def test_buy_stop_normal(self):
        """Buy stop: 升穿 target 入市"""
        df = _make_test_data(
            opens=[100, 101, 102],
            highs=[102, 106, 107],
            lows=[99, 100, 101],
            closes=[97, 105, 106],
            signals_b=[False, True, False],
            entry_prices=[np.nan, 104, np.nan],
            exit_prices=[np.nan, np.nan, np.nan],
        )
        strat = _create_strategy(df, direction="buy", entry_order_type="stop", gap_entry="open")
        strat.run()
        
        # Bar 1: high=106 >= 104 → stop buy at -104
        assert strat.df["entry"].iloc[1] == -104.0
        assert strat.df["position"].iloc[1] == 1
        # 最後一日強制平倉
        assert strat.df["position"].iloc[-1] == 0

    def test_buy_limit_fill_at_open(self):
        """Buy limit: 開市已到 target → 用開市價成交"""
        df = _make_test_data(
            opens=[102, 98, 101],
            highs=[103, 102, 102],
            lows=[101, 97, 100],
            closes=[101, 101, 102],
            signals_b=[False, True, False],
            entry_prices=[np.nan, 100, np.nan],
            exit_prices=[np.nan, np.nan, np.nan],
        )
        strat = _create_strategy(df, direction="buy", entry_order_type="limit", gap_entry="open")
        strat.run()
        
        # Bar 1: open=98 <= 100 → limit buy at -98
        assert strat.df["entry"].iloc[1] == -98.0
        assert strat.df["position"].iloc[1] == 1

    def test_sell_stop_normal(self):
        """Sell stop: 跌穿 target 入市（沽空）"""
        df = _make_test_data(
            opens=[105, 104, 103],
            highs=[106, 105, 104],
            lows=[104, 99, 102],
            closes=[106, 100, 103],
            signals_b=[False, False, False],
            signals_s=[False, True, False],
            entry_prices=[np.nan, 101, np.nan],
            exit_prices=[np.nan, np.nan, np.nan],
        )
        strat = _create_strategy(df, direction="sell", entry_order_type="stop", gap_entry="open")
        strat.run()
        
        # Bar 1: low=99 <= 101 → stop sell at +101
        assert strat.df["entry"].iloc[1] == 101.0
        assert strat.df["position"].iloc[1] == -1

    def test_exit_signal_after_entry(self):
        """入市後，sell signal 觸發出市"""
        df = _make_test_data(
            opens=[100, 101, 102, 103],
            highs=[102, 106, 107, 108],
            lows=[99, 100, 101, 102],
            closes=[101, 104, 105, 107],
            signals_b=[False, True, False, False],
            signals_s=[False, False, True, False],
            entry_prices=[np.nan, 102, np.nan, np.nan],
            exit_prices=[np.nan, np.nan, 106, np.nan],
        )
        strat = _create_strategy(df, direction="buy", entry_order_type="stop", exit_order_type="stop")
        strat.run()
        
        # Bar 1: 入市
        assert strat.df["entry"].iloc[1] == -102.0
        assert strat.df["position"].iloc[1] == 1
        # Bar 2: 出市
        assert strat.df["exit"].iloc[2] == 102.0  # open=102 <= 106 → gap open
        assert strat.df["position"].iloc[2] == 0

    def test_gap_give_up(self):
        """gap_entry='give_up': 開市已突破 target → 放棄交易"""
        df = _make_test_data(
            opens=[100, 106, 102],
            highs=[105, 107, 103],
            lows=[99, 104, 101],
            closes=[104, 106, 102],
            signals_b=[False, True, False],
            entry_prices=[np.nan, 105, np.nan],
            exit_prices=[np.nan, np.nan, np.nan],
        )
        strat = _create_strategy(df, direction="buy", entry_order_type="stop", gap_entry="give_up")
        strat.run()
        
        # Bar 1: open=106 >= 105，但 give_up → 唔成交
        assert pd.isna(strat.df["entry"].iloc[1])
        assert strat.df["position"].iloc[1] == 0

    def test_gap_wait_close(self):
        """gap_entry='wait_close': 開市突破 target，等到收市決定"""
        df = _make_test_data(
            opens=[100, 106, 102],
            highs=[103, 107, 103],
            lows=[99, 104, 101],
            closes=[102, 106, 102],
            signals_b=[False, True, False],
            entry_prices=[np.nan, 105, np.nan],
            exit_prices=[np.nan, np.nan, np.nan],
        )
        strat = _create_strategy(df, direction="buy", entry_order_type="stop", gap_entry="wait_close")
        strat.run()
        
        # Bar 1: open=106 >= 105，wait_close → low=104 <= 105 → 用 target -105
        assert strat.df["entry"].iloc[1] == -105.0

    def test_gap_wait_give_up(self):
        """gap_entry='wait_give_up': 等到收市，如果冇觸發就放棄"""
        df = _make_test_data(
            opens=[100, 108, 102],
            highs=[105, 109, 103],
            lows=[99, 107, 101],
            closes=[104, 108, 102],
            signals_b=[False, True, False],
            entry_prices=[np.nan, 106, np.nan],
            exit_prices=[np.nan, np.nan, np.nan],
        )
        strat = _create_strategy(df, direction="buy", entry_order_type="stop", gap_entry="wait_give_up")
        strat.run()
        
        # Bar 1: open=108 >= 106，但 low=107 > 106 → 冇觸發 → 放棄
        assert pd.isna(strat.df["entry"].iloc[1])

    def test_market_order(self):
        """Market order: 直接用開市價成交"""
        df = _make_test_data(
            opens=[100, 102, 104],
            highs=[102, 104, 106],
            lows=[98, 100, 102],
            closes=[99, 103, 105],
            signals_b=[False, True, False],
            entry_prices=[np.nan, 999, np.nan],
            exit_prices=[np.nan, np.nan, np.nan],
        )
        strat = _create_strategy(df, direction="buy", entry_order_type="market")
        strat.run()
        
        # Bar 1: market → 用開市價 -102
        assert strat.df["entry"].iloc[1] == -102.0

    def test_last_day_force_close_long(self):
        """最後一日仍持好倉 → 強制用 close 平倉"""
        df = _make_test_data(
            opens=[100, 101, 102],
            highs=[102, 105, 104],
            lows=[99, 100, 101],
            closes=[101, 102, 105],
            signals_b=[False, True, False],
            entry_prices=[np.nan, 100, np.nan],
            exit_prices=[np.nan, np.nan, np.nan],
        )
        strat = _create_strategy(df, direction="buy", entry_order_type="stop")
        strat.run()
        
        # 最後一日（bar 2）強制平倉
        assert strat.df["position"].iloc[-1] == 0
        assert strat.df["exit"].iloc[-1] == 105.0

    def test_last_day_force_close_short(self):
        """最後一日仍持淡倉 → 強制用 close 平倉（負數）"""
        df = _make_test_data(
            opens=[103, 100, 102],
            highs=[104, 103, 104],
            lows=[101, 98, 101],
            closes=[102, 102, 105],
            signals_b=[False, False, False],
            signals_s=[False, True, False],
            entry_prices=[np.nan, 102, np.nan],
            exit_prices=[np.nan, np.nan, np.nan],
        )
        strat = _create_strategy(df, direction="sell", entry_order_type="stop")
        strat.run()
        
        # 最後一日（bar 2）強制平倉
        assert strat.df["position"].iloc[-1] == 0
        assert strat.df["exit"].iloc[-1] == -105.0

    def test_no_signal_no_trade(self):
        """冇信號 → 冇交易"""
        df = _make_test_data(
            opens=[100, 101, 102],
            highs=[102, 103, 104],
            lows=[99, 100, 101],
            closes=[101, 102, 103],
            signals_b=[False, False, False],
            signals_s=[False, False, False],
            entry_prices=[np.nan, np.nan, np.nan],
            exit_prices=[np.nan, np.nan, np.nan],
        )
        strat = _create_strategy(df, direction="buy")
        strat.run()
        
        assert (strat.df["position"] == 0).all()
        assert strat.df["entry"].isna().all()
        assert strat.df["exit"].isna().all()

    def test_get_trade_log(self):
        """get_trade_log() 正確提取交易記錄"""
        df = _make_test_data(
            opens=[100, 101, 102, 103, 104],
            highs=[102, 106, 107, 108, 109],
            lows=[99, 100, 101, 102, 103],
            closes=[101, 105, 106, 107, 108],
            signals_b=[False, True, False, False, False],
            signals_s=[False, False, False, True, False],
            entry_prices=[np.nan, 102, np.nan, np.nan, np.nan],
            exit_prices=[np.nan, np.nan, np.nan, 107, np.nan],
        )
        strat = _create_strategy(df, direction="buy")
        strat.run()
        
        log = strat.get_trade_log(rolling=0)
        # 應該有 2 行（entry bar + exit bar）
        assert len(log) == 2
        
        log2 = strat.get_trade_log(rolling=1)
        # rolling=1 應該有 4 行（前後各 1 行）
        assert len(log2) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])