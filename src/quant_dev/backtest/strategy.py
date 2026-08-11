# quant_dev/backtest/strategy.py
"""
精簡版回測引擎 (Strategy)
保留核心：Order Type, Gap Handling for swing trade
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional 
from dataclasses import dataclass 
from ..data.manager import DataManager

import logging
logger = logging.getLogger(__name__) 
# ================================================= #
pd.set_option("display.max_columns", None)
# ================================================= #
@dataclass
class StrategyOption:
    """策略配置"""
    ticker: str
    direction: str = "buy"              # "buy" / "sell"
    entry_order_type: str = "stop"    # "market" / "limit" / "stop"
    exit_order_type: str = "stop"
    gap_entry: str = "open"             # "open" / "close" / "give_up" / "wait_close" / "wait_give_up"
    gap_exit: str = "open"
    market_tz: str = "America/New_York"
    timeframe: str = "1d"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    df: Optional[pd.DataFrame] = None

# ================================================= #
class Strategy:
    """
    策略回測引擎
    支援：
    - Stop / Limit / Market Order 
    - 統一 Gap Handling 
    """
# ------------------------------------------------- #
    def __init__(self, option: StrategyOption):
        """
        初始化 Strategy
        
        Args:
            option: StrategyOption 物件
            data: 必須包含 Open, High, Low, Close 嘅 DataFrame
                以及 signal_b, signal_s, entry_price, exit_price 4 個 columns
        """
        self.option = option 
        self.ticker = option.ticker
        self.direction = option.direction
        self.entry_order_type = option.entry_order_type
        self.exit_order_type = option.exit_order_type
        self.gap_entry = option.gap_entry
        self.gap_exit = option.gap_exit
        self.mode = "normal"  # 只支援 normal mode

        if option.df is not None:
            self.df = option.df.copy()
        else:
            # ===== DataManager 載入數據 ===== 
            dm = DataManager(market_tz=self.option.market_tz)
            self.df = dm.load_csv(
                ticker=self.option.ticker,
                timeframe=self.option.timeframe,
                start_date=self.option.start_date,
                end_date=self.option.end_date,
            )

        self.length = len(self.df)

        # 確保 df 有 required columns (OHLC)
        self._check_ohlc() 
        # 驗證策略參數
        self._check_strategy_input()

        # 初始化結果 columns
        self._init_columns() 
# ================================================= #
# Init Helpers
# ================================================= #
    def _check_ohlc(self):
        if self.df.empty:
            raise ValueError(f"輸入的{self.option.ticker} DataFrame 是空的")
        if not {"Open", "High", "Low", "Close"}.issubset(self.df.columns):
            raise ValueError('DataFrame必須包含"Open", "High", "Low", "Close"列') 
# ------------------------------------------------- #
    def _check_strategy_input(self):
        if self.direction not in ["buy", "sell"]:
            import textwrap
            raise ValueError(textwrap.dedent(f"""
                ❌ 參數錯誤 ❌
                ==============
                🔹 你輸入: {self.direction}
                🔹 但 direction 要係:
                - 'buy'  📈 (做多)
                - 'sell' 📉 (做空)
                """))

        if any(x not in ["give_up", "open", "close", "wait_close", "wait_give_up"] 
                for x in [self.gap_exit, self.gap_entry]):
            import textwrap
            raise ValueError(textwrap.dedent(f"""
                ❌ 參數唔啱規矩啊老友！ ❌
                ==========================
                🌀 你輸入咗:
                gap_exit = '{self.gap_exit}'
                gap_entry = '{self.gap_entry}'
                    
                📜 但係我淨係接受以下選擇:
                - 'give_up'      🙅‍♂️ 放棄交易
                - 'open'         🚪 開倉
                - 'close'        🔒 平倉
                - 'wait_close'   ⏳ 等平倉
                - 'wait_give_up' 💤 等放棄

                💡 提示: 檢查吓係咪串錯字？
                """)) 
        return True
# ------------------------------------------------- #
    def _init_columns(self):
        """初始化結果 columns"""
        self.df["position"] = np.zeros(self.length, dtype=int)  # 持倉狀態
        self.df["entry"] = np.full(self.length, np.nan)  # 買入價
        self.df["exit"] = np.full(self.length, np.nan)  # 賣出價 

# Public API — Run Strategy
# ================================================= #
    def run(self) -> "Strategy":
        """執行回測"""
        # ✅ 喺執行前檢查 4 個必要 columns (signal_b, signal_s, entry_price, exit_price)
        self._check_required_columns()
        
        self._prepare_numpy_arrays()
        self._simulate_trades()
        self._sync_to_dataframe()
        return self
# ================================================= #
# Internal — Data Preparation
# ================================================= #
    def _check_required_columns(self):
        """檢查用戶有冇提供必要嘅 4 個 columns"""
        required = ['signal_b', 'signal_s', 'entry_price', 'exit_price']
        missing = [c for c in required if c not in self.df.columns]
        if missing:
            raise ValueError(f"DataFrame 缺少必要 columns: {missing}")
# ------------------------------------------------- #
    def _prepare_numpy_arrays(self):
        """將 DataFrame 轉為 numpy array"""
        self.np_open = self.df["Open"].to_numpy(dtype=float)
        self.np_high = self.df["High"].to_numpy(dtype=float)
        self.np_low = self.df["Low"].to_numpy(dtype=float)
        self.np_close = self.df["Close"].to_numpy(dtype=float)
        self.np_signal_b = self.df["signal_b"].to_numpy(dtype=bool)
        self.np_signal_s = self.df["signal_s"].to_numpy(dtype=bool)
        self.np_entry_price = self.df["entry_price"].to_numpy(dtype=float)
        self.np_exit_price = self.df["exit_price"].to_numpy(dtype=float)
        
        # 結果 arrays（將會被填充）
        self.np_position = np.zeros(self.length, dtype=int)
        self.np_entry = np.full(self.length, np.nan)
        self.np_exit = np.full(self.length, np.nan) 
        
# ================================================= #
# Internal — Trade Simulation (Core)
# ================================================= #
    def _simulate_trades(self):
        """主模擬循環（只保留 normal mode）"""
        # 從第 1 日開始（第 0 日冇前一日數據）
        for i in range(1, self.length):
            self._process_bar(i)
        # 最後一日強制平倉
        self._close_position_on_last_day()         
# ------------------------------------------------- # 
    def _sync_to_dataframe(self):
        """將 numpy arrays 同步返 DataFrame"""
        self.df["position"] = self.np_position
        self.df["entry"] = self.np_entry
        self.df["exit"] = self.np_exit
# ------------------------------------------------- # 
    def _process_bar(self, i: int):
        """
        處理單一 K 線 
        - normal: 正常 entry/exit 
        """
        prev_pos = self.np_position[i - 1]
        """Normal mode: 持倉跟隨信號"""
        if prev_pos == 0:
            self._try_entry(i)
        elif prev_pos == 1:
            self._try_exit(i, "buy")
        elif prev_pos == -1:
            self._try_exit(i, "sell") 
# ------------------------------------------------- #  
    def _close_position_on_last_day(self):
        # 處理最後一日仍持倉嘅情況  
        if self.np_position[-1] == 0:
            return  # 冇持倉，唔使做

        # 搵最後一個有效 close price
        close_to_use = self.np_close[-1]
        if np.isnan(close_to_use):
            # Fallback: 由尾向前搵第一個 non-NaN close
            for j in range(len(self.np_close) - 2, -1, -1):
                if not np.isnan(self.np_close[j]):
                    close_to_use = self.np_close[j]
                    break 
        if np.isnan(close_to_use):
            logger.error("❗️ 完全冇 close data, 請檢查下載的 csv")
            return  

        if self.np_position[-1] == 1:  # 如果最後持好倉 
            self.np_position[-1] = 0  # 強制平倉
            if np.isnan(self.np_exit[-1]):
                self.np_exit[-1] = close_to_use  # 用收市價平倉  
        elif self.np_position[-1] == -1:  # 如果最後持淡倉  
            self.np_position[-1] = 0  # 強制平倉
            if np.isnan(self.np_exit[-1]):
                self.np_exit[-1] = -close_to_use  # 用收市價平倉 (注意負號)
 
        return
# ------------------------------------------------- #
# ================================================= #
# Entry / Exit Logic
# ================================================= #
    def _try_entry(self, i: int):
        """嘗試入場"""
        if self.direction == "buy" and self._has_signal(i, "buy"):
            price = self._get_order_price(i, "entry", "buy", self.np_entry_price[i], self.entry_order_type)
            if price is not None:
                self.np_position[i] = 1
                self.np_entry[i] = price
                return

        elif self.direction == "sell" and self._has_signal(i, "sell"):
            price = self._get_order_price(i, "entry", "sell", self.np_entry_price[i], self.entry_order_type)
            if price is not None:
                self.np_position[i] = -1
                self.np_entry[i] = price
                return
    # ------------------------------------------------- #
    def _try_exit(self, i: int, holding_direction: str):
        """嘗試出場。holding_direction: 'buy' (好倉) 或 'sell' (淡倉)"""
        if holding_direction == "buy":
            # 平好倉 = 沽貨 → 用 'sell' direction 去做 stop/limit 判斷
            if self._has_signal(i, "sell"):
                price = self._get_order_price(
                    i, "exit", "sell",           # ← direction='sell'
                    self.np_exit_price[i],
                    self.exit_order_type
                )
                if price is not None:
                    self.np_position[i] = 0
                    self.np_exit[i] = abs(price)  # 沽貨收錢，強制正數
                    return
            self.np_position[i] = 1  # 保持好倉
        else:
            # 平淡倉 = 買貨 → 用 'buy' direction
            if self._has_signal(i, "buy"):
                price = self._get_order_price(
                    i, "exit", "buy",            # ← direction='buy'
                    self.np_exit_price[i],
                    self.exit_order_type
                )
                if price is not None:
                    self.np_position[i] = 0
                    self.np_exit[i] = -abs(price)  # 買貨俾錢，強制負數
                    return
            self.np_position[i] = -1  # 保持淡倉
# ------------------------------------------------- #
# ================================================= #
# Internal — Signal Check
# ================================================= #
    def _has_signal(self, i: int, signal_type: str) -> bool:
        """檢查有冇信號"""
        if signal_type == "buy":
            return bool(self.np_signal_b[i])
        else:  # "sell"
            return bool(self.np_signal_s[i])
# ------------------------------------------------- #
# ================================================= #
# Internal — Order Type Logic
# ================================================= #
    def _get_order_price(
            self, i: int, action: str, direction: str,
            target: float, order_type: str
    ) -> Optional[float]:
        """
        根據 order type 決定成交價
        Args:
            i: bar index
            action: "entry" or "exit"
            direction: "buy" or "sell"
            target: target price (from entry_price / exit_price column)
            order_type: "stop", "limit", or "market"

        Returns:
            成交價 (buy 負數, sell 正數), None 表示唔成交
        """
        if order_type == "market":
            sign = -1 if direction == "buy" else 1
            return sign * self.np_open[i]

        o, h, l, c = self.np_open[i], self.np_high[i], self.np_low[i], self.np_close[i]

        if order_type == "stop":
            return self._check_stop(i, action, direction, target, o, h, l, c)
        elif order_type == "limit":
            return self._check_limit(direction, target, o, h, l)

        return None 
# ================================================= #
    def _check_stop(
            self, i: int, action: str, direction: str,
            target: float, o: float, h: float, l: float, c: float
    ) -> Optional[float]:
        """
        Stop order: 價格突破目標價先成交
        Buy stop: 升穿 → 買入
        Sell stop: 跌穿 → 沽空
        """
        if direction == "buy":
            if o >= target:
                return self._handle_gap(action, i, direction, target)
            if h >= target:
                return -target
            return None
        else:
            if o <= target:
                return self._handle_gap(action, i, direction, target)
            if l <= target:
                return target
            return None
# ------------------------------------------------- #
    def _check_limit(self, direction, target, o, h, l):
        """Limit order: 到價就成交"""
        if direction == "buy":
            if o <= target:
                # 開市已到價 → 直接用 open（比掛單價更好或相等）
                return -o
            if l <= target:
                return -target
            return None
        else:
            if o >= target:
                return o
            if h >= target:
                return target
            return None
# ================================================= #
# Gap Handling (Unified)
# ================================================= #
    def _handle_gap(
            self, action: str, i: int, direction: str, target: float
    ) -> Optional[float]:
        """
        統一處理開市跳空
        Args:
            action: "entry" or "exit"
            i: bar index
            direction: "buy" or "sell"
            target: target price
        Returns:
            成交價 or None (give_up)
        """
        gap_method = self.gap_entry if action == "entry" else self.gap_exit
        o, h, l, c = self.np_open[i], self.np_high[i], self.np_low[i], self.np_close[i]
        sign = -1 if direction == "buy" else 1

        if gap_method == "give_up":
            return None
        elif gap_method == "open":
            return sign * o
        elif gap_method == "close":
            return sign * c
        elif gap_method == "wait_close":
            if direction == "buy":
                return sign * (target if l <= target else c)
            else:
                return sign * (target if h >= target else c)
        elif gap_method == "wait_give_up":
            if direction == "buy":
                return sign * target if l <= target else None
            else:
                return sign * target if h >= target else None

        return sign * o  # Default: open price

# ================================================= # 
    def get_trade_log(self, rolling=0):
        """
        提取交易日誌
        Args:
            rolling: 包含交易前後 n 行
        Returns:
            DataFrame with trades + surrounding n rows
        """
        # 創建非NaN標記（1表示非NaN，0表示NaN）
        non_nan_flag = (self.df["entry"].notna() | self.df["exit"].notna()).astype(int)

        # 設置窗口大小為 n+1（包含非NaN行及其後n行 - 但我們要前n行）
        window_size = rolling + 1

        # 使用rolling窗口但調整方向 - 反轉數據
        reversed_flag = non_nan_flag[::-1]  # 反轉序列

        # 在反轉的數據上使用rolling窗口
        rolling_sum = reversed_flag.rolling(window=window_size, min_periods=1).sum()

        # 再反轉回來
        final_flag = rolling_sum[::-1] > 0

        return self.df[final_flag]   
# ------------------------------------------------- #
# ------------------------------------------------- #
# ------------------------------------------------- #
# ------------------------------------------------- # 
# ------------------------------------------------- #
# ------------------------------------------------- # 
# ------------------------------------------------- #

# ================================================= #
# ------------------------------------------------- #
# ------------------------------------------------- #
# ------------------------------------------------- #
# ------------------------------------------------- #
# ------------------------------------------------- #
# ------------------------------------------------- # 
# ================================================= #


























