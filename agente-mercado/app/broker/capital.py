"""Implementación de BrokerInterface para Capital.com REST API."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.broker.base import BrokerInterface
from app.broker.models import AccountState, BrokerPosition, Candle, OrderResult, Price

log = logging.getLogger(__name__)

# Mapeo de timeframes internos a resoluciones Capital.com
_TIMEFRAME_MAP = {
    "M1": "MINUTE",
    "M5": "MINUTE_5",
    "M15": "MINUTE_15",
    "M30": "MINUTE_30",
    "H1": "HOUR",
    "H4": "HOUR_4",
    "D": "DAY",
    "W": "WEEK",
    # Aliases comunes
    "1m": "MINUTE",
    "5m": "MINUTE_5",
    "15m": "MINUTE_15",
    "30m": "MINUTE_30",
    "1h": "HOUR",
    "4h": "HOUR_4",
    "1d": "DAY",
}

# Instrumento interno (EUR_USD) → Capital.com epic (EURUSD)
_INSTRUMENT_TO_CAPITAL = {
    "EUR_USD": "EURUSD",
    "GBP_USD": "GBPUSD",
    "USD_JPY": "USDJPY",
    "XAU_USD": "GOLD",
}

_CAPITAL_TO_INSTRUMENT = {v: k for k, v in _INSTRUMENT_TO_CAPITAL.items()}


def to_capital_epic(instrument: str) -> str:
    """Convierte 'EUR_USD' al epic de Capital.com 'EURUSD'."""
    if "_" not in instrument:
        return instrument
    return _INSTRUMENT_TO_CAPITAL.get(instrument, instrument.replace("_", ""))


def from_capital_epic(epic: str) -> str:
    """Convierte epic Capital.com 'EURUSD' a formato interno 'EUR_USD'."""
    return _CAPITAL_TO_INSTRUMENT.get(epic, epic)


class CapitalBroker(BrokerInterface):
    """Broker Capital.com — REST API con sesiones CST/Security Token."""

    def __init__(
        self,
        api_key: str,
        identifier: str,
        password: str,
        environment: str = "DEMO",
    ) -> None:
        self._api_key = api_key
        self._identifier = identifier
        self._password = password

        if environment.upper() == "LIVE":
            self._base_url = "https://api-capital.backend-capital.com"
        else:
            self._base_url = "https://demo-api-capital.backend-capital.com"

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "X-CAP-API-KEY": self._api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        # Tokens de sesión (se obtienen al autenticarse)
        self._cst: str = ""
        self._security_token: str = ""
        self._authenticated = False

        log.info(
            "Capital.com broker inicializado: env=%s, identifier=%s",
            environment,
            identifier[:5] + "...",
        )

    # ── Autenticación ────────────────────────────────────────

    async def _authenticate(self) -> None:
        """Crear sesión con Capital.com — obtener CST + Security Token."""
        try:
            response = await self._client.post(
                "/api/v1/session",
                json={
                    "identifier": self._identifier,
                    "password": self._password,
                    "encryptedPassword": False,
                },
            )
            response.raise_for_status()

            self._cst = response.headers.get("CST", "")
            self._security_token = response.headers.get("X-SECURITY-TOKEN", "")
            self._authenticated = True

            # Actualizar headers del cliente con los tokens
            self._client.headers["CST"] = self._cst
            self._client.headers["X-SECURITY-TOKEN"] = self._security_token

            log.info("Capital.com autenticado exitosamente")
        except httpx.HTTPStatusError as e:
            log.error("Capital.com auth error: %s — %s", e.response.status_code, e.response.text)
            self._authenticated = False
            raise
        except httpx.RequestError as e:
            log.error("Capital.com connection error: %s", e)
            self._authenticated = False
            raise

    async def _ensure_session(self) -> None:
        """Asegurar que tenemos una sesión válida."""
        if not self._authenticated:
            await self._authenticate()

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Ejecutar request HTTP autenticado contra Capital.com."""
        await self._ensure_session()

        try:
            response = await self._client.request(
                method, path, json=json, params=params
            )

            # Si el token expiró, re-autenticar e intentar de nuevo
            if response.status_code == 401:
                log.info("Sesión expirada, re-autenticando...")
                self._authenticated = False
                await self._authenticate()
                response = await self._client.request(
                    method, path, json=json, params=params
                )

            response.raise_for_status()

            # Algunos endpoints devuelven 200 sin body
            if response.status_code == 204 or not response.content:
                return {}

            return response.json()
        except httpx.HTTPStatusError as e:
            body = e.response.text
            log.error(
                "Capital.com API error %s %s: %s — %s",
                method, path, e.response.status_code, body,
            )
            raise
        except httpx.RequestError as e:
            log.error("Capital.com connection error %s %s: %s", method, path, e)
            raise

    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime de Capital.com (ISO 8601)."""
        if not dt_str:
            return datetime.now(timezone.utc)
        # Capital.com devuelve formato "2024/01/15 10:30:00" o ISO
        dt_str = dt_str.replace("/", "-")
        try:
            if "T" in dt_str:
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        except (ValueError, TypeError):
            return datetime.now(timezone.utc)

    # ── Cuenta ──────────────────────────────────────────────

    async def get_account(self) -> AccountState:
        data = await self._request("GET", "/api/v1/accounts")
        accounts = data.get("accounts", [])
        if not accounts:
            raise ValueError("No se encontraron cuentas en Capital.com")

        acct = accounts[0]
        balance_info = acct.get("balance", {})

        return AccountState(
            balance=float(balance_info.get("balance", 0)),
            unrealized_pnl=float(balance_info.get("profitLoss", 0)),
            margin_used=float(balance_info.get("deposit", 0)),
            margin_available=float(balance_info.get("available", 0)),
            open_trade_count=0,  # Se calcula con get_positions
            currency=acct.get("currency", "USD"),
        )

    async def get_positions(self) -> list[BrokerPosition]:
        data = await self._request("GET", "/api/v1/positions")
        positions = []

        for pos in data.get("positions", []):
            position = pos.get("position", {})
            market = pos.get("market", {})

            # Units: positivo para LONG (BUY), negativo para SHORT (SELL)
            size = float(position.get("size", 0))
            direction = position.get("direction", "BUY")
            units = size if direction == "BUY" else -size

            epic = market.get("epic", "")
            instrument = from_capital_epic(epic)

            sl = position.get("stopLevel")
            tp = position.get("profitLevel")

            positions.append(
                BrokerPosition(
                    trade_id=position.get("dealId", ""),
                    instrument=instrument,
                    units=units,
                    entry_price=float(position.get("level", 0)),
                    unrealized_pnl=float(position.get("upl", 0)),
                    stop_loss=float(sl) if sl is not None else None,
                    take_profit=float(tp) if tp is not None else None,
                    trailing_stop_distance=None,
                    open_time=self._parse_datetime(
                        position.get("createdDateUTC", "")
                    ),
                )
            )
        return positions

    # ── Datos de mercado ────────────────────────────────────

    async def get_candles(
        self,
        instrument: str,
        timeframe: str,
        count: int = 250,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[Candle]:
        epic = to_capital_epic(instrument)
        resolution = _TIMEFRAME_MAP.get(timeframe, timeframe)

        params: dict = {
            "resolution": resolution,
            "max": min(count, 1000),
            "pageSize": min(count, 1000),
        }
        if from_dt:
            params["from"] = from_dt.strftime("%Y-%m-%dT%H:%M:%S")
        if to_dt:
            params["to"] = to_dt.strftime("%Y-%m-%dT%H:%M:%S")

        data = await self._request(
            "GET",
            f"/api/v1/prices/{epic}",
            params=params,
        )

        candles = []
        for p in data.get("prices", []):
            # Capital.com devuelve bid/ask OHLC por separado, usamos midpoint
            bid = p.get("closePrice", p.get("bidPrice", {}))
            ask = p.get("closePrice", p.get("askPrice", {}))

            # Si tenemos open/high/low/close individuales
            snapshot_time = p.get("snapshotTimeUTC", p.get("snapshotTime", ""))

            open_bid = float(p.get("openPrice", {}).get("bid", 0))
            open_ask = float(p.get("openPrice", {}).get("ask", 0))
            high_bid = float(p.get("highPrice", {}).get("bid", 0))
            high_ask = float(p.get("highPrice", {}).get("ask", 0))
            low_bid = float(p.get("lowPrice", {}).get("bid", 0))
            low_ask = float(p.get("lowPrice", {}).get("ask", 0))
            close_bid = float(p.get("closePrice", {}).get("bid", 0))
            close_ask = float(p.get("closePrice", {}).get("ask", 0))

            # Midpoint (promedio bid/ask)
            o = (open_bid + open_ask) / 2 if open_ask else open_bid
            h = (high_bid + high_ask) / 2 if high_ask else high_bid
            l = (low_bid + low_ask) / 2 if low_ask else low_bid
            c = (close_bid + close_ask) / 2 if close_ask else close_bid

            vol = float(p.get("lastTradedVolume", 0))

            if o > 0 and h > 0 and l > 0 and c > 0:
                candles.append(
                    Candle(
                        timestamp=self._parse_datetime(snapshot_time),
                        open=o,
                        high=h,
                        low=l,
                        close=c,
                        volume=vol,
                    )
                )

        return candles

    async def get_price(self, instrument: str) -> Price:
        epic = to_capital_epic(instrument)

        # Usar el endpoint de markets para obtener bid/ask actual
        data = await self._request(
            "GET",
            f"/api/v1/markets/{epic}",
        )

        snapshot = data.get("snapshot", {})
        bid = float(snapshot.get("bid", 0))
        ask = float(snapshot.get("offer", 0))

        if bid <= 0 or ask <= 0:
            raise ValueError(f"No se encontró precio válido para {instrument}")

        return Price(
            instrument=instrument,
            bid=bid,
            ask=ask,
            time=self._parse_datetime(snapshot.get("updateTimeUTC", "")),
        )

    # ── Órdenes ─────────────────────────────────────────────

    async def place_market_order(
        self,
        instrument: str,
        units: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> OrderResult:
        epic = to_capital_epic(instrument)
        direction = "BUY" if units > 0 else "SELL"
        size = abs(units)

        order_body: dict = {
            "epic": epic,
            "direction": direction,
            "size": size,
            "guaranteedStop": False,
        }

        if stop_loss is not None:
            order_body["stopLevel"] = stop_loss
        if take_profit is not None:
            order_body["profitLevel"] = take_profit

        try:
            data = await self._request(
                "POST",
                "/api/v1/positions",
                json=order_body,
            )

            deal_reference = data.get("dealReference", "")

            # Confirmar la orden consultando el dealReference
            if deal_reference:
                confirm = await self._request(
                    "GET",
                    f"/api/v1/confirms/{deal_reference}",
                )

                deal_id = confirm.get("dealId", "")
                deal_status = confirm.get("dealStatus", "")
                level = float(confirm.get("level", 0))
                affected_deals = confirm.get("affectedDeals", [])

                if deal_status == "ACCEPTED":
                    if affected_deals:
                        deal_id = affected_deals[0].get("dealId", deal_id)

                    log.info(
                        "Orden ejecutada: %s %s %s size=%.2f @ %.5f (deal=%s)",
                        direction, instrument, epic, size, level, deal_id,
                    )

                    return OrderResult(
                        success=True,
                        trade_id=deal_id,
                        instrument=instrument,
                        fill_price=level,
                        units=units,
                        raw_response=confirm,
                    )
                else:
                    reason = confirm.get("reason", "Unknown")
                    log.warning(
                        "Orden rechazada: %s %s — %s", instrument, direction, reason
                    )
                    return OrderResult(
                        success=False,
                        instrument=instrument,
                        error=f"{deal_status}: {reason}",
                        raw_response=confirm,
                    )

            return OrderResult(
                success=False,
                instrument=instrument,
                error="No dealReference returned",
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
            body["stopLevel"] = stop_loss
        if take_profit is not None:
            body["profitLevel"] = take_profit

        if not body:
            return OrderResult(success=True, trade_id=trade_id, error="Nada que modificar")

        try:
            data = await self._request(
                "PUT",
                f"/api/v1/positions/{trade_id}",
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
        try:
            # Capital.com cierra posiciones con DELETE
            # Para cierre parcial, se puede especificar el size
            if units is not None:
                # Cierre parcial: necesitamos saber la dirección
                # Capital.com no soporta DELETE con body, se usa header
                data = await self._request(
                    "DELETE",
                    f"/api/v1/positions/{trade_id}",
                )
            else:
                data = await self._request(
                    "DELETE",
                    f"/api/v1/positions/{trade_id}",
                )

            deal_reference = data.get("dealReference", "")

            if deal_reference:
                confirm = await self._request(
                    "GET",
                    f"/api/v1/confirms/{deal_reference}",
                )

                deal_status = confirm.get("dealStatus", "")
                level = float(confirm.get("level", 0))
                profit = float(confirm.get("profit", 0))

                if deal_status == "ACCEPTED":
                    log.info(
                        "Trade %s cerrado @ %.5f, P&L: $%.2f",
                        trade_id, level, profit,
                    )
                    return OrderResult(
                        success=True,
                        trade_id=trade_id,
                        fill_price=level,
                        raw_response=confirm,
                    )

                reason = confirm.get("reason", "Unknown")
                return OrderResult(
                    success=False,
                    trade_id=trade_id,
                    error=f"{deal_status}: {reason}",
                    raw_response=confirm,
                )

            return OrderResult(
                success=False,
                trade_id=trade_id,
                error="No dealReference on close",
                raw_response=data,
            )

        except Exception as e:
            log.exception("Error cerrando trade %s", trade_id)
            return OrderResult(success=False, trade_id=trade_id, error=str(e))

    # ── Utilidades ──────────────────────────────────────────

    async def is_connected(self) -> bool:
        try:
            await self._ensure_session()
            await self._request("GET", "/api/v1/accounts")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        # Cerrar sesión
        if self._authenticated:
            try:
                await self._client.delete("/api/v1/session")
            except Exception:
                pass
        await self._client.aclose()
        log.info("Conexión Capital.com cerrada")
