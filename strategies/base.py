from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TypedDict, Dict, Any, List


class Candle(TypedDict):
    time: str         # ISO string, bv "2025-11-29T18:21:03Z"
    open: float
    high: float
    low: float
    close: float
    volume: float


class StrategyResult(TypedDict):
    signal_type: str          # "BUY" of "HOLD"
    confidence: float         # 0..1
    extra: Dict[str, Any]


class BaseStrategy(ABC):
    code: str
    name: str
    timeframe: str = "1D"

    @abstractmethod
    def generate_signal(self, symbol: str, candles: List[Candle]) -> StrategyResult:
        ...
