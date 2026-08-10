# src/quant_dev/data/manager.py
"""
DataManager - 統一數據管理入口 (Standalone Version)
完全自包含，不依賴 on_finance 任何模組。

用法：
    dm = DataManager()
    df = dm.get_or_fetch("AAPL", timeframe="1d", days=365)
    df = dm.load_csv("AAPL", timeframe="1d", start_date="2025-01-01")
"""
import pytz
import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, List, Union
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DataManager:
    """
    統一數據管理器 (Standalone Version)
    Index 原則：
    - 日K：純日期 (date-only, timezone-naive)
    - 分鐘K：UTC datetime (timezone-naive, UTC values)
    """

    def __init__(
        self,
        market_tz: str = "America/New_York",
        data_dir: Optional[str] = None,
    ):
        """
        初始化 DataManager

        Args:
            market_tz: 市場時區 (預設美國東部時間)
            data_dir: 數據儲存目錄 (預設為當前目錄下的 data/)
        """
        self.data_dir = Path(data_dir) if data_dir else Path("data")
        self.market_tz = market_tz
        self._tz = pytz.timezone(market_tz)

        # 確保數據目錄存在
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ================================================================
    # Public API
    # ================================================================

    def get_or_fetch(
        self,
        ticker: str,
        timeframe: str = "1d",
        days: int = 365,
        prepost: bool = False,
        auto_adjust: bool = True,
        force_download: bool = False,
    ) -> pd.DataFrame:
        """
        獲取數據 (從快取或下載)

        Args:
            ticker: 股票代號 (如 'AAPL', 'BTC-USD')
            timeframe: 時間週期 ('1d', '1h', '30m', '15m', '5m', '1m')
            days: 獲取天數
            prepost: 是否包含盤前盤後
            auto_adjust: 是否自動調整價格
            force_download: 是否強制重新下載

        Returns:
            包含 OHLCV 的 DataFrame
        """
        interval = self._timeframe_to_interval(timeframe)

        # 1. 檢查快取 (CSV)
        cache_path = self._get_cache_path(ticker, interval, prepost)
        if not force_download and cache_path.exists():
            logger.info(f"📂 載入快取: {cache_path}")
            df = self._read_csv(cache_path)
            return self._normalize_index(df, timeframe)

        # 2. 下載數據
        logger.info(f"🌐 下載數據: {ticker} ({timeframe})")
        df = self._download(
            ticker=ticker,
            interval=interval,
            days=days,
            prepost=prepost,
            auto_adjust=auto_adjust,
        )

        # 3. 儲存快取
        self._save_csv(df, cache_path)
        logger.info(f"💾 快取已儲存: {cache_path}")

        return self._normalize_index(df, timeframe)

    def load_csv(
        self,
        ticker: str,
        timeframe: str = "1d",
        prepost: bool = False,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        從 CSV 載入數據 (支援 Yahoo Finance MultiIndex 格式)

        Args:
            ticker: 股票代號
            timeframe: 時間週期
            prepost: 是否包含盤前盤後
            start_date: 開始日期 (可選)
            end_date: 結束日期 (可選)

        Returns:
            包含 OHLCV 的 DataFrame
        """
        interval = self._timeframe_to_interval(timeframe)
        file_path = self._get_cache_path(ticker, interval, prepost)

        if not file_path.exists():
            raise FileNotFoundError(f"CSV not found: {file_path}")

        # 嘗試讀取，支援 MultiIndex (Yahoo Finance 格式)
        try:
            df = self._read_csv(file_path)
        except Exception as e:
            logger.warning(f"MultiIndex read failed, trying standard read: {e}")
            df = pd.read_csv(file_path, index_col=0)
            df.index = pd.to_datetime(df.index, utc=True)

        df = self._normalize_index(df, timeframe)

        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]

        return df

    def batch_get_or_fetch(
        self,
        tickers: List[str],
        timeframe: str = "1d",
        days: int = 365,
        prepost: bool = False,
    ) -> List[pd.DataFrame]:
        """
        批量獲取多個股票數據

        Args:
            tickers: 股票代號列表
            timeframe: 時間週期
            days: 獲取天數
            prepost: 是否包含盤前盤後

        Returns:
            DataFrame 列表
        """
        dfs = []
        for ticker in tickers:
            df = self.get_or_fetch(ticker, timeframe, days, prepost)
            dfs.append(df)
        return dfs

    # ================================================================
    # Internal Methods (參考 on_finance 風格)
    # ================================================================

    def _download(
        self,
        ticker: str,
        interval: str = "1d",
        days: int = 365,
        prepost: bool = False,
        auto_adjust: bool = True,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        下載單一股票 (內部方法)
        風格抄返 on_finance/data/loader.py
        """
        ticker = ticker.upper()

        if end is None:
            tz = pytz.timezone(self.market_tz)
            end = datetime.now(tz)
        elif end.tzinfo is None:
            raise ValueError("'end' must be timezone-aware")

        stock = yf.Ticker(ticker)
        start = end - timedelta(days=days)
        df = stock.history(
            start=start,
            end=end,
            interval=interval,
            prepost=prepost,
            auto_adjust=auto_adjust,
        )

        ohlc_cols = ["Open", "High", "Low", "Close", "Volume"]
        df = df[[c for c in ohlc_cols if c in df.columns]]

        return df

    def _read_csv(self, file_path: Path) -> pd.DataFrame:
        """
        讀取 CSV (標準格式)
        假設第一欄係 Date，會 parse 做 datetime
        """ 
        # 標準格式：第一欄係 Date
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        # ✅ 確保 index name 係 'Date'
        if df.index.name is None:
            df.index.name = 'Date'
        return df 


    def _save_csv(self, df: pd.DataFrame, file_path: Path) -> None:
        """
        儲存 CSV (標準格式，唔用 MultiIndex)
        風格抄返 on_finance/data/loader.py
        """
        df.to_csv(file_path)

    def _get_cache_path(self, ticker: str, interval: str, prepost: bool) -> Path:
        """
        獲取快取檔案路徑
        風格抄返 on_finance/data/loader.py
        """
        folder = self.data_dir / ("datetime_ohlc" if interval in ("2m", "5m", "15m", "30m", "60m") else "")
        folder.mkdir(parents=True, exist_ok=True)
        filename = f"{ticker}_prepost.csv" if prepost else f"{ticker}.csv"
        return folder / filename

    def _timeframe_to_interval(self, timeframe: str) -> str:
        """將 timeframe 轉換為 yfinance interval"""
        mapping = {
            "1d": "1d",
            "1h": "60m",
            "30m": "30m",
            "15m": "15m",
            "5m": "5m",
            "2m": "2m",
            "1m": "1m",
        }
        return mapping.get(timeframe, timeframe)

    # ================================================================
    # Index Normalization (同你原本一樣，冇改)
    # ================================================================

    def _normalize_index(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        統一 index 格式：
        - 日K：純日期 DatetimeIndex（timezone-naive）
        - 分鐘K：UTC datetime（timezone-naive, UTC values）
        """
        df = df.copy()

        if timeframe == "1d":
            df = self._normalize_daily_index(df)
        else:
            df = self._normalize_intraday_index(df)

        df = df.sort_index()
        return df

    def _normalize_daily_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """日K → 純日期（timezone-naive）"""
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, utc=True)

        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        df.index = df.index.normalize()
        return df

    def _normalize_intraday_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """分鐘K → UTC datetime (timezone-naive)"""
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, utc=True)

        if df.index.tz is None:
            df.index = df.index.tz_localize(self.market_tz)
        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC")
        df.index = df.index.tz_localize(None)
        return df

    # ================================================================
    # Timezone Helpers (你原本嘅功能)
    # ================================================================

    def to_market_time(self, dt) -> datetime:
        """將 UTC 時間轉換為市場當地時間"""
        if isinstance(dt, np.datetime64):
            dt = pd.Timestamp(dt).to_pydatetime()
        elif isinstance(dt, pd.Timestamp):
            dt = dt.to_pydatetime()

        if dt.tzinfo is None:
            dt = self._tz.localize(dt.replace(tzinfo=pytz.UTC))
        else:
            dt = dt.astimezone(self._tz)

        return dt

    def now_market(self) -> datetime:
        """獲取當前市場時間"""
        return datetime.now(self._tz)

    def info(self, df: pd.DataFrame) -> str:
        """顯示 DataFrame 的調試資訊"""
        return (
            f"Shape: {df.shape}\n"
            f"Index type: {type(df.index)}\n"
            f"Index[0]: {df.index[0]}\n"
            f"Index[-1]: {df.index[-1]}\n"
            f"Has TZ: {df.index.tz is not None}\n"
            f"Market TZ: {self.market_tz}\n"
            f"Columns: {list(df.columns)}"
        )