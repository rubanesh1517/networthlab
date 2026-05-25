"""Classify each security into per-dimension breakdowns.

MVP fallback chains (see spec §6):
  ETF asset_class: override -> provider -> unclassified
  ETF sector:      override -> provider -> unclassified
  ETF geography:   override -> name-pattern -> stock-exchange aggregation -> unclassified
  Non-ETF asset_class: override -> from security_type -> unclassified
  Non-ETF sector:      override -> provider (info["sector"]) -> unclassified
  Non-ETF geography:   override -> listing exchange -> unclassified
  currency:        always derived from listing_currency

This task implements override + currency + the unclassified default.
Provider/name-pattern/stock-exchange/listing-exchange branches are added
in Tasks 5-6.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Union

import yfinance as yf

from networthlab.models import (
    ClassificationComponent,
    DimensionBreakdown,
    SecurityClassification,
)
from networthlab.services.exposure_config import (
    ComplexSecurityFlag,
    SecurityOverride,
    SecurityOverrideBundle,
)


def _unclassified(notes: list[str] | None = None) -> DimensionBreakdown:
    return DimensionBreakdown(
        buckets={},
        source="unclassified",
        as_of=None,
        notes=notes or [],
    )


# Float drift below this is treated as "essentially 1.0" — no normalization.
# 0.001 catches publisher rounding (e.g., VEQT geography 1.003) while ignoring
# yfinance's float-precision noise (~1e-6).
_WEIGHT_DRIFT_TOLERANCE = Decimal("0.001")

_CACHE_FILE_NAME = "yfinance_cache.json"
_CACHE_TTL = timedelta(hours=24)

_YF_ASSET_CLASS_MAP = {
    "stockPosition": "equity",
    "bondPosition": "bond",
    "cashPosition": "cash",
    "preferredPosition": "preferred",
    "convertiblePosition": "convertible",
    "otherPosition": "other",
}

_SECURITY_TYPE_ASSET_CLASS = {
    "EQUITY": "equity",
    "STOCK": "equity",
    "ETF": "equity",
    "BOND": "bond",
    "CRYPTO": "crypto",
    "CASH": "cash",
    "OPTION": "option",
}

# Name-pattern -> country (geography, ETF only). First match wins.
_NAME_PATTERNS: list[tuple[str, str]] = [
    ("s&p 500", "US"),
    ("total us", "US"),
    ("us total", "US"),
    ("nasdaq", "US"),
    ("ftse canada", "CAN"),
    ("tsx 60", "CAN"),
    ("tsx composite", "CAN"),
    ("eafe", "INTL_DEV"),
    ("intl developed", "INTL_DEV"),
    ("emerging markets", "EM"),
]

# Listing exchange -> country (used for non-ETF positions AND for
# stock-exchange aggregation across an ETF's top_holdings).
_EXCHANGE_COUNTRY: dict[str, str] = {
    "NASDAQ": "US",
    "NYSE": "US",
    "AMEX": "US",
    "BATS": "US",
    "ARCA": "US",
    "NMS": "US",
    "TSX": "CAN",
    "TSXV": "CAN",
    "NEO": "CAN",
    "LSE": "INTL_DEV",
    "TYO": "INTL_DEV",
    "FRA": "INTL_DEV",
    "ASX": "INTL_DEV",
    "HKEX": "EM",
    "SSE": "EM",
    "BSE": "EM",
    "NSE": "EM",
}


def _normalize_buckets(
    buckets: dict[str, Decimal],
    notes: list[str],
    *,
    preserve_excess: bool,
) -> dict[str, Decimal]:
    """Coerce buckets to sum ~1.0 for charting.

    preserve_excess=True (asset_class only):
      - total > 1.0 -> leave as-is (preserves leverage / review_complex signal)
      - total < 1.0 -> add an "other" remainder rather than scaling up
    preserve_excess=False (sector / geography / others):
      - scale to sum to exactly 1.0 when drift > tolerance
    """
    if not buckets:
        return buckets
    total = sum(buckets.values())
    if total <= 0:
        return buckets
    delta = abs(total - Decimal("1"))
    if delta <= _WEIGHT_DRIFT_TOLERANCE:
        return buckets
    if preserve_excess and total > Decimal("1"):
        notes.append(f"weights sum to {total:.4f} (leverage preserved, not normalized)")
        return buckets
    if preserve_excess and total < Decimal("1"):
        remainder = Decimal("1") - total
        out = dict(buckets)
        out["other"] = out.get("other", Decimal("0")) + remainder
        notes.append(f"weights summed to {total:.4f}; added 'other' = {remainder:.4f}")
        return out
    scaled = {k: v / total for k, v in buckets.items()}
    notes.append(f"weights renormalized (raw sum was {total:.4f})")
    return scaled


def _override_breakdown(
    dim_value: Union[dict[str, Decimal], str],
    as_of,
    *,
    preserve_excess: bool,
) -> DimensionBreakdown | None:
    """Return a DimensionBreakdown if the override is a concrete dict.
    Returns None if the override says `provider` (caller falls through)."""
    if dim_value == "provider":
        return None
    if isinstance(dim_value, dict):
        buckets = {k: Decimal(str(v)) for k, v in dim_value.items()}
        notes: list[str] = []
        buckets = _normalize_buckets(buckets, notes, preserve_excess=preserve_excess)
        return DimensionBreakdown(
            buckets=buckets,
            source="override",
            as_of=as_of,
            notes=notes,
        )
    return None


class _DictAttr:
    """Adapt a cached dict back to the yfinance funds_data shape so the rest
    of the classifier doesn't care whether data came from cache or live."""

    class _ToDict:
        def __init__(self, payload):
            self._payload = payload

        def to_dict(self):
            return self._payload

    def __init__(self, payload: dict):
        self.sector_weightings = payload.get("sector_weightings", {})
        self.asset_classes = payload.get("asset_classes", {})
        self.top_holdings = _DictAttr._ToDict(payload.get("top_holdings", {}))


