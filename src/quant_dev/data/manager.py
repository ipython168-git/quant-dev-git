# src/quant_dev/data/manager.py

import yfinance as yf
import pandas as pd
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta

class DataManager:
    def get_or_fetch(
        self,
        ticker: str,
        timeframe: str = "1d",
        days: int = 365,
        prepost: bool = False,
        auto_adjust: bool = True,
        force_download: bool = False,
    ) -> pd.DataFrame:
        """Get data from cache or download"""
        # 1. Check cache (CSV)
        cache_path = self.data_dir / f"{ticker}_{timeframe}.csv"
        if not force_download and cache_path.exists():
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return self._normalize_index(df, timeframe)
        
        # 2. Download
        end = datetime.now()
        start = end - timedelta(days=days)
        df = yf.download(
            ticker, start=start, end=end, 
            interval=timeframe, prepost=prepost, auto_adjust=auto_adjust,
            progress=False
        )
        
        # 3. Cache
        df.to_csv(cache_path)
        return self._normalize_index(df, timeframe)
