"""Registry de estrategias — Oliver Vélez (S1/S2) + SMC El Sensei (S3).

S1/S2: Pullback a EMA20 según el Plan de Trading de Oliver Vélez.
S3: Smart Money Concepts (Order Blocks, BOS/ChoCH, Liquidity Sweeps).
Las señales se generan por reglas técnicas, NO por LLM.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.strategies.prompts import (
    IMPROVEMENT_ANALYSIS_PROMPT,
    LEARNING_REPORT_PROMPT,
    LESSON_BATCH_PROMPT,
)


@dataclass(frozen=True)
class StrategyConfig:
    """Configuración inmutable de una estrategia Forex."""

    id: str
    name: str
    description: str

    # Dirección y tipo
    signal_type: str  # "pullback_ema20_long" | "pullback_ema20_short" | "smc_institutional"
    direction: str  # "LONG" | "SHORT" | "BOTH"

    # Instrumentos que opera
    instruments: tuple[str, ...] = ("EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD")

    # Timeframes
    primary_timeframe: str = "H1"
    context_timeframe: str = "H4"
    entry_timeframe: str = "M1"  # Timeframe para buscar entradas (Oliver Vélez — M1 lo más cercano a M2)

    # Umbrales de entrada para pullback detector (M1/M5)
    entry_min_retrace_pct: float = 0.20  # 20% retrace (más bajo que H1)
    entry_ema20_zone_atr_mult: float = 0.50  # 0.50 ATR zone (más ancho que H1)

    # Risk
    risk_per_trade_pct: float = 0.01  # 1% del balance
    min_risk_reward: float = 2.0  # R:R mínimo 1:2
    max_concurrent_positions: int = 3
    max_trades_per_day: int = 0  # 0 = sin límite, >0 = máximo trades por día

    # Timing
    cycle_interval_minutes: int = 15  # Alineado a velas H1

    # Estado
    enabled: bool = True

    # Capital inicial (se sincroniza con broker al arrancar)
    initial_capital_usd: float = 5_500.0  # Sincroniza con balance real del broker

    # Learning
    trades_per_learning_report: int = 15
    trades_per_improvement_cycle: int = 20

    # LLM (solo post-trade)
    llm_budget_fraction: float = 0.50
    learning_report_prompt: str = LEARNING_REPORT_PROMPT
    lesson_batch_prompt: str = LESSON_BATCH_PROMPT
    improvement_prompt: str = IMPROVEMENT_ANALYSIS_PROMPT


STRATEGIES: dict[str, StrategyConfig] = {
    "s1_pullback_20_up": StrategyConfig(
        id="s1_pullback_20_up",
        name="S1 — Pullback EMA20 Alcista",
        description=(
            "Longs en pullback a EMA20 en tendencia alcista confirmada. "
            "Requiere 8 filtros de contexto (precio > SMA200, SMA200 UP, "
            "EMA20 > SMA200, no trap zone, etc). Patrones: BULL_ENGULFING, "
            "PIN_BAR_ALCISTA, GREEN_OVERPOWERS_RED. R:R mínimo 1:2."
        ),
        signal_type="pullback_ema20_long",
        direction="LONG",
    ),
    "s2_pullback_20_down": StrategyConfig(
        id="s2_pullback_20_down",
        name="S2 — Pullback EMA20 Bajista",
        description=(
            "Shorts en pullback a EMA20 en tendencia bajista confirmada. "
            "Requiere 8 filtros de contexto (precio < SMA200, SMA200 DOWN, "
            "EMA20 < SMA200, no trap zone, etc). Patrones: BEAR_ENGULFING, "
            "PIN_BAR_BAJISTA, RED_OVERPOWERS_GREEN. R:R mínimo 1:2."
        ),
        signal_type="pullback_ema20_short",
        direction="SHORT",
    ),
    "s3_ema_crossover": StrategyConfig(
        id="s3_ema_crossover",
        name="S3 — Cruce EMA 9/21",
        description=(
            "Cruce EMA9/EMA21 en M5. Alto volumen (15-25 trades/día). "
            "Diseñada para aprendizaje rápido del motor de mejora. "
            "Errores aprendibles: time_filter, candle_quality, sma200_distance."
        ),
        signal_type="ema_crossover",
        direction="BOTH",
        instruments=("EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD"),
        primary_timeframe="M5",
        entry_timeframe="M5",
        min_risk_reward=1.33,  # TP=2.0×ATR / SL=1.5×ATR = 1.33
        max_concurrent_positions=3,
        trades_per_improvement_cycle=20,
    ),
    "s4_bollinger_reversion": StrategyConfig(
        id="s4_bollinger_reversion",
        name="S4 — Bollinger Reversión",
        description=(
            "Reversión a la media con Bandas de Bollinger(20,2) en M5. "
            "Lógica opuesta a S1/S2: compra en banda inferior, vende en superior. "
            "10-20 trades/día. TP = banda media (SMA20)."
        ),
        signal_type="bollinger_reversion",
        direction="BOTH",
        instruments=("EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD"),
        primary_timeframe="M5",
        entry_timeframe="M5",
        min_risk_reward=1.0,
        max_concurrent_positions=3,
        trades_per_improvement_cycle=20,
    ),
    "s5_session_breakout": StrategyConfig(
        id="s5_session_breakout",
        name="S5 — Ruptura Sesión",
        description=(
            "Ruptura del rango de apertura de sesión (Londres/NY) en M5. "
            "Rango = primeros 30 min. Entrada al romper. SL = lado opuesto. "
            "TP = 1.5× rango. 4-6 trades/día."
        ),
        signal_type="session_breakout",
        direction="BOTH",
        instruments=("EUR_USD", "GBP_USD", "USD_JPY"),
        primary_timeframe="M5",
        entry_timeframe="M5",
        min_risk_reward=1.5,
        max_concurrent_positions=2,
        trades_per_improvement_cycle=20,
    ),
    # ── Estrategias nuevas (S6-S10) — $100 capital cada una ──
    "s6_pullback_20_up_m5": StrategyConfig(
        id="s6_pullback_20_up_m5",
        name="S6 — Pullback EMA20 Alcista M5",
        description="S1 en M5: pullback a EMA20 en uptrend, mayor frecuencia. 8-15 trades/día.",
        signal_type="pullback_ema20_m5",
        direction="LONG",
        instruments=("EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD"),
        primary_timeframe="M5",
        entry_timeframe="M5",
        initial_capital_usd=100.0,
        risk_per_trade_pct=0.01,
        min_risk_reward=2.0,
        max_concurrent_positions=3,
        trades_per_improvement_cycle=20,
    ),
    "s7_pullback_20_down_m5": StrategyConfig(
        id="s7_pullback_20_down_m5",
        name="S7 — Pullback EMA20 Bajista M5",
        description="S2 en M5: pullback a EMA20 en downtrend, mayor frecuencia. 8-15 trades/día.",
        signal_type="pullback_ema20_m5",
        direction="SHORT",
        instruments=("EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD"),
        primary_timeframe="M5",
        entry_timeframe="M5",
        initial_capital_usd=100.0,
        risk_per_trade_pct=0.01,
        min_risk_reward=2.0,
        max_concurrent_positions=3,
        trades_per_improvement_cycle=20,
    ),
    "s8_double_ema_pullback": StrategyConfig(
        id="s8_double_ema_pullback",
        name="S8 — Double EMA Pullback",
        description="EMA20+EMA50 alineadas, entrada en toque de EMA20. Confluencia de medias. 5-10 trades/día.",
        signal_type="double_ema_pullback",
        direction="BOTH",
        instruments=("EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD"),
        primary_timeframe="M5",
        entry_timeframe="M5",
        initial_capital_usd=100.0,
        risk_per_trade_pct=0.01,
        min_risk_reward=1.5,
        max_concurrent_positions=3,
        trades_per_improvement_cycle=20,
    ),
    "s9_rsi_ema20": StrategyConfig(
        id="s9_rsi_ema20",
        name="S9 — RSI + EMA20",
        description="RSI(14) en zona de interés + precio cerca de EMA20. Confluencia oscilador + media. 5-10 trades/día.",
        signal_type="rsi_ema20",
        direction="BOTH",
        instruments=("EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD"),
        primary_timeframe="M5",
        entry_timeframe="M5",
        initial_capital_usd=100.0,
        risk_per_trade_pct=0.01,
        min_risk_reward=1.33,
        max_concurrent_positions=3,
        trades_per_improvement_cycle=20,
    ),
    "s10_momentum_breakout": StrategyConfig(
        id="s10_momentum_breakout",
        name="S10 — Momentum Breakout",
        description="Ruptura de máximo/mínimo 20 períodos con EMA20 confirmando. Vela fuerte (>40% cuerpo). 5-10 trades/día.",
        signal_type="momentum_breakout",
        direction="BOTH",
        instruments=("EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD"),
        primary_timeframe="M5",
        entry_timeframe="M5",
        initial_capital_usd=100.0,
        risk_per_trade_pct=0.01,
        min_risk_reward=1.5,
        max_concurrent_positions=3,
        trades_per_improvement_cycle=20,
    ),
}


# Estrategias habilitadas para operar en LIVE (cuenta real).
# Las estrategias NO listadas aquí siguen operando en DEMO pero nunca ejecutan
# trades con dinero real — sirven como laboratorio y motor de aprendizaje.
#
# Criterio para incluir: win rate estable ≥40% tras ≥100 trades en DEMO.
# Por ahora solo S1 Pullback EMA20 está validada para LIVE con $100.
STRATEGIES_ENABLED_IN_LIVE: frozenset[str] = frozenset({
    "s1_pullback_20_up",
})