class EtfLookthroughService:
    """Classify each held symbol into per-dimension breakdowns.

    `yfinance_disabled=True` short-circuits any network call — used in unit tests.
    """

    def __init__(
        self,
        overrides: SecurityOverrideBundle,
        complex_flags: dict[str, ComplexSecurityFlag],
        cache_dir: Path,
        yfinance_disabled: bool = False,
    ):
        self.overrides = overrides
        self.complex_flags = complex_flags
        self.cache_dir = cache_dir
        self.yfinance_disabled = yfinance_disabled
        self._cache: dict[str, dict] = self._load_cache()

    # ------------------------------------------------------------------
    # Disk cache (yfinance results)
    # ------------------------------------------------------------------

    def _cache_path(self) -> Path:
        return self.cache_dir / _CACHE_FILE_NAME

    def _load_cache(self) -> dict[str, dict]:
        path = self._cache_path()
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_cache(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path().write_text(json.dumps(self._cache, indent=2, default=str))

    def _cache_lookup(self, symbol: str, field: str):
        entry = self._cache.get(symbol)
        if not entry:
            return None
        try:
            fetched = datetime.fromisoformat(entry["fetched_at"])
        except (KeyError, ValueError):
            return None
        if datetime.now(timezone.utc) - fetched > _CACHE_TTL:
            return None
        return entry.get(field)

    def _cache_store(self, symbol: str, field: str, value) -> None:
        entry = self._cache.setdefault(
            symbol, {"fetched_at": datetime.now(timezone.utc).isoformat()}
        )
        entry["fetched_at"] = datetime.now(timezone.utc).isoformat()
        entry[field] = value
        self._save_cache()

    def classify(
        self,
        symbol: str,
        security_type: str,
        name: str,
        listing_exchange: str,
        listing_currency: str,
    ) -> SecurityClassification:
        override = self.overrides.securities.get(symbol)
        is_etf = security_type.upper() == "ETF"

        asset_class = self._classify_asset_class(override, is_etf, security_type, symbol)
        sector = self._classify_sector(override, is_etf, symbol)
        geography = self._classify_geography(override, is_etf, name, listing_exchange, symbol)
        currency = self._derive_currency(listing_currency)

        flag = self.complex_flags.get(symbol)

        return SecurityClassification(
            symbol=symbol,
            asset_class=asset_class,
            geography=geography,
            sector=sector,
            currency=currency,
            complexity_flag=flag.flag if flag else None,
            components=[
                ClassificationComponent(
                    symbol=symbol,
                    weight=Decimal("1.0"),
                    source=asset_class.source,
                )
            ],
            fetched_at=datetime.now(timezone.utc),
        )

    def _classify_asset_class(
        self,
        override: SecurityOverride | None,
        is_etf: bool,
        security_type: str,
        symbol: str,
    ) -> DimensionBreakdown:
        if override:
            ob = _override_breakdown(override.asset_class, override.as_of, preserve_excess=True)
            if ob:
                return ob
        if not is_etf:
            bucket = _SECURITY_TYPE_ASSET_CLASS.get(security_type.upper())
            if bucket:
                return DimensionBreakdown(
                    buckets={bucket: Decimal("1.0")},
                    source="heuristic",
                    as_of=None,
                    notes=[f"derived from security_type={security_type}"],
                )
            return _unclassified(notes=[f"unknown security_type={security_type}"])
        if self.yfinance_disabled:
            return _unclassified(notes=["yfinance disabled"])
        try:
            fd = self._get_funds_data(symbol)
            raw = getattr(fd, "asset_classes", None) or {}
        except Exception as exc:
            return _unclassified(notes=[f"yfinance error: {exc!s}"])
        buckets: dict[str, Decimal] = {}
        for yf_key, weight in raw.items():
            bucket = _YF_ASSET_CLASS_MAP.get(yf_key, yf_key)
            w = Decimal(str(weight))
            if w > 0:
                buckets[bucket] = buckets.get(bucket, Decimal("0")) + w
        if not buckets:
            return _unclassified(notes=["yfinance asset_classes empty"])
        notes: list[str] = []
        buckets = _normalize_buckets(buckets, notes, preserve_excess=True)
        return DimensionBreakdown(
            buckets=buckets, source="provider", as_of=None, notes=notes
        )

    def _classify_sector(
        self,
        override: SecurityOverride | None,
        is_etf: bool,
        symbol: str,
    ) -> DimensionBreakdown:
        if override:
            ob = _override_breakdown(override.sector, override.as_of, preserve_excess=False)
            if ob:
                return ob
        if self.yfinance_disabled:
            return _unclassified(notes=["yfinance disabled"])
        try:
            if is_etf:
                fd = self._get_funds_data(symbol)
                raw = getattr(fd, "sector_weightings", None) or {}
            else:
                info = self._get_info(symbol)
                sector_name = (info or {}).get("sector")
                raw = {sector_name.lower(): 1.0} if sector_name else {}
        except Exception as exc:
            return _unclassified(notes=[f"yfinance error: {exc!s}"])
        buckets: dict[str, Decimal] = {}
        for key, weight in raw.items():
            w = Decimal(str(weight))
            if w > 0:
                buckets[str(key)] = buckets.get(str(key), Decimal("0")) + w
        if not buckets:
            return _unclassified(notes=["yfinance sector data empty"])
        notes: list[str] = []
        buckets = _normalize_buckets(buckets, notes, preserve_excess=False)
        return DimensionBreakdown(
            buckets=buckets, source="provider", as_of=None, notes=notes
        )

    def _classify_geography(
        self,
        override: SecurityOverride | None,
        is_etf: bool,
        name: str,
        listing_exchange: str,
        symbol: str,
    ) -> DimensionBreakdown:
        if override:
            ob = _override_breakdown(override.geography, override.as_of, preserve_excess=False)
            if ob:
                return ob

        # Non-ETF: listing-exchange directly.
        if not is_etf:
            country = _EXCHANGE_COUNTRY.get(listing_exchange.upper())
            if country:
                return DimensionBreakdown(
                    buckets={country: Decimal("1.0")},
                    source="heuristic",
                    as_of=None,
                    notes=[f"from listing_exchange={listing_exchange}"],
                )
            return _unclassified(notes=[f"unknown listing_exchange={listing_exchange}"])

        # ETF geography fallback chain.
        if self.yfinance_disabled:
            return _unclassified(notes=["yfinance disabled"])

        # 1) Name-pattern.
        name_lower = (name or "").lower()
        for pattern, country in _NAME_PATTERNS:
            if pattern in name_lower:
                return DimensionBreakdown(
                    buckets={country: Decimal("1.0")},
                    source="heuristic",
                    as_of=None,
                    notes=[f"name matched '{pattern}'"],
                )

        # 2) Stock-exchange aggregation across top_holdings.
        try:
            fd = self._get_funds_data(symbol)
            th = getattr(fd, "top_holdings", None)
            raw = th.to_dict() if th is not None and hasattr(th, "to_dict") else {}
        except Exception as exc:
            return _unclassified(notes=[f"yfinance top_holdings error: {exc!s}"])

        weights = raw.get("Holding Percent") or {}
        exchanges = raw.get("exchange") or {}
        quote_types = raw.get("quoteType") or {}

        if weights:
            stock_count = sum(1 for s, qt in quote_types.items() if str(qt).upper() == "EQUITY")
            if quote_types and (stock_count / max(len(quote_types), 1)) >= 0.8:
                buckets: dict[str, Decimal] = {}
                for sub_symbol, pct in weights.items():
                    ex = (exchanges.get(sub_symbol) or "").upper()
                    country = _EXCHANGE_COUNTRY.get(ex)
                    if country:
                        buckets[country] = buckets.get(country, Decimal("0")) + Decimal(str(pct))
                # Renormalize so weights sum to 1.0 (top_holdings may be partial).
                total = sum(buckets.values())
                if total > 0:
                    buckets = {k: v / total for k, v in buckets.items()}
                    return DimensionBreakdown(
                        buckets=buckets,
                        source="heuristic",
                        as_of=None,
                        notes=[f"aggregated {len(weights)} top_holdings by exchange"],
                    )

        # 3) No fallback to listing_exchange for ETFs (spec §10).
        return _unclassified(notes=["ETF geography: no override/name/top_holdings match"])

    def _derive_currency(self, listing_currency: str) -> DimensionBreakdown:
        return DimensionBreakdown(
            buckets={listing_currency: Decimal("1.0")},
            source="heuristic",
            as_of=None,
            notes=[],
        )

    # ------------------------------------------------------------------
    # yfinance wrappers — kept thin so tests can mock yf.Ticker
    # ------------------------------------------------------------------

    def _get_funds_data(self, symbol: str):
        cached = self._cache_lookup(symbol, "funds_data")
        if cached is not None:
            return _DictAttr(cached)
        raw = yf.Ticker(symbol).funds_data
        snapshot = {
            "sector_weightings": dict(getattr(raw, "sector_weightings", {}) or {}),
            "asset_classes": dict(getattr(raw, "asset_classes", {}) or {}),
            "top_holdings": (
                raw.top_holdings.to_dict()
                if getattr(raw, "top_holdings", None) is not None
                and hasattr(raw.top_holdings, "to_dict")
                else {}
            ),
        }
        self._cache_store(symbol, "funds_data", snapshot)
        return _DictAttr(snapshot)

    def _get_info(self, symbol: str):
        cached = self._cache_lookup(symbol, "info")
        if cached is not None:
            return cached
        info = dict(yf.Ticker(symbol).info or {})
        self._cache_store(symbol, "info", info)
        return info

    def is_override_stale(self, as_of: date | None) -> bool:
        if as_of is None:
            return False
        return (date.today() - as_of).days > self.overrides.stale_after_days

    def clear_symbols(self, symbols: list[str]) -> None:
        """Evict the given symbols from the yfinance cache (spec §11).

        Called by ExposureState.refresh so that a user-initiated refresh
        actually re-fetches data for currently-held symbols instead of
        re-reading the same 24h-cached snapshot.
        """
        changed = False
        for symbol in symbols:
            if symbol in self._cache:
                del self._cache[symbol]
                changed = True
        if changed:
            self._save_cache()
