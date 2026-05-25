"""Inspect ~/.networthlab/positions_cache.json — what the dashboard sees.

Run with:  .venv/bin/python scripts/inspect_cache.py
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path


def main() -> int:
    cache = Path.home() / ".networthlab" / "positions_cache.json"
    if not cache.is_file():
        print(f"NO CACHE at {cache}")
        return 1
    data = json.loads(cache.read_text())
    positions = data["positions"]
    fetched = data.get("fetched_at", "unknown")
    print(f"Cache fetched_at: {fetched}")
    print(f"Total positions:  {len(positions)}")
    print()

    sums = collections.defaultdict(float)
    counts = collections.Counter()
    for p in positions:
        sums[p["account_type"]] += float(p["market_value_cad"])
        counts[p["account_type"]] += 1

    print("=== Per-account-type CAD sum ===")
    total = 0.0
    for t in sorted(sums):
        print(f"  {t:45} count={counts[t]:3} sum=${sums[t]:>12,.2f}")
        total += sums[t]
    print(f"  {'TOTAL':45}           ${total:>12,.2f}")
    print()

    print("=== Spot-check (these should look CAD-normalized after the fix) ===")
    spot = ("AAPL", "AMD", "AMZN", "NVDA", "JD", "ADBE")
    seen = set()
    for p in positions:
        if p["symbol"] in spot and p["symbol"] not in seen:
            seen.add(p["symbol"])
            v = float(p["market_value_cad"])
            print(
                f"  {p['symbol']:8} ccy={p['listing_currency']:4} "
                f"value=${v:,.2f}"
            )

    print()
    print("=== USD-listed positions total ===")
    usd_total = sum(
        float(p["market_value_cad"])
        for p in positions
        if p["listing_currency"] == "USD"
    )
    print(f"  USD positions sum: ${usd_total:,.2f}")
    print(
        "  (if this looks like CAD-converted values, the fix worked; "
        "if it looks like raw USD, it didn't)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
