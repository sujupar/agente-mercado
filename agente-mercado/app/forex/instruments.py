"""Utilidades de instrumentos Forex — pip sizes, position sizing, spreads."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Configuración por instrumento
# pip_size: tamaño de 1 pip en precio
# pip_value_per_unit: valor en USD de 1 pip por 1 unidad del instrumento
# max_spread_pips: spread máximo aceptable para operar
INSTRUMENT_CONFIG = {
    "EUR_USD": {
        "pip_size": 0.0001,
        "pip_value_per_unit": 0.0001,  # 1 pip = $0.0001 por unidad
        "max_spread_pips": 2.0,
        "display": "EURUSD",
        "min_units": 1,
    },
    "GBP_USD": {
        "pip_size": 0.0001,
        "pip_value_per_unit": 0.0001,
        "max_spread_pips": 2.5,
        "display": "GBPUSD",
        "min_units": 1,
    },
    "USD_JPY": {
        "pip_size": 0.01,
        "pip_value_per_unit": 0.01,  # Requiere conversión a USD
        "max_spread_pips": 2.0,
        "display": "USDJPY",
        "min_units": 1,
    },
    "XAU_USD": {
        "pip_size": 0.01,
        "pip_value_per_unit": 0.01,  # 1 pip = $0.01 por unidad (1 oz)
        "max_spread_pips": 30.0,  # Oro tiene spreads más amplios
        "display": "XAUUSD",
        "min_units": 1,
    },
    "BTC_USD": {
        "pip_size": 1.0,
        "pip_value_per_unit": 1.0,
        "max_spread_pips": 50.0,
        "display": "BTCUSD",
        "min_units": 0.001,
    },
}


def _normalize_instrument(instrument: str) -> str:
    """Normaliza 'EURUSD' o 'EUR_USD' al formato OANDA 'EUR_USD'."""
    if "_" in instrument:
        return instrument
    # Intentar separar en posición 3 (la mayoría de pares forex)
    for oanda_name, config in INSTRUMENT_CONFIG.items():
        if config["display"] == instrument:
            return oanda_name
    # Fallback: insertar _ en posición 3
    if len(instrument) == 6:
        return f"{instrument[:3]}_{instrument[3:]}"
    return instrument


def get_pip_size(instrument: str) -> float:
    """Tamaño de 1 pip para un instrumento."""
    key = _normalize_instrument(instrument)
    config = INSTRUMENT_CONFIG.get(key)
    if not config:
        log.warning("Instrumento desconocido: %s — usando pip_size=0.0001", instrument)
        return 0.0001
    return config["pip_size"]


def get_pip_value(instrument: str, current_price: float = 0.0) -> float:
    """Valor en USD de 1 pip por 1 unidad del instrumento.

    Para pares XXX/USD (EURUSD, GBPUSD): pip_value = pip_size
    Para pares USD/XXX (USDJPY): pip_value = pip_size / current_price
    Para XAUUSD: pip_value = pip_size (directo)
    """
    key = _normalize_instrument(instrument)
    config = INSTRUMENT_CONFIG.get(key)
    if not config:
        return 0.0001

    # Para USD/JPY necesitamos convertir
    if key == "USD_JPY" and current_price > 0:
        return config["pip_value_per_unit"] / current_price

    return config["pip_value_per_unit"]


def price_to_pips(instrument: str, price_distance: float) -> float:
    """Convierte una distancia en precio a pips."""
    pip_size = get_pip_size(instrument)
    if pip_size == 0:
        return 0.0
    return abs(price_distance) / pip_size


def pips_to_price(instrument: str, pips: float) -> float:
    """Convierte pips a distancia en precio."""
    return pips * get_pip_size(instrument)


def calculate_position_size(
    instrument: str,
    account_balance: float,
    risk_pct: float,
    stop_distance_price: float,
    current_price: float = 0.0,
    max_risk_multiplier: float = 1.5,
) -> float:
    """Calcula el tamaño de posición en unidades del instrumento.

    Fórmula:
        risk_amount = account_balance × risk_pct
        stop_pips = stop_distance_price / pip_size
        pip_value = valor de 1 pip por unidad
        units = risk_amount / (stop_pips × pip_value)

    Args:
        instrument: Par de trading (ej. "EUR_USD")
        account_balance: Balance de la cuenta en USD
        risk_pct: Porcentaje de riesgo (ej. 0.01 = 1%)
        stop_distance_price: Distancia del stop en precio
        current_price: Precio actual (necesario para USD/JPY)
        max_risk_multiplier: Multiplicador máximo aceptable si el min_units
            del broker fuerza a exceder el riesgo objetivo (default 1.5 = 50%
            más de riesgo permitido). Para capital pequeño (ej. $100) es común
            que el min_units viole el 1% — este cap evita que el sistema
            abra trades con riesgo desproporcionado.

    Returns:
        Tamaño de posición en unidades del instrumento, o 0 si no es viable.
    """
    if stop_distance_price <= 0 or account_balance <= 0 or risk_pct <= 0:
        return 0.0

    risk_amount = account_balance * risk_pct
    pip_size = get_pip_size(instrument)
    pip_value = get_pip_value(instrument, current_price)

    if pip_size == 0 or pip_value == 0:
        return 0.0

    stop_pips = stop_distance_price / pip_size
    units = risk_amount / (stop_pips * pip_value)

    # Redondear según el instrumento
    key = _normalize_instrument(instrument)
    config = INSTRUMENT_CONFIG.get(key, {})
    min_units = config.get("min_units", 1)

    # Redondear a enteros para Forex, a decimales para crypto
    if min_units >= 1:
        units = int(units)
    else:
        units = round(units, 3)

    if units <= 0:
        return 0.0

    # Sizing adaptativo para capital pequeño:
    # Si el tamaño calculado es menor al mínimo del broker, necesitamos
    # forzar a min_units. Verificar que el riesgo efectivo no exceda el cap.
    if units < min_units:
        effective_risk = (min_units * stop_pips * pip_value) / account_balance
        if effective_risk > risk_pct * max_risk_multiplier:
            # Riesgo efectivo sobrepasa el cap aceptable — skip trade
            return 0.0
        units = min_units

    return units


def is_spread_acceptable(instrument: str, current_spread: float) -> bool:
    """Verifica si el spread actual es aceptable para operar."""
    key = _normalize_instrument(instrument)
    config = INSTRUMENT_CONFIG.get(key)
    if not config:
        return True  # Si no conocemos el instrumento, permitir

    spread_pips = current_spread / config["pip_size"]
    acceptable = spread_pips <= config["max_spread_pips"]

    if not acceptable:
        log.info(
            "Spread demasiado alto para %s: %.1f pips (máx: %.1f)",
            instrument, spread_pips, config["max_spread_pips"],
        )

    return acceptable


def get_buffer_price(instrument: str, buffer_pips: float = 1.0) -> float:
    """Obtiene el buffer en precio para entry/stop (1 pip por defecto)."""
    return buffer_pips * get_pip_size(instrument)


def get_stepped_risk_base(
    current_balance: float,
    base_capital: float,
    step_pct: float = 0.50,
) -> tuple[float, float]:
    """Calcula la base de riesgo escalonado (stepped compound interest).

    El riesgo se calcula sobre base_capital, NO sobre current_balance.
    La base solo sube cuando el balance alcanza base_capital × (1 + step_pct).

    Ejemplo: base=$10K, step=50% → riesgo sobre $10K hasta que balance
    llegue a $15K → entonces base=$15K, next=$22.5K.

    Args:
        current_balance: Balance actual de la cuenta del broker.
        base_capital: Base de capital actual para calcular riesgo.
        step_pct: Porcentaje de incremento para subir de nivel (default 50%).

    Returns:
        Tupla (risk_base, next_threshold):
        - risk_base: base sobre la cual calcular el 1% de riesgo
        - next_threshold: balance al que hay que llegar para subir de nivel
    """
    threshold = base_capital * (1 + step_pct)
    if current_balance >= threshold:
        new_base = threshold
        return new_base, new_base * (1 + step_pct)
    return base_capital, threshold
