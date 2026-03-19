"""Análisis de estado de mercado — Oliver Vélez: tendencia, medias, trampas."""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import datetime

from app.broker.models import Candle

log = logging.getLogger(__name__)

# Umbrales de configuración
SLOPE_THRESHOLD_PCT = 0.05  # 0.05% para clasificar pendiente como UP/DOWN
NARROW_PCT = 0.15  # |EMA20 - SMA200| / close * 100 < 0.15% = NARROW
WIDE_PCT = 0.75  # > 0.75% = WIDE
TRAP_ZONE_CROSSES = 4  # Cruces EMA20-SMA200 en 20 velas para zona trampa
SWING_LOOKBACK = 2  # Velas antes/después para detectar swing


@dataclass
class MarketState:
    """Estado completo del mercado para un instrumento en un timeframe."""

    instrument: str
    timeframe: str
    timestamp: datetime

    # Precio y medias
    price: float
    sma200: float
    ema20: float
    atr14: float

    # Clasificaciones
    trend_state: str  # "UP" | "DOWN" | "RANGE"
    price_vs_sma200: str  # "ABOVE" | "BELOW"
    sma200_slope: str  # "UP" | "DOWN" | "FLAT"
    ema20_slope: str  # "UP" | "DOWN" | "FLAT"

    # Relación entre medias
    ma_state: str  # "NARROW" | "NORMAL" | "WIDE"
    ema20_vs_sma200: str  # "ABOVE" | "BELOW"

    # Zona trampa
    trap_zone: bool

    # Swings
    last_swing_high: float
    last_swing_low: float
    impulse_range: float  # last_swing_high - last_swing_low

    def to_dict(self) -> dict:
        """Para almacenar en market_state_json de la DB."""
        return asdict(self)


