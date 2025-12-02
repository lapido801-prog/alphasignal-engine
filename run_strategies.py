# run_strategies.py
from __future__ import annotations
from typing import List, Optional

from supabase_client import supabase
from strategies import build_combined_strategies
from strategies.base import Candle


def fetch_candles_from_db(symbol: str, timeframe: str = "1D") -> List[Candle]:
    resp = (
        supabase.table("candles")
        .select("time, open, high, low, close, volume")
        .eq("symbol", symbol)
        .eq("timeframe", timeframe)
        .order("time", desc=True)
        .limit(300)
        .execute()
    )
    data = resp.data or []
    data.reverse()  # oud -> nieuw
    return data  # type: ignore[return-value]


def get_asset_id(symbol: str) -> Optional[str]:
    resp = (
        supabase.table("assets")
        .select("id")
        .eq("symbol", symbol)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        print(f"[WARN] Geen asset gevonden voor symbol={symbol} in 'assets' tabel")
        return None
    return rows[0]["id"]


def get_strategy_id(slug: str) -> Optional[str]:
    resp = (
        supabase.table("strategies")
        .select("id")
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        print(f"[WARN] Geen strategy gevonden voor slug={slug} in 'strategies' tabel")
        return None
    return rows[0]["id"]


def normalize_signal_type(signal_type: str) -> str:
    """
    Veiligheidsnet: alles wat geen BUY is, wordt HOLD.
    Zo komt er NOOIT 'SELL' in de database.
    """
    return "BUY" if signal_type == "BUY" else "HOLD"


def run_for_asset(symbol: str, timeframe: str = "1D"):
    candles = fetch_candles_from_db(symbol, timeframe)
    if not candles:
        print(f"[WARN] Geen candles voor {symbol}")
        return

    asset_id = get_asset_id(symbol)
    if not asset_id:
        print(f"[WARN] Skip {symbol} omdat er geen asset_id is")
        return

    last_candle = candles[-1]
    strategies = build_combined_strategies()

    for strat in strategies:
        if strat.timeframe != timeframe:
            continue

        strategy_slug = getattr(strat, "code", None)
        if not strategy_slug:
            print(f"[WARN] Strategie zonder code: {strat}")
            continue

        strategy_id = get_strategy_id(strategy_slug)
        if not strategy_id:
            print(f"[WARN] Skip strategie {strategy_slug} omdat er geen strategy_id is")
            continue

        res = strat.generate_signal(symbol, candles)
        signal_type = normalize_signal_type(res["signal_type"])

        payload = {
            "asset_id": asset_id,
            "strategy_id": strategy_id,
            "signal_type": signal_type,        # ALTIJD BUY of HOLD
            "price": last_candle["close"],
            "timeframe": strat.timeframe,
            "generated_at": last_candle["time"],
            "meta": res["extra"],              # extra info in meta jsonb
        }

        supabase.table("signals").insert(payload).execute()
        print(f"[OK] {symbol} - {strategy_slug} -> {signal_type} ({res['confidence']})")


def run_for_universe(symbols: List[str]):
    for symbol in symbols:
        run_for_asset(symbol)


if __name__ == "__main__":
    # Voor nu alleen AAPL, omdat we daar candles + asset voor hebben
    symbols = ["AAPL"]
    run_for_universe(symbols)
