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


_USD_CAD_FALLBACK = Decimal("1.37")  # used when yfinance is unreachable


def _fetch_usd_cad_rate() -> Decimal:
    """One yfinance hit per refresh for the spot USD/CAD rate.

    Returns a recent-history fallback (~1.37) when yfinance is unreachable
    so the dashboard still renders rather than crashing the refresh.
    """
    try:
        import yfinance as yf  # local import to keep cold-start lean

        hist = yf.Ticker("USDCAD=X").history(period="1d")
        if not hist.empty:
            return Decimal(str(float(hist["Close"].iloc[-1])))
    except Exception:
        pass
    return _USD_CAD_FALLBACK


def _to_cad(amount: str, currency: str, usd_cad_rate: Decimal) -> Decimal:
    """Convert a (amount, currency) pair from WS to CAD using the FX rate."""
    value = Decimal(str(amount))
    if currency and currency.upper() == "USD":
        return value * usd_cad_rate
    return value


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
            # USD/CAD spot rate — also needed for USD cash balances even
            # though totalValue itself already comes back CAD-converted.
            usd_cad_rate = _fetch_usd_cad_rate()

            # Cash sleeves per account. FetchIdentityPositions only returns
            # invested positions; cash (sec-c-cad / sec-c-usd) lives in a
            # separate account_balances call. Without this the per-account
            # totals are 3-30% short of the WS account-page balance and
            # the entire CASH / margin-loan accounts are invisible.
            cash_by_account: dict[str, dict] = {}
            for acct in accounts:
                try:
                    cash_by_account[acct["id"]] = api.get_account_balances(acct["id"])
                except Exception:
                    cash_by_account[acct["id"]] = {}
        except (ManualLoginRequired, LoginFailedException) as exc:
            # Spec §10: surface auth banner, hide page body; NOT cache fallback.
            raise WealthsimpleAuthError(
                f"Wealthsimple session expired or invalid — run "
                f"`lunchsimple login` to reconnect: {exc}"
            ) from exc
        except Exception as exc:
            return self._render_from_cache(reason=f"WS API failed: {exc!s}")

        positions = self._normalize_positions(edges, accounts, usd_cad_rate)
        positions.extend(
            self._normalize_cash(accounts, cash_by_account, usd_cad_rate)
        )
        self._write_cache(positions)
        return PositionsResult(positions=positions, stale_minutes=0, warnings=[])

    @staticmethod
    def _normalize_cash(
        accounts: list[dict],
        cash_by_account: dict[str, dict],
        usd_cad_rate: Decimal,
    ) -> list[Position]:
        """Synthesize a CASH Position per account so cash sleeves count.

        Lumps each account's CAD + USD cash into a single CAD-valued
        Position with symbol='CASH'. USD cash (e.g. sec-c-usd) is FX-
        converted using the spot rate. Negative balances (margin loans)
        flow through as-is so the account total reflects the debt.

        Accounts with zero cash are skipped so we don't fill the
        concentration tile with empty rows.
        """
        out: list[Position] = []
        for acct in accounts:
            balances = cash_by_account.get(acct["id"], {})
            try:
                cad = Decimal(str(balances.get("sec-c-cad", "0")))
                usd = Decimal(str(balances.get("sec-c-usd", "0")))
            except Exception:
                continue
            total = cad + (usd * usd_cad_rate)
            if total == 0:
                continue
            out.append(
                Position(
                    account_id=acct["id"],
                    account_type=acct.get("unifiedAccountType", "UNKNOWN"),
                    account_nickname=acct.get("nickname", "") or "",
                    symbol="CASH",
                    name="Cash",
                    security_type="CASH",
                    listing_currency="CAD",
                    listing_exchange="",
                    quantity=Decimal("1"),
                    market_value_cad=total,
                    book_value_cad=total,
                )
            )
        return out

    @staticmethod
    def _normalize_positions(
        edges: list[dict],
        accounts: list[dict],
        usd_cad_rate: Decimal,
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

            # totalValue / marketBookValue come back in the position's
            # NATIVE currency (WS rejects currencyOverride='CAD' as
            # UNPROCESSABLE_ENTITY). Convert USD → CAD client-side using
            # the live FX rate.
            tv = node.get("totalValue") or {}
            mbv = node.get("marketBookValue") or {}
            qty = node.get("quantity") or "0"

            value_cad = _to_cad(tv.get("amount", "0"), tv.get("currency", "CAD"), usd_cad_rate)
            book_cad = _to_cad(mbv.get("amount", "0"), mbv.get("currency", "CAD"), usd_cad_rate)

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
                    market_value_cad=value_cad,
                    book_value_cad=book_cad,
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
