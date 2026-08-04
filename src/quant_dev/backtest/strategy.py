# src/quant_dev/backtest/strategy.py
"""
精簡版回測引擎 (Strategy)
保留核心：Order Type, Gap Handling, 多模式 (Normal/EAC/Strong Hold)
移除：YAML 設定、複雜的條件生成器
only for swing trade
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class StrategyConfig:
    """策略配置（精簡版）"""
    ticker: str
    direction: str = "buy"                  # "buy" 或 "sell"
    mode: str = "normal"                    # "normal", "exit_at_close", "strong_hold"
    entry_order_type: str = "stop"        # "market", "limit", "stop"
    exit_order_type: str = "stop"
    gap_entry: str = "open"                 # "open", "close", "give_up", "wait_close"
    gap_exit: str = "open"
    initial_capital: float = 10000.0


class Strategy:
    """精簡版回測引擎"""

    def __init__(self, config: StrategyConfig, data: pd.DataFrame):
        self.config = config
        self.df = data.copy()
        self._validate_data()
        self._init_columns()

    # ============================================================
    # 用戶 API
    # ============================================================
    def add_signal(self, signal_series: pd.Series) -> None:
        """加入交易信號：1=買入, -1=賣出, 0=觀望"""
        if len(signal_series) != len(self.df):
            raise ValueError("Signal 長度必須與數據一致")
        self.df['signal'] = signal_series.values

    def set_entry_price(self, price_series: pd.Series) -> None:
        """設定入市價（例如：df['High'].shift(1)）"""
        if len(price_series) != len(self.df):
            raise ValueError("Entry price 長度必須與數據一致")
        self.df['entry_price'] = price_series.values

    def set_exit_price(self, price_series: pd.Series) -> None:
        """設定出市價（例如：df['Low'].shift(1)）"""
        if len(price_series) != len(self.df):
            raise ValueError("Exit price 長度必須與數據一致")
        self.df['exit_price'] = price_series.values

    def run(self) -> "Strategy":
        """執行回測"""
        self._prepare_arrays()
        self._simulate()
        self._sync_to_dataframe()
        return self

 
    # ============================================================
    # 內部方法 (保留你嘅核心邏輯)
    # ============================================================
    def _validate_data(self):
        if not {"Open", "High", "Low", "Close"}.issubset(self.df.columns):
            raise ValueError("DataFrame 必須包含 Open, High, Low, Close")

    def _init_columns(self):
        self.df["position"] = 0
        self.df["entry"] = np.nan
        self.df["exit"] = np.nan
        self.df["signal"] = 0
        if "entry_price" not in self.df.columns:
            self.df["entry_price"] = np.nan
        if "exit_price" not in self.df.columns:
            self.df["exit_price"] = np.nan

    def _prepare_arrays(self):
        """將 DataFrame 轉為 NumPy Array 以加快速度"""
        cols = ["Open", "High", "Low", "Close", "signal", "entry_price", "exit_price"]
        for col in cols:
            setattr(self, f"_np_{col}", self.df[col].to_numpy(dtype=float))
        self._np_position = np.zeros(len(self.df), dtype=int)
        self._np_entry = np.full(len(self.df), np.nan)
        self._np_exit = np.full(len(self.df), np.nan)

    # ============================================================
    # 核心模擬循環 (保留你原設計)
    # ============================================================
    def _simulate(self):
        """主模擬循環"""
        n = len(self.df)
        if self.config.mode == "strong_hold":
            self._simulate_strong_hold()
            return

        start_i = 0 if self.config.mode == "exit_at_close" else 1
        for i in range(start_i, n):
            self._process_bar(i)
        self._close_position_on_last_day()

    def _process_bar(self, i: int):
        """處理單一 K 線"""
        prev_pos = self._np_position[i-1] if i > 0 else 0
        signal = self._np_signal[i]

        if self.config.mode == "exit_at_close":
            self._process_eac_bar(i, prev_pos, signal)
            return

        # Normal mode
        if prev_pos == 0:
            self._try_entry(i, signal)
        elif prev_pos == 1:
            self._try_exit(i, signal, "buy")
        elif prev_pos == -1:
            self._try_exit(i, signal, "sell")

    # ============================================================
    # Entry / Exit 邏輯 (保留你原設計)
    # ============================================================
    def _try_entry(self, i: int, signal: int):
        """嘗試入場"""
        if signal == 0:
            return
        if self.config.direction == "buy" and signal != 1:
            return
        if self.config.direction == "sell" and signal != -1:
            return

        price = self._get_order_price(i, "entry", signal, self._np_entry_price[i])
        if price is not None:
            self._np_position[i] = signal
            self._np_entry[i] = price

    def _try_exit(self, i: int, signal: int, holding: str):
        """嘗試出場"""
        exit_signal = -1 if holding == "buy" else 1
        if signal != exit_signal:
            self._np_position[i] = 1 if holding == "buy" else -1
            return

        price = self._get_order_price(i, "exit", signal, self._np_exit_price[i])
        if price is not None:
            self._np_position[i] = 0
            self._np_exit[i] = abs(price)

    # ============================================================
    # Order Type + Gap Handling (你嘅獨家本領)
    # ============================================================
    def _get_order_price(self, i: int, action: str, signal: int, target: float) -> Optional[float]:
        """根據 Order Type 決定成交價（保留你原設計）"""
        order_type = self.config.entry_order_type if action == "entry" else self.config.exit_order_type
        o, h, l, c = self._np_Open[i], self._np_High[i], self._np_Low[i], self._np_Close[i]

        if order_type == "market":
            return o * signal

        if np.isnan(target):
            return None

        # Stop Order
        if order_type == "stop":
            if signal == 1:  # 買入停損：升穿 target
                if o >= target:
                    return self._handle_gap(i, action, signal, target)
                if h >= target:
                    return target * signal
            else:  # 賣出停損：跌穿 target
                if o <= target:
                    return self._handle_gap(i, action, signal, target)
                if l <= target:
                    return target * signal
            return None

        # Limit Order
        if order_type == "limit":
            if signal == 1:  # 限價買入：跌到 target
                if o <= target:
                    return o * signal
                if l <= target:
                    return target * signal
            else:  # 限價賣出：升到 target
                if o >= target:
                    return o * signal
                if h >= target:
                    return target * signal
            return None

        return None

    def _handle_gap(self, i: int, action: str, signal: int, target: float) -> Optional[float]:
        """處理開市跳空（保留你原設計）"""
        gap_method = self.config.gap_entry if action == "entry" else self.config.gap_exit
        o, c = self._np_Open[i], self._np_Close[i]

        if gap_method == "give_up":
            return None
        elif gap_method == "open":
            return o * signal
        elif gap_method == "close":
            return c * signal
        elif gap_method == "wait_close":
            return c * signal
        return o * signal

    def _process_eac_bar(self, i: int, prev_pos: int, signal: int):
        """Exit-at-Close 模式"""
        if prev_pos == 0 and signal != 0:
            price = self._get_order_price(i, "entry", signal, self._np_entry_price[i])
            if price is not None:
                self._np_position[i] = signal
                self._np_entry[i] = price
                self._np_exit[i] = self._np_Close[i]
        else:
            self._np_position[i] = prev_pos

    def _simulate_strong_hold(self):
        """Strong Hold 模式"""
        factor = 1 if self.config.direction == "buy" else -1
        self._np_position[:] = factor
        self._np_entry[0] = -self._np_Open[0] * factor
        self._np_exit[-1] = self._np_Close[-1] * factor
        self._np_position[-1] = 0

    def _close_position_on_last_day(self):
        """最後一日強制平倉"""
        if self._np_position[-1] == 0:
            return
        self._np_position[-1] = 0
        self._np_exit[-1] = self._np_Close[-1] if self._np_position[-2] == 1 else -self._np_Close[-1]

    def _sync_to_dataframe(self):
        """將結果寫回 DataFrame"""
        self.df["position"] = self._np_position
        self.df["entry"] = self._np_entry
        self.df["exit"] = self._np_exit
