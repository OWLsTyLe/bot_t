"""
Завантаження ринкових даних та розрахунок технічних індикаторів.
Джерела: Yahoo Finance та Twelve Data (реальний час FOREX).
"""

from __future__ import annotations

import pandas as pd
import requests
import yfinance as yf

from config import BotConfig


class MarketAnalyzer:
    def __init__(self, config: BotConfig | None = None):
        self.config = config or BotConfig()

    # ---------- Yahoo Finance ----------
    def fetch_data(self) -> pd.DataFrame:
        """Завантажує свечі з Yahoo Finance."""
        ticker = yf.Ticker(self.config.symbol)
        df = ticker.history(interval=self.config.interval, period=self.config.period)

        if df.empty:
            raise ValueError(f"Не вдалося завантажити дані для {self.config.symbol}")

        df = df.rename(columns=str.lower)
        df.index.name = "datetime"
        return df

    # ---------- Twelve Data ----------
    def fetch_twelve_data(self, symbol: str | None = None, interval: str | None = None) -> pd.DataFrame:
        """Завантажує останні свечі з Twelve Data (REST API, реальний час FOREX)."""
        symbol = symbol or self.config.symbol
        interval = interval or self.config.interval
        api_key = self.config.twelve_api_key

        if not api_key:
            raise ValueError("Не вказано TWELVE_DATA_API_KEY у config.py")

        # Конвертуємо інтервал для Twelve Data (1m -> 1min тощо)
        interval_map = {
            "1m": "1min",
            "5m": "5min",
            "15m": "15min",
            "1h": "1h",
        }
        td_interval = interval_map.get(interval, "1min")

        url = f"{self.config.twelve_base_url}/time_series"
        params = {
            "symbol": symbol,
            "interval": td_interval,
            "apikey": api_key,
            "outputsize": self.config.twelve_outputsize,
            "format": "JSON",
        }

        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if "values" not in data:
            msg = data.get("msg", "Невідома помилка Twelve Data")
            raise ValueError(f"Twelve Data: {msg}")

        rows = data["values"]
        df = pd.DataFrame(rows)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime").set_index("datetime")

        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

        df = df.rename(columns=str.lower)
        return df

    # ---------- Індикатори (чистий pandas) ----------
    @staticmethod
    def _ema(series: pd.Series, length: int) -> pd.Series:
        return series.ewm(span=length, adjust=False).mean()

    @staticmethod
    def _rsi(series: pd.Series, length: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = (-delta.clip(upper=0))
        avg_gain = gain.rolling(window=length, min_periods=1).mean()
        avg_loss = loss.rolling(window=length, min_periods=1).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
        macd_hist = macd_line - macd_signal
        return macd_line, macd_signal, macd_hist

    @staticmethod
    def _bollinger(series: pd.Series, length: int = 20, std: float = 2.0):
        rolling_mean = series.rolling(window=length, min_periods=1).mean()
        rolling_std = series.rolling(window=length, min_periods=1).std()
        upper = rolling_mean + std * rolling_std
        lower = rolling_mean - std * rolling_std
        return lower, rolling_mean, upper

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Додає EMA, RSI, MACD та Боллінґери."""
        df = df.copy()
        close = df["close"]

        # Тренд
        df["ema_fast"] = self._ema(close, 9)
        df["ema_slow"] = self._ema(close, 21)

        # Момент / перекупленість
        df["rsi"] = self._rsi(close, 14)

        # MACD
        macd, macd_signal, macd_hist = self._macd(close, 12, 26, 9)
        df["macd"] = macd
        df["macd_signal"] = macd_signal
        df["macd_hist"] = macd_hist

        # Боллінґери
        lower, middle, upper = self._bollinger(close, 20, 2.0)
        df["BBL_20_2.0"] = lower
        df["BBM_20_2.0"] = middle
        df["BBU_20_2.0"] = upper

        return df

    # ---------- Аналіз ----------
    def analyze(self) -> tuple[pd.Series, pd.DataFrame]:
        """Yahoo Finance: остання свеча з індикаторами і весь DataFrame."""
        df = self.fetch_data()
        df = self.add_indicators(df)
        last = df.iloc[-1]
        return last, df

    def analyze_twelve(self, symbol: str | None = None, interval: str | None = None) -> tuple[pd.Series, pd.DataFrame]:
        """Twelve Data: остання свеча з індикаторами і весь DataFrame."""
        df = self.fetch_twelve_data(symbol=symbol, interval=interval)
        df = self.add_indicators(df)
        last = df.iloc[-1]
        return last, df