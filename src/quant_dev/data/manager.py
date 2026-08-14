# quant_dev/data/manager.py
"""
DataManager - Unified data management entry point (Standalone Version).
Fully self-contained, with no dependency on on_finance modules.

Usage:
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
    Unified data manager (Standalone Version).

    Index conventions:
    - Daily bars: date-only (timezone-naive)
    - Intraday bars: UTC datetime (timezone-naive, UTC values)
    """

    def __init__(
        self,
        market_tz: str = "America/New_York",
        data_dir: Optional[str] = None,
    ):
        """
        Initialize the DataManager.

        Args:
            market_tz: Market timezone (default: America/New_York)
            data_dir: Directory for storing cached data (default: ./data)
        """
        self.data_dir = Path(data_dir) if data_dir else Path("data")
        self.market_tz = market_tz
        self._tz = pytz.timezone(market_tz)

        # Ensure data directory exists
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
        Retrieve data (from cache or download).

        Args:
            ticker: Stock symbol (e.g., 'AAPL', 'BTC-USD')
            timeframe: Timeframe ('1d', '1h', '30m', '15m', '5m', '1m')
            days: Number of days to fetch
            prepost: Include pre-market / after-hours data
            auto_adjust: Auto-adjust prices
            force_download: Force re-download even if cache exists

        Returns:
            DataFrame containing OHLCV data
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
        Load data from CSV (supports Yahoo Finance MultiIndex format).

        Args:
            ticker: Stock symbol
            timeframe: Timeframe
            prepost: Include pre-market / after-hours data
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            DataFrame containing OHLCV data
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
        Fetch data for multiple symbols in batch.

        Args:
            tickers: List of stock symbols
            timeframe: Timeframe
            days: Number of days to fetch
            prepost: Include pre-market / after-hours data

        Returns:
            List of DataFrames
        """
        dfs = []
        for ticker in tickers:
            df = self.get_or_fetch(ticker, timeframe, days, prepost)
            dfs.append(df)
        return dfs

    # ================================================================
    # Internal Methods 
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
        Download single stock data (internal method).
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
        Read CSV (standard format).
        Assumes the first column is 'Date', parsed as datetime.
        """ 
        # 標準格式：第一欄係 Date
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        # ✅ 確保 index name 係 'Date'
        if df.index.name is None:
            df.index.name = 'Date'
        return df 


    def _save_csv(self, df: pd.DataFrame, file_path: Path) -> None:
        """
        Save CSV (standard format, no MultiIndex).
        Style follows on_finance/data/loader.py.
        """
        df.to_csv(file_path)

    def _get_cache_path(self, ticker: str, interval: str, prepost: bool) -> Path:
        """
        Get cache file path.
        Style follows on_finance/data/loader.py.
        """
        folder = self.data_dir / ("datetime_ohlc" if interval in ("2m", "5m", "15m", "30m", "60m") else "")
        folder.mkdir(parents=True, exist_ok=True)
        filename = f"{ticker}_prepost.csv" if prepost else f"{ticker}.csv"
        return folder / filename

    def _timeframe_to_interval(self, timeframe: str) -> str:
        """Convert timeframe to yfinance interval."""
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
    # Index Normalization 
    # ================================================================

    def _normalize_index(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Normalize index format:
        - Daily bars: date-only DatetimeIndex (timezone-naive)
        - Intraday bars: UTC datetime (timezone-naive, UTC values)
        """
        df = df.copy()

        if timeframe == "1d":
            df = self._normalize_daily_index(df)
        else:
            df = self._normalize_intraday_index(df)

        df = df.sort_index()
        return df

    def _normalize_daily_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """Daily bars → date-only (timezone-naive)."""
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, utc=True)

        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        df.index = df.index.normalize()
        return df

    def _normalize_intraday_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """Intraday bars → UTC datetime (timezone-naive)."""
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, utc=True)

        if df.index.tz is None:
            df.index = df.index.tz_localize(self.market_tz)
        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC")
        df.index = df.index.tz_localize(None)
        return df

    # ================================================================
    # Timezone Helpers 
    # ================================================================

    def to_market_time(self, dt) -> datetime:
        """Convert UTC time to market local time."""
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
        """Get current time in market timezone."""
        return datetime.now(self._tz)

    def info(self, df: pd.DataFrame) -> str:
        """Display debug information for the DataFrame."""
        return (
            f"Shape: {df.shape}\n"
            f"Index type: {type(df.index)}\n"
            f"Index[0]: {df.index[0]}\n"
            f"Index[-1]: {df.index[-1]}\n"
            f"Has TZ: {df.index.tz is not None}\n"
            f"Market TZ: {self.market_tz}\n"
            f"Columns: {list(df.columns)}"
        )