from __future__ import annotations
from typing import List
import numpy as np


def compute_rsi(closes: List[float], period: int = 14) -> float:
    """
    Simpele RSI-berekening. Geeft de laatste RSI terug.
    """
    if len(closes) < period + 1:
        return 50.0  # neutraal als er te weinig data is

    arr = np.array(closes, dtype=float)
    delta = np.diff(arr)

    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)

    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()

    # Wilder smoothing
    for i in range(period, len(delta)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi)


def simple_ma(values: List[float], period: int) -> float:
    if len(values) < period:
        return values[-1] if values else 0.0
    return float(sum(values[-period:]) / period)


def highest_high(candles, lookback: int) -> float:
    if len(candles) < lookback:
        return max(c["high"] for c in candles)
    return max(c["high"] for c in candles[-lookback:])
