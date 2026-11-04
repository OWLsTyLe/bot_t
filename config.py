"""
Конфігурація бота.
Тут можна змінювати тикер, інтервал, порогові значення індикаторів тощо.
"""

from dataclasses import dataclass


# --- Популярні валютні пари FOREX через Yahoo Finance ---
FOREX_SYMBOLS: list[str] = [
    "EURUSD=X",   # Євро / Долар
    "GBPUSD=X",   # Фунт стерлінгів / Долар
    "USDJPY=X",   # Долар / Йена
    "AUDUSD=X",   # Австралійський долар / Долар США
    "USDCAD=X",   # Долар США / Канадський долар
    "USDCHF=X",   # Долар США / Швейцарський франк
    "NZDUSD=X",   # Новозеландський долар / Долар США
    "EURGBP=X",   # Євро / Фунт
    "EURJPY=X",   # Євро / Йена
    "GBPJPY=X",   # Фунт / Йена
]

# --- Популярні валютні пари FOREX через Twelve Data (формат SYMBOL/SYMBOL) ---
FOREX_SYMBOLS_TWELVE: list[str] = [
    "EUR/USD",   # Євро / Долар
    "GBP/USD",   # Фунт стерлінгів / Долар
    "USD/JPY",   # Долар / Йена
    "AUD/USD",   # Австралійський долар / Долар США
    "USD/CAD",   # Долар США / Канадський долар
    "USD/CHF",   # Долар США / Швейцарський франк
    "NZD/USD",   # Новозеландський долар / Долар США
    "EUR/GBP",   # Євро / Фунт
    "EUR/JPY",   # Євро / Йена
    "GBP/JPY",   # Фунт / Йена
]

DEFAULT_FOREX_SYMBOL: str = "EURUSD=X"
DEFAULT_FOREX_SYMBOL_TWELVE: str = "EUR/USD"

# Як часто оновлювати дані FOREX через Yahoo Finance (секунди).
FOREX_REFRESH_SECONDS: int = 60


@dataclass
class BotConfig:
    # --- Загальне (Yahoo Finance) ---
    symbol: str = DEFAULT_FOREX_SYMBOL       # Тикер: EURUSD=X, GBPUSD=X, USDJPY=X тощо
    interval: str = "1m"            # 1m, 5m, 15m, 1h, 1d
    period: str = "1d"              # 1d, 5d, 1mo

    # --- Індикатори ---
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    min_signal_strength: int = 40   # Мінімальна увереність (0-100) для виходу в угоду

    # --- Binance (крипта) ---
    binance_symbol: str = "btcusdt"  # btc, eth, sol і т.д.
    binance_interval: str = "1m"     # 1m, 5m, 15m, 1h

    # --- Twelve Data (FOREX реальний час) ---
    twelve_api_key: str = ""  # <-- встав свій безкоштовний API-ключ з twelve.com
    twelve_base_url: str = "https://api.twelvedata.com"
    twelve_refresh_seconds: int = 60
    twelve_outputsize: int = 30