"""
Реальний час: крипта через Binance WebSocket або FOREX через Yahoo Finance / Twelve Data.
Запуск: python bot_realtime.py
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime

import pandas as pd
import requests
import websockets

from config import (
    BotConfig,
    FOREX_SYMBOLS,
    FOREX_SYMBOLS_TWELVE,
    DEFAULT_FOREX_SYMBOL,
    DEFAULT_FOREX_SYMBOL_TWELVE,
    FOREX_REFRESH_SECONDS,
)
from market_analyzer import MarketAnalyzer
from strategy import BinaryStrategy, TradeSignal, Signal


def print_signal(signal: TradeSignal, source: str = "") -> None:
    print("\n" + "=" * 50)
    print(f"Джерело   : {source}")
    print(f"Час       : {datetime.now().strftime('%H:%M:%S')}")
    print(f"Інструмент: {signal.symbol}")
    print(f"Ціна      : {signal.price:.5f}")
    print(f"СИГНАЛ    : {signal.signal.value}")
    print(f"Увереність: {signal.strength}/100")
    print("-" * 50)
    print("Причини:")
    for part in signal.reason.split("; "):
        print(f"  • {part}")
    print("=" * 50)


class RealtimeBot:
    def __init__(self, config: BotConfig | None = None, mode: str = "forex_yahoo"):
        self.config = config or BotConfig()
        self.mode = mode  # "forex_yahoo", "forex_twelve", "crypto"
        self.strategy = BinaryStrategy(config)

    # ---------- FOREX через Yahoo Finance (polling, є затримка) ----------
    def _run_forex_yahoo(self) -> None:
        symbol = self.config.symbol
        interval = self.config.interval
        analyzer = MarketAnalyzer(self.config)

        print(f"Режим FOREX (Yahoo Finance): {symbol} / інтервал {interval}")
        print(f"Оновлення кожні {FOREX_REFRESH_SECONDS} сек. (є затримка до 15 хв)")
        print("Натисніть Ctrl+C для зупинки.\n")

        try:
            while True:
                try:
                    last, _ = analyzer.analyze()
                    signal = self.strategy.generate(last, symbol)
                    print_signal(signal, source="Yahoo Finance (FOREX)")
                except Exception as exc:
                    print(f"❌ Помилка оновлення даних: {exc}")

                print(f"\nНаступне оновлення через {FOREX_REFRESH_SECONDS} сек... (Ctrl+C для зупинки)")
                time.sleep(FOREX_REFRESH_SECONDS)
        except KeyboardInterrupt:
            print("\nБота зупинено користувачем.")

    # ---------- FOREX через Twelve Data (реальний час, REST polling) ----------
    def _run_forex_twelve(self) -> None:
        symbol = self.config.symbol
        interval = self.config.interval
        analyzer = MarketAnalyzer(self.config)

        if not self.config.twelve_api_key:
            print("❌ Не вказано TWELVE_DATA_API_KEY у config.py")
            print("Отримай безкоштовний ключ на https://twelvedata.com і встав у config.py")
            return

        print(f"Режим FOREX (Twelve Data): {symbol} / інтервал {interval}")
        print(f"Оновлення кожні {self.config.twelve_refresh_seconds} сек. (реальний час FOREX)")
        print("Натисніть Ctrl+C для зупинки.\n")

        try:
            while True:
                try:
                    last, _ = analyzer.analyze_twelve(symbol=symbol, interval=interval)
                    signal = self.strategy.generate(last, symbol)
                    print_signal(signal, source="Twelve Data (FOREX real-time)")
                except Exception as exc:
                    print(f"❌ Помилка оновлення даних: {exc}")

                print(f"\nНаступне оновлення через {self.config.twelve_refresh_seconds} сек... (Ctrl+C для зупинки)")
                time.sleep(self.config.twelve_refresh_seconds)
        except KeyboardInterrupt:
            print("\nБота зупинено користувачем.")

    # ---------- Крипта через Binance WebSocket ----------
    async def _run_crypto(self) -> None:
        symbol = self.config.binance_symbol
        interval = self.config.binance_interval
        closes: list[float] = []

        ws_url = (
            f"wss://stream.binance.com:9443/ws/"
            f"{symbol}@kline_{interval}"
        )

        print(f"Підключення до Binance ({symbol.upper()}/USDT)...")
        async with websockets.connect(ws_url) as ws:
            print("✓ Підключено. Очікуємо закриття свіч...\n")
            async for message in ws:
                data = json.loads(message)
                kline = data["k"]
                is_closed = kline["x"]
                close_price = float(kline["c"])

                if is_closed:
                    closes.append(close_price)
                    if len(closes) > 100:
                        closes.pop(0)

                    signal = self._compute_signal(closes)

                    print("\n" + "=" * 50)
                    print(f"Час: {pd.Timestamp.now().strftime('%H:%M:%S')}")
                    print(f"Символ: {symbol.upper()}/USDT")
                    print(f"Ціна: {close_price:.2f}")
                    if signal:
                        print(f"СИГНАЛ: {signal.signal.value}")
                        print(f"Увереність: {signal.strength}/100")
                        print(f"Причини: {signal.reason}")
                    else:
                        print("СИГНАЛ: Збирання даних...")
                    print("=" * 50)

    def _compute_signal(self, prices: list[float]):
        if len(prices) < 30:
            return None

        df = pd.DataFrame({"close": prices})

        ema_fast = df["close"].ewm(span=9, adjust=False).mean().iloc[-1]
        ema_slow = df["close"].ewm(span=21, adjust=False).mean().iloc[-1]

        delta = df["close"].diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        macd = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(
            span=26, adjust=False
        ).mean()
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_hist = float((macd - macd_signal).iloc[-1])

        close = float(prices[-1])
        rolling_mean = df["close"].rolling(window=20).mean().iloc[-1]
        rolling_std = df["close"].rolling(window=20).std().iloc[-1]
        lower = rolling_mean - 2 * rolling_std
        upper = rolling_mean + 2 * rolling_std

        last = {
            "close": close,
            "rsi": float(rsi),
            "ema_fast": float(ema_fast),
            "ema_slow": float(ema_slow),
            "macd_hist": macd_hist,
            "BBL_20_2.0": float(lower),
            "BBU_20_2.0": float(upper),
        }

        import pandas as _pd

        return self.strategy.generate(_pd.Series(last), self.config.binance_symbol.upper())

    def run(self) -> None:
        if self.mode == "crypto":
            asyncio.run(self._run_crypto())
        elif self.mode == "forex_twelve":
            self._run_forex_twelve()
        else:
            self._run_forex_yahoo()


def choose_mode() -> str:
    print("\nОберіть джерело даних:")
    print("  1. FOREX через Yahoo Finance (є затримка до 15 хв)")
    print("  2. FOREX через Twelve Data (реальний час, потребує API-ключ)")
    print("  3. Криптовалюта через Binance WebSocket")

    choice = input("\nВаш вибір [1-3] [1]: ").strip()
    if choice == "2":
        return "forex_twelve"
    if choice == "3":
        return "crypto"
    return "forex_yahoo"


def choose_symbol(symbols: list[str], default: str, label: str) -> str:
    print(f"\n{label}:")
    for i, sym in enumerate(symbols, start=1):
        print(f"  {i:2d}. {sym}")
    print("  0. Власний тикер")

    choice = input(f"\nВибір [1-{len(symbols)}, 0] [1]: ").strip()
    if choice == "0":
        custom = input("Тикер: ").strip().upper()
        return custom or default

    if not choice or choice == "1":
        return default

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(symbols):
            return symbols[idx]
    except ValueError:
        pass

    print("Некоректний вибір, буде використано значення за замовчуванням")
    return default


def choose_interval() -> str:
    print("\nІнтервал свічки:")
    print("  1. 1 м хвилина   2. 5 хвилин   3. 15 хвилин   4. 1 година")

    choice = input("\nВибір [1-4] [1]: ").strip()
    mapping = {"1": "1m", "2": "5m", "3": "15m", "4": "1h", "": "1m"}
    return mapping.get(choice, "1m")


def main() -> None:
    print("=== РЕАЛЬНИЙ ЧАС: БІНАРНІ ОПЦІЇ ===\n")

    mode = choose_mode()
    config = BotConfig()

    if mode == "forex_yahoo":
        config.symbol = choose_symbol(
            FOREX_SYMBOLS, DEFAULT_FOREX_SYMBOL, "Доступні валютні пари FOREX (Yahoo)"
        )
        config.interval = choose_interval()
    elif mode == "forex_twelve":
        config.symbol = choose_symbol(
            FOREX_SYMBOLS_TWELVE,
            DEFAULT_FOREX_SYMBOL_TWELVE,
            "Доступні валютні пари FOREX (Twelve Data)",
        )
        config.interval = choose_interval()

        if not config.twelve_api_key:
            key = input("\nВведіть безкоштовний API-ключ Twelve Data: ").strip()
            if key:
                config.twelve_api_key = key
            else:
                print("⚠️  Без API-ключа Twelve Data не спрацює. Використайте режим 1 (Yahoo).")
                return
    else:
        print("\nКриптовалюти (Binance): BTCUSDT, ETHUSDT, SOLUSDT тощо.")
        custom = input(f"Символ [{config.binance_symbol.upper()}]: ").strip().lower()
        if custom:
            config.binance_symbol = custom
        config.binance_interval = choose_interval()

    bot = RealtimeBot(config=config, mode=mode)
    bot.run()


if __name__ == "__main__":
    main()