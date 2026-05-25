"""One-shot debug: query WS positions directly and dump raw shape for a
few sample positions so we can see what totalValue.currency actually is."""

from __future__ import annotations

import json
import keyring
from ws_api import WealthsimpleAPI, WSAPISession


def main() -> int:
    raw = keyring.get_password("lunchsimple", "session")
    if not raw:
        print("NO SESSION in keyring; run `lunchsimple login` first.")
        return 1
    session = WSAPISession.from_json(raw)
    api = WealthsimpleAPI.from_token(session, lambda j: keyring.set_password(
        "lunchsimple", "session", j))

    edges = api.do_graphql_query(
        "FetchIdentityPositions",
        {
            "identityId": api.get_token_info().get("identity_canonical_id"),
            "currency": "CAD",
            "filter": {"securityIds": None},
            "first": 100,
            "aggregated": False,
            "includeAccountData": True,
            "includeSecurity": True,
        },
        "identity.financials.current.positions.edges",
        "array",
        load_all_pages=True,
    )

    print(f"Got {len(edges)} edges\n")
    spot = ("AMD", "AAPL", "AMZN", "VFV", "VEQT", "JD", "HOOD")
    seen: set = set()
    for edge in edges:
        node = edge.get("node", edge)
        security = node.get("security") or {}
        stock = security.get("stock") or {}
        symbol = stock.get("symbol", "?")
        if symbol in spot and symbol not in seen:
            seen.add(symbol)
            print(f"=== {symbol} ===")
            print(f"  security.currency:   {security.get('currency')!r}")
            print(f"  security.securityType: {security.get('securityType')!r}")
            print(f"  stock.primaryExchange: {stock.get('primaryExchange')!r}")
            print(f"  totalValue:          {json.dumps(node.get('totalValue'))}")
            print(f"  marketBookValue:     {json.dumps(node.get('marketBookValue'))}")
            print(f"  quantity:            {node.get('quantity')!r}")
            print(f"  accounts ids:        {[a.get('id') for a in node.get('accounts') or []]}")
            print()

    # Also show account-level cash holdings (the missing-money hypothesis):
    print("=== Account balances (the WS-dashboard 'balance' figure) ===")
    accounts = api.get_accounts()
    for acct in accounts:
        try:
            bal = api.get_account_balances(acct["id"])
            print(f"  {acct.get('unifiedAccountType','?'):40}  cash/positions: {bal}")
        except Exception as exc:
            print(f"  {acct.get('unifiedAccountType','?'):40}  ERROR: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
