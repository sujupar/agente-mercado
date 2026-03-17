"""Interfaz abstracta del broker — cualquier broker debe implementar estos métodos."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.broker.models import AccountState, BrokerPosition, Candle, OrderResult, Price


class BrokerInterface(ABC):
    """Contrato que todo broker debe cumplir para integrarse con el agente."""

    # ── Cuenta ──────────────────────────────────────────────

    @abstractmethod
    async def get_account(self) -> AccountState:
        """Obtener estado actual de la cuenta (balance, equity, margen)."""

    @abstractmethod
    async def get_positions(self) -> list[BrokerPosition]:
        """Listar todas las posiciones abiertas."""

    # ── Datos de mercado ────────────────────────────────────

    @abstractmethod
    async def get_candles(
        self,
        instrument: str,
        timeframe: str,
        count: int = 250,
    ) -> list[Candle]:
        """Obtener velas históricas OHLCV.

        Args:
            instrument: Par de trading (ej. "EUR_USD")
            timeframe: Temporalidad (ej. "H1", "H4", "D")
            count: Número de velas a obtener
        """

    @abstractmethod
    async def get_price(self, instrument: str) -> Price:
        """Obtener precio actual bid/ask de un instrumento."""

    # ── Órdenes ─────────────────────────────────────────────

    @abstractmethod
    async def place_market_order(
        self,
        instrument: str,
        units: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> OrderResult:
        """Colocar orden de mercado.

        Args:
            instrument: Par de trading
            units: Unidades (positivo = compra, negativo = venta)
            stop_loss: Precio de stop loss
            take_profit: Precio de take profit
        """

    @abstractmethod
    async def modify_trade(
        self,
        trade_id: str,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> OrderResult:
        """Modificar stop loss y/o take profit de un trade existente."""

    @abstractmethod
    async def close_trade(
        self,
        trade_id: str,
        units: float | None = None,
    ) -> OrderResult:
        """Cerrar un trade (total o parcial).

        Args:
            trade_id: ID del trade en el broker
            units: Si se especifica, cierre parcial. Si None, cierre total.
        """

    # ── Utilidades ──────────────────────────────────────────

    @abstractmethod
    async def is_connected(self) -> bool:
        """Verificar si la conexión con el broker está activa."""

    @abstractmethod
    async def close(self) -> None:
        """Cerrar conexión con el broker y liberar recursos."""
