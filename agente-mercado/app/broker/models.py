"""Modelos de datos compartidos para la capa de broker."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Candle:
    """Vela OHLCV."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def is_green(self) -> bool:
        return self.close >= self.open

    @property
    def is_red(self) -> bool:
        return self.close < self.open

    @property
    def body(self) -> float:
        """Tamaño absoluto del cuerpo."""
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        """Rango total de la vela (high - low)."""
        return self.high - self.low

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def midpoint(self) -> float:
        return (self.high + self.low) / 2


@dataclass(frozen=True)
class Price:
    """Precio bid/ask actual de un instrumento."""

    instrument: str
    bid: float
    ask: float
    time: datetime

    @property
    def spread(self) -> float:
        return self.ask - self.bid

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2


@dataclass(frozen=True)
class AccountState:
    """Estado de la cuenta del broker."""

    balance: float
    unrealized_pnl: float
    margin_used: float
    margin_available: float
    open_trade_count: int
    currency: str = "USD"

    @property
    def equity(self) -> float:
        return self.balance + self.unrealized_pnl


@dataclass(frozen=True)
class BrokerPosition:
    """Posición abierta en el broker."""

    trade_id: str
    instrument: str
    units: float  # positivo = long, negativo = short
    entry_price: float
    unrealized_pnl: float
    stop_loss: float | None = None
    take_profit: float | None = None
    trailing_stop_distance: float | None = None
    open_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def direction(self) -> str:
        return "LONG" if self.units > 0 else "SHORT"

    @property
    def abs_units(self) -> float:
        return abs(self.units)


@dataclass(frozen=True)
class OrderResult:
    """Resultado de una operación de orden en el broker."""

    success: bool
    trade_id: str = ""
    instrument: str = ""
    fill_price: float = 0.0
    units: float = 0.0
    error: str = ""
    raw_response: dict = field(default_factory=dict)

    @property
    def direction(self) -> str:
        return "LONG" if self.units > 0 else "SHORT"
