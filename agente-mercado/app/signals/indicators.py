"""Indicadores técnicos compartidos — usados por todas las estrategias.

Funciones puras (sin estado, sin efectos secundarios). Reciben listas de
precios o velas y retornan valores numéricos. Diseñadas para ser rápidas
y reutilizables tanto en producción como en backtesting.
"""

from __future__ import annotations

import math

from app.broker.models import Candle


# ── Medias Móviles ─────────────────────────────────────────

def sma(values: list[float], period: int) -> float:
    """Media Móvil Simple del último período."""
    if len(values) < period:
        return values[-1] if values else 0.0
    return sum(values[-period:]) / period


def ema(values: list[float], period: int) -> float:
    """Media Móvil Exponencial (valor actual)."""
    if len(values) < period:
        return values[-1] if values else 0.0

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period  # SMA como seed

    for val in values[period:]:
        result = (val - result) * multiplier + result

    return result


def ema_series(values: list[float], period: int) -> list[float]:
    """Serie completa de EMA (para detectar cruces)."""
    if len(values) < period:
        return values.copy()

    multiplier = 2 / (period + 1)
    result_val = sum(values[:period]) / period
    result = [result_val]

    for val in values[period:]:
        result_val = (val - result_val) * multiplier + result_val
        result.append(result_val)

    return result


# ── Volatilidad ────────────────────────────────────────────

def atr(candles: list[Candle], period: int = 14) -> float:
    """Average True Range — mide la volatilidad promedio."""
    if len(candles) < 2:
        return 0.0

    true_ranges = []
    for i in range(1, len(candles)):
        prev_close = candles[i - 1].close
        high = candles[i].high
        low = candles[i].low
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0

    return sum(true_ranges[-period:]) / period


def stddev(values: list[float], period: int) -> float:
    """Desviación estándar del último período."""
    if len(values) < period:
        return 0.0

    subset = values[-period:]
    mean = sum(subset) / period
    variance = sum((x - mean) ** 2 for x in subset) / period
    return math.sqrt(variance)


# ── Bandas de Bollinger ────────────────────────────────────

def bollinger_bands(
    values: list[float],
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[float, float, float]:
    """Bandas de Bollinger: (upper, middle, lower).

    - upper = SMA + num_std × StdDev
    - middle = SMA
    - lower = SMA - num_std × StdDev
    """
    if len(values) < period:
        v = values[-1] if values else 0.0
        return (v, v, v)

    middle = sma(values, period)
    sd = stddev(values, period)

    upper = middle + num_std * sd
    lower = middle - num_std * sd

    return (upper, middle, lower)


# ── RSI ────────────────────────────────────────────────────

def rsi(closes: list[float], period: int = 14) -> float:
    """Relative Strength Index.

    RSI(2) con period=2 es ultra-rápido (sistema Connors).
    RSI(14) es el estándar.
    """
    if len(closes) < period + 1:
        return 50.0  # Neutral

    gains = []
    losses = []
    for i in range(len(closes) - period, len(closes)):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0

    if avg_loss == 0:
        return 100.0
    if avg_gain == 0:
        return 0.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
