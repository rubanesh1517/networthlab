"""Wealthsimple session handling and position fetch, normalized to `Position`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import keyring
from ws_api import WealthsimpleAPI, WSAPISession
from ws_api.exceptions import LoginFailedException, ManualLoginRequired

from networthlab.models import Position

KEYRING_SERVICE = "lunchsimple"
KEYRING_KEY = "session"
CACHE_FILE_NAME = "positions_cache.json"

# Wealthsimple returns bare symbols (e.g. "VEQT", "XEQT") that omit the exchange
# suffix yfinance and our security_overrides YAML require. Map primaryExchange ->
# the yfinance-compatible suffix and append it when missing.
_YFINANCE_SUFFIX_BY_EXCHANGE: dict[str, str] = {
    "TSX": ".TO",
    "TSX VENTURE": ".V",
    "TSXV": ".V",
    "NEO": ".NE",
    "CSE": ".CN",
    "LSE": ".L",
    "FRA": ".F",
    "ETR": ".DE",
    "TYO": ".T",
    "ASX": ".AX",
    "HKEX": ".HK",
    # US exchanges have no suffix in yfinance:
    "NASDAQ": "",
    "NYSE": "",
    "AMEX": "",
    "ARCA": "",
    "BATS": "",
    "NMS": "",
}


def _normalize_symbol(raw_symbol: str, listing_exchange: str) -> str:
    """Append the yfinance-style exchange suffix when the WS-returned symbol
    is bare (no dot). Leaves any already-suffixed symbol (e.g. "QQC.F",
    "VEQT.TO") alone. Unknown exchanges pass through unchanged."""
    if not raw_symbol or "." in raw_symbol:
        return raw_symbol
    suffix = _YFINANCE_SUFFIX_BY_EXCHANGE.get(listing_exchange.upper())
    if suffix is None or suffix == "":
        return raw_symbol
    return f"{raw_symbol}{suffix}"


class WealthsimpleAuthError(RuntimeError):
    """Raised when no session is available — UI should show a 'run lunchsimple login' banner."""


@dataclass
class PositionsResult:
    positions: list[Position]
    stale_minutes: int  # 0 when fresh; positive when rendered from cache fallback
    warnings: list[str]


class WealthsimpleService:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self._session_override: WSAPISession | None = None

    @staticmethod
    def load_session() -> WSAPISession | None:
        raw = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
        if not raw:
            return None
        try:
            return WSAPISession.from_json(raw)
        except Exception:
            return None

    @staticmethod
    def persist_session(session_json: str) -> None:
        keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, session_json)

    def fetch_positions(self) -> PositionsResult:
        session = self._session_override or self.load_session()
        if not session:
            raise WealthsimpleAuthError(
                "No Wealthsimple session found in keyring — run `lunchsimple login`."
            )

        try:
            api = WealthsimpleAPI.from_token(session, self.persist_session)
            accounts = api.get_accounts()
            # ws_api 0.34.0's get_identity_positions() helper does NOT pass
            # includeSecurity=True, and the GraphQL query gates the
            # SecuritySummary fragment behind @include(if: $includeSecurity).
            # Call do_graphql_query directly so we get the metadata.
            # Also: first/aggregated/load_all_pages for full pagination.
            edges = api.do_graphql_query(
                "FetchIdentityPositions",
                {
                    "identityId": api.get_token_info().get("identity_canonical_id"),
                    "currency": "CAD",
                    # currencyOverride controls per-position totalValue
                    # conversion — without it WS returns each position's
                    # native-currency value (USD for NASDAQ/NYSE listings)
                    # which then gets misread as CAD downstream.
                    "currencyOverride": "CAD",
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
        except (ManualLoginRequired, LoginFailedException) as exc:
            # Spec §10: surface auth banner, hide page body; NOT cache fallback.
            raise WealthsimpleAuthError(
                f"Wealthsimple session expired or invalid — run "
                f"`lunchsimple login` to reconnect: {exc}"
            ) from exc
        except Exception as exc:
            return self._render_from_cache(reason=f"WS API failed: {exc!s}")

        positions = self._normalize_positions(edges, accounts)
        self._write_cache(positions)
        return PositionsResult(positions=positions, stale_minutes=0, warnings=[])

    @staticmethod
    def _normalize_positions(
        edges: list[dict], accounts: list[dict]
    ) -> list[Position]:
        accounts_by_id = {acct["id"]: acct for acct in accounts}
        # WS occasionally returns the same (account, security) pair more than
        # once across edges (e.g. when a security exists in multiple accounts
        # and the response still aggregates the accounts list per edge). Dedup
        # by (account_id, symbol) so we never double-count a single position
        # toward the per-account-type totals.
        deduped: dict[tuple[str, str], Position] = {}
        for edge in edges:
            node = edge.get("node", edge)
            security = node.get("security") or {}
            stock = security.get("stock") or {}
            raw_symbol = stock.get("symbol") or security.get("id", "UNKNOWN")
            security_type = security.get("securityType") or "EQUITY"
            listing_currency = security.get("currency") or "CAD"
            listing_exchange = stock.get("primaryExchange") or ""
            # Normalize WS bare tickers (VEQT -> VEQT.TO) so override YAML
            # lookups AND yfinance fetches use the same form.
            symbol = _normalize_symbol(raw_symbol, listing_exchange)
            name = stock.get("name") or symbol

            value = (node.get("totalValue") or {}).get("amount", "0")
            book = (node.get("marketBookValue") or {}).get("amount", "0")
            qty = node.get("quantity") or "0"

            account_ids = [a["id"] for a in (node.get("accounts") or [])]
            if not account_ids:
                continue

            for account_id in account_ids:
                key = (account_id, symbol)
                if key in deduped:
                    continue  # WS already gave us this (account, symbol)
                acct = accounts_by_id.get(account_id, {})
                deduped[key] = Position(
                    account_id=account_id,
                    account_type=acct.get("unifiedAccountType", "UNKNOWN"),
                    account_nickname=acct.get("nickname", "") or "",
                    symbol=symbol,
                    name=name,
                    security_type=security_type,
                    listing_currency=listing_currency,
                    listing_exchange=listing_exchange,
                    quantity=Decimal(str(qty)),
                    market_value_cad=Decimal(str(value)),
                    book_value_cad=Decimal(str(book)),
                )
        return list(deduped.values())

    def _cache_path(self) -> Path:
        return self.cache_dir / CACHE_FILE_NAME

    def _write_cache(self, positions: list[Position]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "positions": [p.model_dump(mode="json") for p in positions],
        }
        self._cache_path().write_text(json.dumps(payload, indent=2, default=str))

    def _render_from_cache(self, reason: str) -> PositionsResult:
        path = self._cache_path()
        if not path.is_file():
            return PositionsResult(positions=[], stale_minutes=0, warnings=[reason])
        data = json.loads(path.read_text())
        positions = [Position.model_validate(p) for p in data["positions"]]
        fetched = datetime.fromisoformat(data["fetched_at"])
        stale_minutes = int(
            (datetime.now(timezone.utc) - fetched).total_seconds() // 60
        )
        return PositionsResult(
            positions=positions,
            stale_minutes=max(stale_minutes, 1),
            warnings=[reason, f"showing cached snapshot ({stale_minutes}m old)"],
        )
