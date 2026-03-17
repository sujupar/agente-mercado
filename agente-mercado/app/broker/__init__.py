"""Capa de abstracción del broker — interfaz unificada para OANDA y futuros brokers."""

from app.broker.base import BrokerInterface
from app.broker.models import (
    AccountState,
    BrokerPosition,
    Candle,
    OrderResult,
    Price,
)

__all__ = [
    "BrokerInterface",
    "AccountState",
    "BrokerPosition",
    "Candle",
    "OrderResult",
    "Price",
]
