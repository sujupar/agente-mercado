"""Implementación de BrokerInterface para Capital.com REST API."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from app.broker.base import BrokerInterface
from app.broker.models import AccountState, BrokerPosition, Candle, OrderResult, Price

log = logging.getLogger(__name__)

# Rate limit de Capital.com en /session (login): ~10 req/min por cuenta.
# Si nos exceden → 429 "too-many.requests". Implementamos cooldown agresivo.
_SESSION_MIN_INTERVAL_SEC = 30.0  # Entre logins del mismo broker: mínimo 30s
_SESSION_TTL_SEC = 600.0          # Reutilizar sesión hasta 10 min (CST token dura ~10min)

# Locks de autenticación globales por identifier (cuenta Capital.com).
# Capital.com rate-limit /session por cuenta: si DEMO y LIVE comparten identifier
# (o dos instancias apuntan a la misma cuenta), el lock por instancia no basta.
# Compartir un lock module-level por identifier evita requests paralelos a /session.
_GLOBAL_AUTH_LOCKS: dict[str, asyncio.Lock] = {}


def _get_global_auth_lock(identifier: str) -> asyncio.Lock:
    lock = _GLOBAL_AUTH_LOCKS.get(identifier)
    if lock is None:
        lock = asyncio.Lock()
        _GLOBAL_AUTH_LOCKS[identifier] = lock
    return lock

# Mapeo de timeframes internos a resoluciones Capital.com
_TIMEFRAME_MAP = {
    "M1": "MINUTE",
    "M5": "MINUTE_5",
    "M15": "MINUTE_15",
    "M30": "MINUTE_30",
    "H1": "HOUR",
    "H4": "HOUR_4",
    "D": "DAY",
    "D1": "DAY",
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

        # Control de concurrencia + rate limit de /session
        # Sin esto, múltiples corrutinas golpean /session al mismo tiempo
        # → Capital.com responde 429 "too-many.requests" y banea.
        # El lock es GLOBAL por identifier: DEMO y LIVE con la misma cuenta
        # (o dos instancias del mismo env) comparten el lock y no se pisan.
        self._auth_lock = _get_global_auth_lock(identifier)
        self._last_auth_at: float = 0.0  # time.monotonic() del último login exitoso
        self._last_auth_attempt_at: float = 0.0  # incluye intentos fallidos

        # Cache de markets (min_size, step, límites SL/TP) para pre-validar
        # órdenes y EVITAR 400 "error.invalid.size.minvalue" etc.
        self._market_cache: dict = {}  # epic → {min_size, step, ...}
        self._market_cache_at: dict = {}  # epic → monotonic timestamp

        log.info(
            "Capital.com broker inicializado: env=%s, identifier=%s",
            environment,
            identifier[:5] + "...",
        )

    # ── Autenticación ────────────────────────────────────────

    async def _authenticate(self) -> None:
        """Crear sesión con Capital.com — obtener CST + Security Token.

        Protegido por self._auth_lock: solo 1 login concurrente.
        Respeta cooldown _SESSION_MIN_INTERVAL_SEC entre intentos.
        """
        async with self._auth_lock:
            # Doble-check: otra corrutina pudo haber autenticado mientras esperábamos el lock
            now = time.monotonic()
            if self._authenticated and (now - self._last_auth_at) < _SESSION_TTL_SEC:
                return

            # Cooldown: evitar 429 en /session
            elapsed_since_attempt = now - self._last_auth_attempt_at
            if elapsed_since_attempt < _SESSION_MIN_INTERVAL_SEC:
                wait = _SESSION_MIN_INTERVAL_SEC - elapsed_since_attempt
                log.info(
                    "Auth cooldown: esperando %.1fs antes de reintentar /session",
                    wait,
                )
                await asyncio.sleep(wait)

            self._last_auth_attempt_at = time.monotonic()

            try:
                response = await self._client.post(
                    "/api/v1/session",
                    json={
                        "identifier": self._identifier,
                        "password": self._password,
                        "encryptedPassword": False,
                    },
                )
                # 429: backoff agresivo antes de raise
                if response.status_code == 429:
                    log.warning(
                        "Capital.com /session 429 — backoff 60s",
                    )
                    # Marcar el último intento para que el cooldown tenga efecto
                    self._authenticated = False
                    await asyncio.sleep(60.0)
                    response.raise_for_status()  # propagar para que el caller decida

                response.raise_for_status()

                self._cst = response.headers.get("CST", "")
                self._security_token = response.headers.get("X-SECURITY-TOKEN", "")
                self._authenticated = True
                self._last_auth_at = time.monotonic()

                # Actualizar headers del cliente con los tokens
                self._client.headers["CST"] = self._cst
                self._client.headers["X-SECURITY-TOKEN"] = self._security_token

                log.info("Capital.com autenticado exitosamente")
            except httpx.HTTPStatusError as e:
                log.error(
                    "Capital.com auth error: %s — %s",
                    e.response.status_code, e.response.text,
                )
                self._authenticated = False
                raise
            except httpx.RequestError as e:
                log.error("Capital.com connection error: %s", e)
                self._authenticated = False
                raise

    async def _ensure_session(self) -> None:
        """Asegurar que tenemos una sesión válida, REUTILIZANDO si está fresca."""
        now = time.monotonic()
        session_age = now - self._last_auth_at

        # Si tenemos sesión activa Y fresca (< TTL) → reusar sin tocar /session
        if self._authenticated and session_age < _SESSION_TTL_SEC:
            return

        # Sesión inexistente o caducada → autenticar (con lock + cooldown)
        await self._authenticate()

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
        _retry_count: int = 0,
    ) -> dict:
        """Ejecutar request HTTP autenticado contra Capital.com.

        Retry policy:
        - 401 (unauthorized): re-auth 1 vez y reintentar
        - 429 (too-many-requests): backoff exponencial (1s, 2s, 4s, 8s) hasta 3 retries
        - Otros errores: raise inmediato
        """
        await self._ensure_session()

        try:
            response = await self._client.request(
                method, path, json=json, params=params
            )

            # 401: token expirado — re-auth 1 vez
            if response.status_code == 401 and _retry_count == 0:
                log.info("Sesión expirada, re-autenticando...")
                self._authenticated = False
                await self._authenticate()
                return await self._request(
                    method, path, json=json, params=params,
                    _retry_count=_retry_count + 1,
                )

            # 429: rate limit — backoff exponencial
            if response.status_code == 429 and _retry_count < 3:
                backoff = 2 ** _retry_count  # 1s, 2s, 4s
                log.warning(
                    "429 rate limit en %s %s — backoff %ds (retry %d/3)",
                    method, path, backoff, _retry_count + 1,
                )
                await asyncio.sleep(backoff)
                return await self._request(
                    method, path, json=json, params=params,
                    _retry_count=_retry_count + 1,
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

    async def _get_market_details(self, epic: str) -> dict:
        """Obtiene y cachea detalles del mercado (min_size, step, precio actual, límites).

        Permite pre-validar órdenes antes de POST para evitar rejects 400.
        Cache TTL: 5 min — los límites cambian raramente.
        """
        now = time.monotonic()
        cached_at = self._market_cache_at.get(epic, 0)
        if epic in self._market_cache and (now - cached_at) < 300:
            return self._market_cache[epic]

        try:
            data = await self._request("GET", f"/api/v1/markets/{epic}")
            dealing_rules = data.get("dealingRules", {})
            snapshot = data.get("snapshot", {})

            # min_deal_size: mínimo contratos/lots que acepta
            min_size_rule = dealing_rules.get("minDealSize", {})
            max_stop_rule = dealing_rules.get("maxStopOrLimitDistance", {})
            min_stop_rule = dealing_rules.get("minStopOrLimitDistance", {})

            details = {
                "min_size": float(min_size_rule.get("value", 0.01)),
                "min_size_unit": min_size_rule.get("unit", ""),
                "max_stop_distance": float(max_stop_rule.get("value", 0)) if max_stop_rule else 0,
                "max_stop_unit": max_stop_rule.get("unit", "") if max_stop_rule else "",
                "min_stop_distance": float(min_stop_rule.get("value", 0)) if min_stop_rule else 0,
                "min_stop_unit": min_stop_rule.get("unit", "") if min_stop_rule else "",
                "bid": float(snapshot.get("bid", 0)),
                "offer": float(snapshot.get("offer", 0)),
                "market_status": snapshot.get("marketStatus", "TRADEABLE"),
            }
            self._market_cache[epic] = details
            self._market_cache_at[epic] = now
            return details
        except Exception as e:
            log.warning("No se pudo obtener market details para %s: %s", epic, e)
            # Fallback: permitir la orden, el broker la rechazará si falla
            return {"min_size": 0, "bid": 0, "offer": 0, "market_status": "TRADEABLE"}

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

        # ── PRE-VALIDACIÓN: evitar rejects 400 que Capital.com monitorea ──
        try:
            market = await self._get_market_details(epic)

            # Check 1: mercado tradeable
            if market.get("market_status") not in ("TRADEABLE", ""):
                log.warning(
                    "Skip orden %s: market_status=%s",
                    epic, market.get("market_status"),
                )
                return OrderResult(
                    success=False,
                    instrument=instrument,
                    error=f"market_not_tradeable: {market.get('market_status')}",
                )

            # Check 2: size >= min_deal_size (unit-aware)
            # Capital.com reporta `minDealSize.unit` que puede ser:
            #   - vacío o "" → raw (mismas unidades que mandamos en `size`).
            #     Evidencia: trades exitosos ~15 abr con size=700 en GBP_USD
            #     prueban que Capital acepta tamaños "raw" sub-lote.
            #   - "LOTS" → 1 lot = 100,000 unidades (forex CFD standard).
            #   - "AMOUNT" → notional USD (size × precio).
            # Si la unidad es desconocida, NO bloqueamos: mejor que el broker
            # decida que generar un falso positivo que pare trades válidos.
            min_size = market.get("min_size", 0)
            min_size_unit = (market.get("min_size_unit") or "").upper()
            if min_size > 0:
                size_comparable = None
                if min_size_unit == "LOTS":
                    size_comparable = size / 100_000
                elif min_size_unit == "AMOUNT":
                    ref = market.get("offer", 0) or market.get("bid", 0)
                    if ref > 0:
                        size_comparable = size * ref
                elif min_size_unit in ("", "POINTS"):
                    size_comparable = size
                # Otras unidades exóticas: size_comparable queda None → no check
                if size_comparable is not None and size_comparable < min_size:
                    log.warning(
                        "Skip orden %s: size=%.4f (comparable=%.4f unit=%s) < min=%.4f",
                        epic, size, size_comparable, min_size_unit or "RAW", min_size,
                    )
                    return OrderResult(
                        success=False,
                        instrument=instrument,
                        error=(
                            f"size_below_minimum: {size_comparable:.4f} "
                            f"< {min_size:.4f} ({min_size_unit or 'RAW'})"
                        ),
                    )

            # Check 3: SL/TP del lado correcto
            # BUY: SL debe ser < precio, TP debe ser > precio
            # SELL: SL debe ser > precio, TP debe ser < precio
            bid = market.get("bid", 0)
            offer = market.get("offer", 0)
            ref_price = offer if direction == "BUY" else bid
            if ref_price > 0:
                if direction == "BUY":
                    if stop_loss is not None and stop_loss >= ref_price:
                        log.warning(
                            "Skip orden BUY %s: SL=%.5f >= precio=%.5f (invalid side)",
                            epic, stop_loss, ref_price,
                        )
                        return OrderResult(
                            success=False,
                            instrument=instrument,
                            error=f"stop_loss_wrong_side: SL={stop_loss} >= price={ref_price}",
                        )
                    if take_profit is not None and take_profit <= ref_price:
                        log.warning(
                            "Skip orden BUY %s: TP=%.5f <= precio=%.5f (invalid side)",
                            epic, take_profit, ref_price,
                        )
                        return OrderResult(
                            success=False,
                            instrument=instrument,
                            error=f"take_profit_wrong_side: TP={take_profit} <= price={ref_price}",
                        )
                else:  # SELL
                    if stop_loss is not None and stop_loss <= ref_price:
                        log.warning(
                            "Skip orden SELL %s: SL=%.5f <= precio=%.5f (invalid side)",
                            epic, stop_loss, ref_price,
                        )
                        return OrderResult(
                            success=False,
                            instrument=instrument,
                            error=f"stop_loss_wrong_side: SL={stop_loss} <= price={ref_price}",
                        )
                    if take_profit is not None and take_profit >= ref_price:
                        log.warning(
                            "Skip orden SELL %s: TP=%.5f >= precio=%.5f (invalid side)",
                            epic, take_profit, ref_price,
                        )
                        return OrderResult(
                            success=False,
                            instrument=instrument,
                            error=f"take_profit_wrong_side: TP={take_profit} >= price={ref_price}",
                        )
        except Exception:
            log.exception("Error en pre-validación %s (continuando, broker validará)", epic)

        # ── Envío de la orden ──────────────────────────────────
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
