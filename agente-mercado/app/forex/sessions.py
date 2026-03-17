"""Filtros de sesión Forex — solo operar durante horas de alta liquidez."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class TradingSession:
    """Definición de una sesión de trading."""

    name: str
    start_hour_utc: int
    end_hour_utc: int
    strength: int  # 1 = bajo, 2 = medio, 3 = alto

    def is_active(self, utc_hour: int) -> bool:
        if self.start_hour_utc <= self.end_hour_utc:
            return self.start_hour_utc <= utc_hour < self.end_hour_utc
        # Sesión que cruza medianoche (no aplica a las actuales, pero por robustez)
        return utc_hour >= self.start_hour_utc or utc_hour < self.end_hour_utc


# Sesiones principales
LONDON = TradingSession(name="London", start_hour_utc=7, end_hour_utc=16, strength=3)
NEW_YORK = TradingSession(name="New York", start_hour_utc=12, end_hour_utc=21, strength=3)
OVERLAP = TradingSession(name="London-NY Overlap", start_hour_utc=12, end_hour_utc=16, strength=3)
TOKYO = TradingSession(name="Tokyo", start_hour_utc=0, end_hour_utc=9, strength=1)

# Sesiones en las que permitimos nuevas entradas
TRADING_SESSIONS = [LONDON, NEW_YORK]


def is_trading_session(
    utc_time: datetime | None = None,
    require_overlap: bool = False,
) -> bool:
    """Verifica si estamos en una sesión válida para abrir nuevas operaciones.

    Por defecto: permite durante Londres (07-16 UTC) y NY (12-21 UTC).
    Si require_overlap=True: solo durante el overlap Londres-NY (12-16 UTC).

    Args:
        utc_time: Hora a evaluar. Si None, usa la hora actual UTC.
        require_overlap: Si True, solo permite durante el overlap.
    """
    if utc_time is None:
        utc_time = datetime.now(timezone.utc)

    hour = utc_time.hour

    if require_overlap:
        return OVERLAP.is_active(hour)

    return any(session.is_active(hour) for session in TRADING_SESSIONS)


def is_forex_market_open(utc_time: datetime | None = None) -> bool:
    """Verifica si el mercado Forex está abierto.

    Forex cierra viernes 21:00 UTC y abre domingo 21:00 UTC.
    """
    if utc_time is None:
        utc_time = datetime.now(timezone.utc)

    weekday = utc_time.weekday()  # 0=lunes, 6=domingo
    hour = utc_time.hour

    # Sábado completo cerrado
    if weekday == 5:
        return False

    # Viernes después de 21:00 UTC cerrado
    if weekday == 4 and hour >= 21:
        return False

    # Domingo antes de 21:00 UTC cerrado
    if weekday == 6 and hour < 21:
        return False

    return True


def get_current_session(utc_time: datetime | None = None) -> str:
    """Retorna el nombre de la sesión activa, o 'Closed' si no hay ninguna."""
    if utc_time is None:
        utc_time = datetime.now(timezone.utc)

    if not is_forex_market_open(utc_time):
        return "Closed"

    hour = utc_time.hour

    if OVERLAP.is_active(hour):
        return OVERLAP.name

    if LONDON.is_active(hour):
        return LONDON.name

    if NEW_YORK.is_active(hour):
        return NEW_YORK.name

    if TOKYO.is_active(hour):
        return TOKYO.name

    return "Off-Hours"
