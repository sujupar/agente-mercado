"""Implementación de BrokerInterface para OANDA v20 REST API."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.broker.base import BrokerInterface
from app.broker.models import AccountState, BrokerPosition, Candle, OrderResult, Price

log = logging.getLogger(__name__)

# Mapeo de timeframes internos a granularidades OANDA
_TIMEFRAME_MAP = {
    "M1": "M1",
    "M5": "M5",
    "M15": "M15",
    "M30": "M30",
    "H1": "H1",
    "H4": "H4",
    "D": "D",
    "W": "W",
    "M": "M",
    # Aliases comunes
    "1m": "M1",
    "5m": "M5",
    "15m": "M15",
    "30m": "M30",
    "1h": "H1",
    "4h": "H4",
    "1d": "D",
}

# Instrumento display → OANDA format
_INSTRUMENT_TO_OANDA = {
    "EURUSD": "EUR_USD",
    "GBPUSD": "GBP_USD",
    "USDJPY": "USD_JPY",
    "XAUUSD": "XAU_USD",
    "BTCUSD": "BTC_USD",
}

_OANDA_TO_INSTRUMENT = {v: k for k, v in _INSTRUMENT_TO_OANDA.items()}


def to_oanda_instrument(instrument: str) -> str:
    """Convierte 'EURUSD' o 'EUR_USD' al formato OANDA 'EUR_USD'."""
    if "_" in instrument:
        return instrument
    return _INSTRUMENT_TO_OANDA.get(instrument, instrument)


def from_oanda_instrument(oanda_instrument: str) -> str:
    """Convierte 'EUR_USD' a display 'EURUSD'."""
    return _OANDA_TO_INSTRUMENT.get(oanda_instrument, oanda_instrument.replace("_", ""))


class OANDABroker(BrokerInterface):
    """Broker OANDA v20 — soporta demo y live con la misma API."""

    def __init__(
        self,
        account_id: str,
        access_token: str,
        environment: str = "practice",
    ) -> None:
        self._account_id = account_id
        self._access_token = access_token

        if environment == "live":
            self._base_url = "https://api-fxtrade.oanda.com"
        else:
            self._base_url = "https://api-fxpractice.oanda.com"

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
                "Accept-Datetime-Format": "RFC3339",
            },
            timeout=30.0,
        )

        log.info(
            "OANDA broker inicializado: env=%s, account=%s",
            environment,
            account_id[:8] + "..." if len(account_id) > 8 else account_id,
        )

    # ── Helpers internos ────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Ejecutar request HTTP contra la API de OANDA."""
        url = f"/v3/{path}"
        try:
            response = await self._client.request(
                method, url, json=json, params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            body = e.response.text
            log.error("OANDA API error %s %s: %s — %s", method, url, e.response.status_code, body)
            raise
        except httpx.RequestError as e:
            log.error("OANDA connection error %s %s: %s", method, url, e)
            raise

    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime RFC3339 de OANDA."""
        # OANDA devuelve formato como "2024-01-15T10:30:00.000000000Z"
        # Truncar nanosegundos a microsegundos
        if "." in dt_str:
            parts = dt_str.split(".")
            frac = parts[1].rstrip("Z")
            frac = frac[:6]  # max microsegundos
            dt_str = f"{parts[0]}.{frac}+00:00"
        else:
            dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)

    # ── Cuenta ──────────────────────────────────────────────

    async def get_account(self) -> AccountState:
        data = await self._request("GET", f"accounts/{self._account_id}/summary")
        acct = data["account"]
        return AccountState(
            balance=float(acct["balance"]),
            unrealized_pnl=float(acct["unrealizedPL"]),
            margin_used=float(acct["marginUsed"]),
            margin_available=float(acct["marginAvailable"]),
            open_trade_count=int(acct["openTradeCount"]),
            currency=acct.get("currency", "USD"),
        )

    async def get_positions(self) -> list[BrokerPosition]:
        data = await self._request("GET", f"accounts/{self._account_id}/openTrades")
        positions = []
        for trade in data.get("trades", []):
            sl = None
            tp = None
            trailing = None
            if "stopLossOrder" in trade:
                sl = float(trade["stopLossOrder"]["price"])
            if "takeProfitOrder" in trade:
                tp = float(trade["takeProfitOrder"]["price"])
            if "trailingStopLossOrder" in trade:
                trailing = float(trade["trailingStopLossOrder"]["distance"])

            positions.append(
                BrokerPosition(
                    trade_id=trade["id"],
                    instrument=trade["instrument"],
                    units=float(trade["currentUnits"]),
                    entry_price=float(trade["price"]),
                    unrealized_pnl=float(trade["unrealizedPL"]),
                    stop_loss=sl,
                    take_profit=tp,
                    trailing_stop_distance=trailing,
                    open_time=self._parse_datetime(trade["openTime"]),
                )
            )
        return positions

    # ── Datos de mercado ────────────────────────────────────

    async def get_candles(
        self,
        instrument: str,
        timeframe: str,
        count: int = 250,
    ) -> list[Candle]:
        oanda_instrument = to_oanda_instrument(instrument)
        granularity = _TIMEFRAME_MAP.get(timeframe, timeframe)

        data = await self._request(
            "GET",
            f"instruments/{oanda_instrument}/candles",
            params={
                "granularity": granularity,
                "count": min(count, 5000),  # OANDA max es 5000
                "price": "M",  # Midpoint (promedio bid/ask)
            },
        )

        candles = []
        for c in data.get("candles", []):
            if not c.get("complete", False):
                continue  # Solo velas completas
            mid = c["mid"]
            candles.append(
                Candle(
                    timestamp=self._parse_datetime(c["time"]),
                    open=float(mid["o"]),
                    high=float(mid["h"]),
                    low=float(mid["l"]),
                    close=float(mid["c"]),
                    volume=float(c.get("volume", 0)),
                )
            )
        return candles

    async def get_price(self, instrument: str) -> Price:
        oanda_instrument = to_oanda_instrument(instrument)
        data = await self._request(
            "GET",
            f"accounts/{self._account_id}/pricing",
            params={"instruments": oanda_instrument},
        )

        prices = data.get("prices", [])
        if not prices:
            raise ValueError(f"No se encontró precio para {instrument}")

        p = prices[0]
        # Usar el mejor bid/ask disponible
        bids = p.get("bids", [])
        asks = p.get("asks", [])
        bid = float(bids[0]["price"]) if bids else float(p.get("closeoutBid", 0))
        ask = float(asks[0]["price"]) if asks else float(p.get("closeoutAsk", 0))

        return Price(
            instrument=instrument,
            bid=bid,
            ask=ask,
            time=self._parse_datetime(p["time"]),
        )

    # ── Órdenes ─────────────────────────────────────────────

    async def place_market_order(
        self,
        instrument: str,
        units: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> OrderResult:
        oanda_instrument = to_oanda_instrument(instrument)

        order_body: dict = {
            "type": "MARKET",
            "instrument": oanda_instrument,
            "units": str(int(units)) if instrument in ("XAU_USD", "XAUUSD") else str(units),
            "timeInForce": "FOK",  # Fill or Kill
            "positionFill": "DEFAULT",
        }

        if stop_loss is not None:
            order_body["stopLossOnFill"] = {
                "price": f"{stop_loss:.5f}",
                "timeInForce": "GTC",
            }
        if take_profit is not None:
            order_body["takeProfitOnFill"] = {
                "price": f"{take_profit:.5f}",
                "timeInForce": "GTC",
            }

        try:
            data = await self._request(
                "POST",
                f"accounts/{self._account_id}/orders",
                json={"order": order_body},
            )

            # Verificar si la orden fue ejecutada
            if "orderFillTransaction" in data:
                fill = data["orderFillTransaction"]
                trade_id = ""
                if "tradeOpened" in fill:
                    trade_id = fill["tradeOpened"]["tradeID"]

                log.info(
                    "Orden ejecutada: %s %s units @ %s (trade_id=%s)",
                    instrument,
                    units,
                    fill.get("price", "N/A"),
                    trade_id,
                )

                return OrderResult(
                    success=True,
                    trade_id=trade_id,
                    instrument=instrument,
                    fill_price=float(fill.get("price", 0)),
                    units=float(fill.get("units", units)),
                    raw_response=data,
                )

            # Orden rechazada
            reject = data.get("orderRejectTransaction", {})
            reason = reject.get("rejectReason", "Unknown rejection")
            log.warning("Orden rechazada: %s %s — %s", instrument, units, reason)
            return OrderResult(
                success=False,
                instrument=instrument,
                error=reason,
                raw_response=data,
            )

        except Exception as e:
            log.exception("Error colocando orden %s %s", instrument, units)
            return OrderResult(
                success=False,
                instrument=instrument,
                error=str(e),
            )

    async def modify_trade(
        self,
        trade_id: str,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> OrderResult:
        body: dict = {}

        if stop_loss is not None:
            body["stopLoss"] = {
                "price": f"{stop_loss:.5f}",
                "timeInForce": "GTC",
            }
        if take_profit is not None:
            body["takeProfit"] = {
                "price": f"{take_profit:.5f}",
                "timeInForce": "GTC",
            }

        if not body:
            return OrderResult(success=True, trade_id=trade_id, error="Nada que modificar")

        try:
            data = await self._request(
                "PUT",
                f"accounts/{self._account_id}/trades/{trade_id}/orders",
                json=body,
            )

            log.info("Trade %s modificado: SL=%s, TP=%s", trade_id, stop_loss, take_profit)
            return OrderResult(
                success=True,
                trade_id=trade_id,
                raw_response=data,
            )
        except Exception as e:
            log.exception("Error modificando trade %s", trade_id)
            return OrderResult(success=False, trade_id=trade_id, error=str(e))

    async def close_trade(
        self,
        trade_id: str,
        units: float | None = None,
    ) -> OrderResult:
        body: dict = {}
        if units is not None:
            body["units"] = str(abs(units))
        else:
            body["units"] = "ALL"

        try:
            data = await self._request(
                "PUT",
                f"accounts/{self._account_id}/trades/{trade_id}/close",
                json=body,
            )

            fill = data.get("orderFillTransaction", {})
            fill_price = float(fill.get("price", 0))
            filled_units = float(fill.get("units", 0))
            realized_pnl = float(fill.get("pl", 0))

            log.info(
                "Trade %s cerrado: %s units @ %s, P&L: $%.2f",
                trade_id, filled_units, fill_price, realized_pnl,
            )

            return OrderResult(
                success=True,
                trade_id=trade_id,
                fill_price=fill_price,
                units=filled_units,
                raw_response=data,
            )
        except Exception as e:
            log.exception("Error cerrando trade %s", trade_id)
            return OrderResult(success=False, trade_id=trade_id, error=str(e))

    # ── Utilidades ──────────────────────────────────────────

    async def is_connected(self) -> bool:
        try:
            await self._request("GET", f"accounts/{self._account_id}/summary")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()
        log.info("Conexión OANDA cerrada")
