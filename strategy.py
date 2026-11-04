"""
Торгова стратегія: тренс + RSI + MACD + Боллінґери.
Кожен фактор дає до 25 балів. Якщо сума >= min_signal_strength — сигнал виходить.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from config import BotConfig


class Signal(str, Enum):
    CALL = "CALL (вгору / покупка)"
    PUT = "PUT (вниз / продаж)"
    NONE = "НІ (чекати — сигнал слабкий)"


@dataclass
class TradeSignal:
    signal: Signal
    strength: int          # 0-100
    price: float
    reason: str
    symbol: str


class BinaryStrategy:
    def __init__(self, config: BotConfig | None = None):
        self.config = config or BotConfig()

    def generate(self, last: pd.Series, symbol: str) -> TradeSignal:
        close = float(last["close"])
        rsi = float(last["rsi"])
        ema_fast = float(last["ema_fast"])
        ema_slow = float(last["ema_slow"])
        macd_hist = float(last["macd_hist"])
        lower = float(last["BBL_20_2.0"])
        upper = float(last["BBU_20_2.0"])

        score_call = 0
        score_put = 0
        reasons: list[str] = []

        # 1. Тренс (EMA)
        if ema_fast > ema_slow:
            score_call += 25
            reasons.append("Тренс вгору (EMA9 > EMA21)")
        else:
            score_put += 25
            reasons.append("Тренс вниз (EMA9 < EMA21)")

        # 2. RSI
        if rsi < self.config.rsi_oversold:
            score_call += 25
            reasons.append(f"RSI перепроданий ({rsi:.1f}) — можливий зріст")
        elif rsi > self.config.rsi_overbought:
            score_put += 25
            reasons.append(f"RSI перекуплений ({rsi:.1f}) — можливий спад")

        # 3. MACD гістограма
        if macd_hist > 0:
            score_call += 25
            reasons.append("MACD гістограма позитивна")
        else:
            score_put += 25
            reasons.append("MACD гістограма негативна")

        # 4. Боллінґери (повернення до середнього)
        if close <= lower:
            score_call += 25
            reasons.append("Ціна внизу ланцюга Боллінґера")
        elif close >= upper:
            score_put += 25
            reasons.append("Ціна вгорі ланцюга Боллінґера")

        total = max(score_call, score_put)

        if total >= self.config.min_signal_strength:
            signal = Signal.CALL if score_call > score_put else Signal.PUT
        else:
            signal = Signal.NONE

        return TradeSignal(
            signal=signal,
            strength=total,
            price=close,
            reason="; ".join(reasons),
            symbol=symbol,
        )
