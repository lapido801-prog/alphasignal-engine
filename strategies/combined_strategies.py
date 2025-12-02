from __future__ import annotations
from typing import List

from .base import BaseStrategy, StrategyResult, Candle
from .indicators import compute_rsi, simple_ma, highest_high
from .news_sentiment import NewsSentimentStrategy


class NewsRSICombo(BaseStrategy):
    code = "NEWS_RSI_COMBO"
    name = "News + RSI Mean Reversion"
    timeframe = "1D"

    def __init__(
        self,
        news_strategy: NewsSentimentStrategy,
        rsi_period: int = 14,
        oversold: float = 30.0,
    ):
        self.news_strategy = news_strategy
        self.rsi_period = rsi_period
        self.oversold = oversold

    def generate_signal(self, symbol: str, candles: List[Candle]) -> StrategyResult:
        if len(candles) < self.rsi_period + 1:
            return {
                "signal_type": "HOLD",
                "confidence": 0.1,
                "extra": {"reason": "not_enough_candles"},
            }

        closes = [c["close"] for c in candles]
        rsi = compute_rsi(closes, self.rsi_period)
        tech_buy = rsi < self.oversold  # alleen oversold → BUY-kans

        news_res = self.news_strategy.generate_signal(symbol, candles)
        avg_sentiment = float(news_res["extra"].get("avg_sentiment", 0.0))

        tech_score = 1.0 if tech_buy else 0.0
        news_score = max(0.0, avg_sentiment)  # alleen positief telt mee

        tech_weight = 0.7 * (1 if tech_buy else 0.5)
        news_weight = 0.3 * max(0.2, news_res["confidence"])

        combined_score = tech_weight * tech_score + news_weight * news_score
        max_possible = tech_weight + news_weight
        normalized = combined_score / max_possible if max_possible > 0 else 0.0

        signal_type = "BUY" if tech_buy and normalized >= 0.35 else "HOLD"
        confidence = normalized if signal_type == "BUY" else 0.2

        return {
            "signal_type": signal_type,
            "confidence": round(confidence, 3),
            "extra": {
                "normalized_score": round(normalized, 3),
                "rsi": round(rsi, 2),
                "news": news_res,
            },
        }


class NewsBreakoutCombo(BaseStrategy):
    code = "NEWS_BREAKOUT_COMBO"
    name = "News + Breakout High Momentum (20D)"
    timeframe = "1D"

    def __init__(
        self,
        news_strategy: NewsSentimentStrategy,
        lookback: int = 20,
    ):
        self.news_strategy = news_strategy
        self.lookback = lookback

    def generate_signal(self, symbol: str, candles: List[Candle]) -> StrategyResult:
        if len(candles) < self.lookback + 1:
            return {
                "signal_type": "HOLD",
                "confidence": 0.1,
                "extra": {"reason": "not_enough_candles"},
            }

        last = candles[-1]
        hh = highest_high(candles[:-1], self.lookback)
        close = last["close"]

        tech_buy = close > hh  # breakout boven hoogste high

        news_res = self.news_strategy.generate_signal(symbol, candles)
        avg_sentiment = float(news_res["extra"].get("avg_sentiment", 0.0))
        news_score = max(0.0, avg_sentiment)

        tech_score = 1.0 if tech_buy else 0.0

        tech_weight = 0.7 * (1 if tech_buy else 0.5)
        news_weight = 0.3 * max(0.2, news_res["confidence"])

        combined_score = tech_weight * tech_score + news_weight * news_score
        max_possible = tech_weight + news_weight
        normalized = combined_score / max_possible if max_possible > 0 else 0.0

        signal_type = "BUY" if tech_buy and normalized >= 0.35 else "HOLD"
        confidence = normalized if signal_type == "BUY" else 0.2

        return {
            "signal_type": signal_type,
            "confidence": round(confidence, 3),
            "extra": {
                "normalized_score": round(normalized, 3),
                "close": close,
                "highest_high_lookback": hh,
                "news": news_res,
            },
        }


class NewsTrendMA200Combo(BaseStrategy):
    code = "NEWS_TREND_MA200_COMBO"
    name = "News + Trend MA200 Pullback"
    timeframe = "1D"

    def __init__(
        self,
        news_strategy: NewsSentimentStrategy,
        ma_period: int = 200,
        pullback_pct: float = 0.05,
    ):
        self.news_strategy = news_strategy
        self.ma_period = ma_period
        self.pullback_pct = pullback_pct

    def generate_signal(self, symbol: str, candles: List[Candle]) -> StrategyResult:
        if len(candles) < self.ma_period + 20:
            return {
                "signal_type": "HOLD",
                "confidence": 0.1,
                "extra": {"reason": "not_enough_candles"},
            }

        closes = [c["close"] for c in candles]
        ma200 = simple_ma(closes, self.ma_period)
        last = candles[-1]
        close = last["close"]

        uptrend = close > ma200

        recent_closes = closes[-20:]
        recent_high = max(recent_closes)
        drop_from_high = (recent_high - close) / recent_high if recent_high > 0 else 0.0

        tech_buy = uptrend and (self.pullback_pct * 0.5 <= drop_from_high <= self.pullback_pct)

        news_res = self.news_strategy.generate_signal(symbol, candles)
        avg_sentiment = float(news_res["extra"].get("avg_sentiment", 0.0))
        news_score = max(0.0, avg_sentiment)

        tech_score = 1.0 if tech_buy else 0.0
        tech_weight = 0.7 * (1 if tech_buy else 0.5)
        news_weight = 0.3 * max(0.2, news_res["confidence"])

        combined_score = tech_weight * tech_score + news_weight * news_score
        max_possible = tech_weight + news_weight
        normalized = combined_score / max_possible if max_possible > 0 else 0.0

        signal_type = "BUY" if tech_buy and normalized >= 0.35 else "HOLD"
        confidence = normalized if signal_type == "BUY" else 0.2

        return {
            "signal_type": signal_type,
            "confidence": round(confidence, 3),
            "extra": {
                "normalized_score": round(normalized, 3),
                "ma200": round(ma200, 2),
                "close": close,
                "recent_high": recent_high,
                "drop_from_high": round(drop_from_high, 3),
                "news": news_res,
            },
        }


def build_combined_strategies():
    """
    Alleen combinaties! Geen losse technische strategieën.
    """
    news = NewsSentimentStrategy()

    return [
        NewsRSICombo(news_strategy=news),
        NewsBreakoutCombo(news_strategy=news),
        NewsTrendMA200Combo(news_strategy=news),
    ]
