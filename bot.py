"""
CLI-бот для аналізу валютного ринку (FOREX) через Yahoo Finance.
Запуск: python bot.py
"""

from __future__ import annotations

from market_analyzer import MarketAnalyzer
from strategy import BinaryStrategy, TradeSignal, Signal
from config import BotConfig, FOREX_SYMBOLS, DEFAULT_FOREX_SYMBOL


def print_signal(signal: TradeSignal) -> None:
    print("\n" + "=" * 50)
    print(f"Інструмент : {signal.symbol}")
    print(f"Ціна       : {signal.price:.5f}")
    print(f"СИГНАЛ     : {signal.signal.value}")
    print(f"Увереність : {signal.strength}/100")
    print("-" * 50)
    print("Причини:")
    for part in signal.reason.split("; "):
        print(f"  • {part}")
    print("=" * 50)


def choose_symbol() -> str:
    print("\nОберіть валютну пару FOREX:")
    for i, sym in enumerate(FOREX_SYMBOLS, start=1):
        print(f"  {i:2d}. {sym}")
    print(f"  0. Вказати свій тикер вручну")

    choice = input(f"\nВаш вибір [1-{len(FOREX_SYMBOLS)}, або 0] [1]: ").strip()
    if not choice or choice == "1":
        return DEFAULT_FOREX_SYMBOL

    if choice == "0":
        custom = input("Введіть тикер (наприклад EURUSD=X): ").strip().upper()
        return custom or DEFAULT_FOREX_SYMBOL

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(FOREX_SYMBOLS):
            return FOREX_SYMBOLS[idx]
    except ValueError:
        pass

    print("Некоректний вибір, буде використано EURUSD=X")
    return DEFAULT_FOREX_SYMBOL


def choose_interval() -> str:
    print("\nОберіть інтервал свічки:")
    print("  1. 1 м хвилина")
    print("  2. 5 хвилин")
    print("  3. 15 хвилин")
    print("  4. 1 година")

    choice = input("\nВаш вибір [1-4] [1]: ").strip()
    mapping = {"1": "1m", "2": "5m", "3": "15m", "4": "1h", "": "1m"}
    return mapping.get(choice, "1m")


def main() -> None:
    print("=== ЛОКАЛЬНИЙ АНАЛІТИК БІНАРНИХ ОПЦІЙ (FOREX) ===\n")

    symbol = choose_symbol()
    interval = choose_interval()

    config = BotConfig(symbol=symbol, interval=interval)
    analyzer = MarketAnalyzer(config)
    strategy = BinaryStrategy(config)

    try:
        last, _ = analyzer.analyze()
        signal = strategy.generate(last, symbol)
        print_signal(signal)

        if signal.signal == Signal.NONE:
            print("\nℹ️  Сигнал слабкий — краще почекати на підтвердження.")
        else:
            print("\n✅ Сигнал готовий до перевірки на демо-рахунку!")

        print("\n⚠️  Це не фінансова порада. Спочатку тестуй на демо-рахунку!")
    except Exception as exc:
        print(f"\n❌ Помилка аналізу: {exc}")


if __name__ == "__main__":
    main()