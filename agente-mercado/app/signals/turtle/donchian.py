"""Donchian Channel — highest high / lowest low de N períodos.

El canal Donchian es la base del sistema Turtle Trading.
Upper = max(high, N)  → señal de breakout alcista
Lower = min(low, N)   → señal de breakout bajista
"""

from __future__ import annotations

from dataclasses import dataclass

from app.broker.models import Candle


@dataclass
class DonchianChannel:
    """Valores del canal Donchian."""

    upper: float  # Highest high de N períodos
    lower: float  # Lowest low de N períodos
    middle: float  # (upper + lower) / 2
    period: int


def calculate_donchian(candles: list[Candle], period: int) -> DonchianChannel | None:
    """Calcula el canal Donchian de N períodos.

    Usa las últimas N velas (excluyendo la actual) para definir el canal.
    La vela actual se compara contra este canal para detectar breakout.
    """
    if len(candles) < period + 1:
        return None

    # Últimas N velas ANTES de la actual
    lookback = candles[-(period + 1):-1]
    upper = max(c.high for c in lookback)
    lower = min(c.low for c in lookback)

    return DonchianChannel(
        upper=upper,
        lower=lower,
        middle=(upper + lower) / 2,
        period=period,
    )


def calculate_atr(candles: list[Candle], period: int = 20) -> float:
    """ATR(N) para position sizing y stop loss del Turtle system."""
    if len(candles) < period + 1:
        return 0.0

    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i].high
        low = candles[i].low
        prev_close = candles[i - 1].close
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0

    return sum(true_ranges[-period:]) / period
