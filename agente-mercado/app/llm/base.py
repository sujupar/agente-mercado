"""Interfaz abstracta para clientes LLM."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class ProbabilityEstimate:
    """Estimación del LLM para un par/mercado (legacy, mantenido por compatibilidad)."""

    symbol: str
    direction: str  # "BUY" | "SELL" | "HOLD"
    confidence: float  # 0.0 - 1.0
    deviation_pct: float
    take_profit_pct: float
    stop_loss_pct: float
    rationale: str
    data_sources: list[str] = field(default_factory=list)


class LLMClient(ABC):
    """Interfaz genérica para cualquier modelo LLM."""

    @abstractmethod
    async def close(self) -> None:
        ...
