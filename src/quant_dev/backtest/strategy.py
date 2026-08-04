# src/quant_dev/backtest/strategy.py
"""
Strategy - 回測引擎 (Public Version)
支援 Stop/Limit/Market Order，多種交易模式
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class StrategyConfig:
    """策略配置"""
    ticker: str
    timeframe: str = "1d"
    direction: str = "buy"  # "buy" or "sell"
    mode: str = "normal"  # "normal", "exit_at_close", "strong_hold"
    entry_order_type: str = "market"  # "market", "limit", "stop"
    exit_order_type: str = "market"
    gap_entry: str = "open"  # "open", "close", "give_up", "wait_close", "wait_give_up"
    gap_exit: str = "open"
    initial_capital: float = 100000.0
    params: Dict[str, Any] = field(default_factory=dict)


class Strategy:
    """輕量級回測引擎，支援多種訂單類型與交易模式"""

    def __init__(self, config: StrategyConfig, data: pd.DataFrame):
        self.config = config
        self.df = data.copy()
        self._validate_data()
        self._init_columns()

    def _validate_data(self):
        """驗證輸入數據"""
        required = ["Open", "High", "Low", "Close"]
        if not all(c in self.df.columns for c in required):
            raise ValueError("DataFrame 必須包含 Open, High, Low, Close")
        if self.df.empty:
            raise ValueError("DataFrame 不能為空")

    def _init_columns(self):
        """初始化結果欄位"""
        self.df["position"] = 0
        self.df["entry"] = np.nan
        self.df["exit"] = np.nan
        self.df["signal"] = 0

    def add_signal(self, signal_series: pd.Series):
        """
        加入交易信號
        signal_series: 1 = 買入, -1 = 賣出, 0 = 觀望
        """
        if len(signal_series) != len(self.df):
            raise ValueError("信號長度必須與數據一致")
        self.df["signal"] = signal_series.values

    def run(self) -> "Strategy":
        """執行回測"""
        self._prepare_arrays()
        self._simulate()
        self._sync_to_dataframe()
        return self

    def _prepare_arrays(self):
        """將DataFrame轉為numpy array"""
        cols = ["Open", "High", "Low", "Close", "signal"]
        for col in cols:
            setattr(self, f"_np_{col.lower()}", self.df[col].to_numpy(dtype=float))
        self._np_position = np.zeros(len(self.df), dtype=int)
        self._np_entry = np.full(len(self.df), np.nan)
        self._np_exit = np.full(len(self.df), np.nan)

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
        """處理單一K線"""
        prev_pos = self._np_position[i - 1] if i > 0 else 0
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

    def _process_eac_bar(self, i: int, prev_pos: int, signal: int):
        """Exit-at-Close 模式"""
        if prev_pos == 0 and signal != 0:
            price = self._get_order_price(i, "entry", signal)
            if price is not None:
                self._np_position[i] = signal
                self._np_entry[i] = price
                self._np_exit[i] = self._np_close[i]  # 收市平倉
        else:
            self._np_position[i] = prev_pos

    def _simulate_strong_hold(self):
        """Strong Hold 模式：開市買入，最後一日賣出"""
        factor = 1 if self.config.direction == "buy" else -1
        self._np_position[:] = factor
        self._np_entry[0] = -self._np_open[0] * factor
        self._np_exit[-1] = self._np_close[-1] * factor
        self._np_position[-1] = 0

    def _try_entry(self, i: int, signal: int):
        """嘗試入場"""
        if signal == 0:
            return
        if self.config.direction == "buy" and signal != 1:
            return
        if self.config.direction == "sell" and signal != -1:
            return

        price = self._get_order_price(i, "entry", signal)
        if price is not None:
            self._np_position[i] = signal
            self._np_entry[i] = price

    def _try_exit(self, i: int, signal: int, holding: str):
        """嘗試出場"""
        exit_signal = -1 if holding == "buy" else 1
        if signal != exit_signal:
            self._np_position[i] = 1 if holding == "buy" else -1
            return

        price = self._get_order_price(i, "exit", signal)
        if price is not None:
            self._np_position[i] = 0
            self._np_exit[i] = abs(price)

    def _get_order_price(self, i: int, action: str, signal: int) -> Optional[float]:
        """
        根據訂單類型計算成交價
        signal: 1=買入, -1=賣出
        """
        order_type = self.config.entry_order_type if action == "entry" else self.config.exit_order_type
        o, h, l, c = self._np_open[i], self._np_high[i], self._np_low[i], self._np_close[i]

        if order_type == "market":
            return o * signal

        # 計算目標價（用簡單的移動平均作為示例，你可改為自己的邏輯）
        target = self._calculate_target_price(i, action)

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

    def _calculate_target_price(self, i: int, action: str) -> float:
        """計算目標價（可被覆寫）"""
        # 預設：用前20日收市價平均
        if i < 20:
            return self._np_close[i] * 0.99 if action == "entry" else self._np_close[i] * 1.01
        return np.mean(self._np_close[i-20:i]) * 0.99 if action == "entry" else np.mean(self._np_close[i-20:i]) * 1.01

    def _handle_gap(self, i: int, action: str, signal: int, target: float) -> Optional[float]:
        """處理開市跳空"""
        gap_method = self.config.gap_entry if action == "entry" else self.config.gap_exit
        o, c = self._np_open[i], self._np_close[i]

        if gap_method == "give_up":
            return None
        elif gap_method == "open":
            return o * signal
        elif gap_method == "close":
            return c * signal
        elif gap_method == "wait_close":
            return c * signal
        return o * signal

    def _close_position_on_last_day(self):
        """最後一日強制平倉"""
        if self._np_position[-1] == 0:
            return
        self._np_position[-1] = 0
        self._np_exit[-1] = self._np_close[-1] if self._np_position[-2] == 1 else -self._np_close[-1]

    def _sync_to_dataframe(self):
        """將結果寫回DataFrame"""
        self.df["position"] = self._np_position
        self.df["entry"] = self._np_entry
        self.df["exit"] = self._np_exit

    def get_performance_metrics(self) -> Dict[str, float]:
        """計算績效指標"""
        # 計算每日回報
        self.df["daily_return"] = self.df["Close"].pct_change().fillna(0)
        self.df["strategy_return"] = self.df["position"].shift(1).fillna(0) * self.df["daily_return"]
        self.df["equity"] = self.config.initial_capital * (1 + self.df["strategy_return"]).cumprod()

        total_return = (1 + self.df["strategy_return"]).prod() - 1
        n = len(self.df)
        annual_return = (1 + total_return) ** (252 / n) - 1 if n > 0 else 0
        volatility = self.df["strategy_return"].std() * np.sqrt(252) if n > 1 else 0
        sharpe = annual_return / volatility if volatility > 0 else 0
        max_dd = (self.df["equity"].cummax() - self.df["equity"]).max() / self.df["equity"].max() if self.df["equity"].max() > 0 else 0

        return {
            "Total Return (%)": round(total_return * 100, 2),
            "Annual Return (%)": round(annual_return * 100, 2),
            "Sharpe Ratio": round(sharpe, 2),
            "Max Drawdown (%)": round(max_dd * 100, 2),
        }
