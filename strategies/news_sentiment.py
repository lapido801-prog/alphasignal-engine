from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

from .base import BaseStrategy, StrategyResult, Candle
from supabase_client import supabase


class NewsSentimentStrategy(BaseStrategy):
    code = "NEWS_SENTIMENT_MOMENTUM"
    name = "News Sentiment Momentum"
    timeframe = "1D"

    def __init__(
        self,
        lookback_hours: int = 24,
        min_articles: int = 2,
    ):
        self.lookback_hours = lookback_hours
        self.min_articles = min_articles

    def _fetch_recent_news(self, symbol: str) -> List[Dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)
        resp = (
            supabase.table("news_articles")
            .select("*")
            .eq("symbol", symbol)
            .gte("published_at", since.isoformat())
            .order("published_at", desc=True)
            .execute()
        )
        return resp.data or []

    def _aggregate_sentiment(self, articles: List[Dict[str, Any]]) -> float:
        if not articles:
            return 0.0

        weighted_sum = 0.0
        weight_total = 0.0
        now = datetime.now(timezone.utc)

        for art in articles:
            s = float(art.get("sentiment_score") or 0.0)  # verwacht -1..1
            impact = float(art.get("impact_score") or 0.5)

            published_at_str = art.get("published_at")
            if isinstance(published_at_str, str):
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            else:
                published_at = now

            hours_ago = (now - published_at).total_seconds() / 3600.0
            recency_weight = max(0.1, 1.0 / (1.0 + hours_ago / 8.0))

            w = impact * recency_weight
            weighted_sum += s * w
            weight_total += w

        return weighted_sum / weight_total if weight_total > 0 else 0.0

    def generate_signal(self, symbol: str, candles: List[Candle]) -> StrategyResult:
        """
        Deze wordt alleen intern gebruikt door de combinaties.
        """
        articles = self._fetch_recent_news(symbol)

        if len(articles) < self.min_articles:
            return {
                "signal_type": "HOLD",
                "confidence": 0.1,
                "extra": {
                    "reason": "not_enough_news",
                    "articles_count": len(articles),
                    "avg_sentiment": 0.0,
                },
            }

        avg_sentiment = self._aggregate_sentiment(articles)  # -1..1
        confidence = min(1.0, max(0.0, abs(avg_sentiment)))

        # JIJ WILT GEEN SELL:
        # positief sentiment -> BUY
        # niet-positief     -> HOLD
        if avg_sentiment > 0:
            signal_type = "BUY"
        else:
            signal_type = "HOLD"

        return {
            "signal_type": signal_type,
            "confidence": round(confidence, 3),
            "extra": {
                "avg_sentiment": round(avg_sentiment, 3),
                "articles_count": len(articles),
            },
        }