class MarketStateAnalyzer:
    """Analiza el estado del mercado según los principios de Oliver Vélez."""

    def analyze(
        self,
        instrument: str,
        timeframe: str,
        candles: list[Candle],
        require_sma200: bool = True,
    ) -> MarketState | None:
        """Analiza el estado del mercado para un instrumento y timeframe.

        Args:
            require_sma200: Si True (default), requiere 200 velas para SMA200.
                Si False, solo necesita 30 velas — calcula EMA20 + ATR14 + swings
                y llena campos SMA200 con valores neutros. Útil para M5.
        """
        min_candles = 200 if require_sma200 else 30
        if len(candles) < min_candles:
            log.warning(
                "Insuficientes velas para %s %s: %d (necesita %d)",
                instrument, timeframe, len(candles), min_candles,
            )
            return None

        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]

        # Calcular indicadores
        ema20 = self._ema(closes, 20)
        atr14 = self._atr(candles, 14)

        current_price = closes[-1]
        current_time = candles[-1].timestamp

        if require_sma200:
            sma200 = self._sma(closes, 200)
            price_vs_sma200 = "ABOVE" if current_price > sma200 else "BELOW"
            sma200_slope = self._calculate_slope(closes, 200, lookback=10)
            ema20_vs_sma200 = "ABOVE" if ema20 > sma200 else "BELOW"
            ma_state = self._classify_ma_state(ema20, sma200, current_price)
            trend_state = self._classify_trend(
                price_vs_sma200, sma200_slope, highs, lows,
            )
            trap_zone = self._detect_trap_zone(closes, 20, 200)
        else:
            # Modo ligero (M5): sin SMA200, valores neutros
            sma200 = 0.0
            price_vs_sma200 = "N/A"
            sma200_slope = "N/A"
            ema20_vs_sma200 = "N/A"
            ma_state = "N/A"
            trend_state = "N/A"
            trap_zone = False

        # Pendiente EMA20 (aplica a ambos modos)
        ema20_slope = self._calculate_slope_ema(closes, 20, lookback=5)

        # Detección de swings
        swing_high, swing_low = self._detect_swings(highs, lows)

        impulse_range = swing_high - swing_low if swing_high > swing_low else 0.0

        return MarketState(
            instrument=instrument,
            timeframe=timeframe,
            timestamp=current_time,
            price=current_price,
            sma200=sma200,
            ema20=ema20,
            atr14=atr14,
            trend_state=trend_state,
            price_vs_sma200=price_vs_sma200,
            sma200_slope=sma200_slope,
            ema20_slope=ema20_slope,
            ma_state=ma_state,
            ema20_vs_sma200=ema20_vs_sma200,
            trap_zone=trap_zone,
            last_swing_high=swing_high,
            last_swing_low=swing_low,
            impulse_range=impulse_range,
        )

    # ── Indicadores técnicos ────────────────────────────────

    @staticmethod
    def _sma(values: list[float], period: int) -> float:
        """Simple Moving Average del último periodo."""
        if len(values) < period:
            return values[-1] if values else 0.0
        return sum(values[-period:]) / period

    @staticmethod
    def _ema(values: list[float], period: int) -> float:
        """Exponential Moving Average."""
        if len(values) < period:
            return values[-1] if values else 0.0

        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period  # SMA como seed

        for val in values[period:]:
            ema = (val - ema) * multiplier + ema

        return ema

    @staticmethod
    def _ema_series(values: list[float], period: int) -> list[float]:
        """Retorna la serie completa de EMA."""
        if len(values) < period:
            return values.copy()

        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        result = [ema]

        for val in values[period:]:
            ema = (val - ema) * multiplier + ema
            result.append(ema)

        return result

    @staticmethod
    def _atr(candles: list[Candle], period: int = 14) -> float:
        """Average True Range."""
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

    # ── Clasificaciones ─────────────────────────────────────

    def _calculate_slope(
        self, closes: list[float], ma_period: int, lookback: int = 10
    ) -> str:
        """Calcula pendiente de una SMA comparando valor actual vs N velas atrás."""
        if len(closes) < ma_period + lookback:
            return "FLAT"

        current_sma = self._sma(closes, ma_period)
        past_sma = self._sma(closes[:-lookback], ma_period)

        if past_sma == 0:
            return "FLAT"

        change_pct = ((current_sma - past_sma) / past_sma) * 100

        if change_pct > SLOPE_THRESHOLD_PCT:
            return "UP"
        elif change_pct < -SLOPE_THRESHOLD_PCT:
            return "DOWN"
        return "FLAT"

    def _calculate_slope_ema(
        self, closes: list[float], ma_period: int, lookback: int = 5
    ) -> str:
        """Calcula pendiente de una EMA."""
        if len(closes) < ma_period + lookback:
            return "FLAT"

        current_ema = self._ema(closes, ma_period)
        past_ema = self._ema(closes[:-lookback], ma_period)

        if past_ema == 0:
            return "FLAT"

        change_pct = ((current_ema - past_ema) / past_ema) * 100

        if change_pct > SLOPE_THRESHOLD_PCT:
            return "UP"
        elif change_pct < -SLOPE_THRESHOLD_PCT:
            return "DOWN"
        return "FLAT"

    @staticmethod
    def _classify_ma_state(ema20: float, sma200: float, price: float) -> str:
        """NARROW / NORMAL / WIDE basado en distancia EMA20 a SMA200."""
        if price == 0:
            return "NORMAL"

        distance_pct = abs(ema20 - sma200) / price * 100

        if distance_pct < NARROW_PCT:
            return "NARROW"
        elif distance_pct > WIDE_PCT:
            return "WIDE"
        return "NORMAL"

    def _detect_swings(
        self,
        highs: list[float],
        lows: list[float],
        lookback: int = SWING_LOOKBACK,
    ) -> tuple[float, float]:
        """Detecta último swing high y swing low.

        Un swing high es una vela cuyo high es mayor que las N velas antes y después.
        """
        last_swing_high = max(highs[-20:]) if highs else 0.0
        last_swing_low = min(lows[-20:]) if lows else 0.0

        # Buscar swings reales en las últimas 30 velas
        search_range = min(30, len(highs) - lookback)

        for i in range(len(highs) - 1 - lookback, len(highs) - 1 - search_range, -1):
            if i < lookback:
                break
            is_swing = True
            for j in range(1, lookback + 1):
                if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                    is_swing = False
                    break
            if is_swing:
                last_swing_high = highs[i]
                break

        for i in range(len(lows) - 1 - lookback, len(lows) - 1 - search_range, -1):
            if i < lookback:
                break
            is_swing = True
            for j in range(1, lookback + 1):
                if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                    is_swing = False
                    break
            if is_swing:
                last_swing_low = lows[i]
                break

        return last_swing_high, last_swing_low

    def _classify_trend(
        self,
        price_vs_sma200: str,
        sma200_slope: str,
        highs: list[float],
        lows: list[float],
    ) -> str:
        """Clasifica la tendencia: UP, DOWN o RANGE.

        UP requiere: precio > SMA200, SMA200 subiendo, swings crecientes.
        DOWN requiere: precio < SMA200, SMA200 bajando, swings decrecientes.
        """
        # Verificar swings crecientes/decrecientes en las últimas 20 velas
        recent_swing_highs = []
        recent_swing_lows = []
        lookback = SWING_LOOKBACK

        for i in range(max(lookback, len(highs) - 20), len(highs) - lookback):
            # Swing high
            is_sh = all(
                highs[i] > highs[i - j] and highs[i] > highs[i + j]
                for j in range(1, lookback + 1)
                if i - j >= 0 and i + j < len(highs)
            )
            if is_sh:
                recent_swing_highs.append(highs[i])

            # Swing low
            is_sl = all(
                lows[i] < lows[i - j] and lows[i] < lows[i + j]
                for j in range(1, lookback + 1)
                if i - j >= 0 and i + j < len(lows)
            )
            if is_sl:
                recent_swing_lows.append(lows[i])

        # Necesitamos al menos 2 swings para evaluar secuencia
        highs_rising = (
            len(recent_swing_highs) >= 2
            and all(
                recent_swing_highs[i] > recent_swing_highs[i - 1]
                for i in range(1, len(recent_swing_highs))
            )
        )
        lows_rising = (
            len(recent_swing_lows) >= 2
            and all(
                recent_swing_lows[i] > recent_swing_lows[i - 1]
                for i in range(1, len(recent_swing_lows))
            )
        )
        highs_falling = (
            len(recent_swing_highs) >= 2
            and all(
                recent_swing_highs[i] < recent_swing_highs[i - 1]
                for i in range(1, len(recent_swing_highs))
            )
        )
        lows_falling = (
            len(recent_swing_lows) >= 2
            and all(
                recent_swing_lows[i] < recent_swing_lows[i - 1]
                for i in range(1, len(recent_swing_lows))
            )
        )

        # UP: precio encima, SMA200 subiendo, swings crecientes
        if (
            price_vs_sma200 == "ABOVE"
            and sma200_slope in ("UP", "FLAT")
            and (highs_rising or lows_rising)
        ):
            return "UP"

        # DOWN: precio debajo, SMA200 bajando, swings decrecientes
        if (
            price_vs_sma200 == "BELOW"
            and sma200_slope in ("DOWN", "FLAT")
            and (highs_falling or lows_falling)
        ):
            return "DOWN"

        return "RANGE"

    def _detect_trap_zone(
        self,
        closes: list[float],
        ema_period: int = 20,
        sma_period: int = 200,
    ) -> bool:
        """Detecta zona trampa: SMA200 plana + muchos cruces EMA20-SMA200."""
        if len(closes) < sma_period + 20:
            return False

        # Verificar que SMA200 esté plana
        current_sma = self._sma(closes, sma_period)
        past_sma = self._sma(closes[:-20], sma_period)

        if past_sma == 0:
            return False

        sma_change_pct = abs((current_sma - past_sma) / past_sma) * 100
        if sma_change_pct > SLOPE_THRESHOLD_PCT:
            return False  # SMA200 tiene pendiente → no es trampa

        # Contar cruces EMA20-SMA200 en las últimas 20 velas
        ema_series = self._ema_series(closes, ema_period)
        if len(ema_series) < 20:
            return False

        crosses = 0
        # Necesitamos calcular SMA200 para cada punto (simplificado)
        for i in range(-20, -1):
            idx = len(closes) + i
            if idx < sma_period:
                continue
            sma_at_i = sum(closes[idx - sma_period + 1 : idx + 1]) / sma_period
            ema_at_i = ema_series[min(len(ema_series) - 1, len(ema_series) + i)]
            sma_at_next = sum(closes[idx - sma_period + 2 : idx + 2]) / sma_period
            ema_idx_next = min(len(ema_series) - 1, len(ema_series) + i + 1)
            ema_at_next = ema_series[ema_idx_next]

            # Cruce si el signo de (EMA - SMA) cambia
            if (ema_at_i - sma_at_i) * (ema_at_next - sma_at_next) < 0:
                crosses += 1

        return crosses >= TRAP_ZONE_CROSSES
