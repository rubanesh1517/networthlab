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

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Union

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

        asset_class = self._classify_asset_class(override, is_etf, security_type)
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
        self, override: SecurityOverride | None, is_etf: bool, security_type: str
    ) -> DimensionBreakdown:
        if override:
            ob = _override_breakdown(override.asset_class, override.as_of, preserve_excess=True)
            if ob:
                return ob
        return _unclassified(notes=["no override; provider not implemented in this task"])

    def _classify_sector(
        self, override: SecurityOverride | None, is_etf: bool, symbol: str
    ) -> DimensionBreakdown:
        if override:
            ob = _override_breakdown(override.sector, override.as_of, preserve_excess=False)
            if ob:
                return ob
        return _unclassified(notes=["no override; provider not implemented in this task"])

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
        return _unclassified(notes=["no override; geography fallbacks not implemented in this task"])

    def _derive_currency(self, listing_currency: str) -> DimensionBreakdown:
        return DimensionBreakdown(
            buckets={listing_currency: Decimal("1.0")},
            source="heuristic",
            as_of=None,
            notes=[],
        )
