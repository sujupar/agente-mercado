"""Indicadores para el sistema Connors RSI(2).

RSI(2): RSI ultra-corto que detecta condiciones extremas de oversold/overbought.
SMA(5): Media móvil de 5 períodos como señal de salida.
SMA(200): Filtro de tendencia.
"""

from __future__ import annotations


def rsi(closes: list[float], period: int = 2) -> float:
    """Calcula RSI con período ultra-corto (default 2).

    RSI(2) oscila rápidamente entre 0-100.
    < 10 = extremadamente oversold → señal de compra
    > 90 = extremadamente overbought → señal de venta
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


def sma(values: list[float], period: int) -> float:
    """Simple Moving Average."""
    if len(values) < period:
        return values[-1] if values else 0.0
    return sum(values[-period:]) / period


def atr(candles, period: int = 14) -> float:
    """ATR para stop loss."""
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
