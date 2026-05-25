"""Data models for the market exposure dashboard."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

Dimension = Literal[
    "asset_class", "geography", "sector", "concentration", "currency", "account"
]
ClassificationSource = Literal[
    "override", "provider", "heuristic", "recursive", "unclassified"
]


class _Frozen(BaseModel):
    """Base for immutable, hashable-by-value models."""

    model_config = ConfigDict(frozen=True)


class Position(_Frozen):
    """A single security held in a Wealthsimple account, CAD-normalized."""

    account_id: str
    account_type: str           # WS unifiedAccountType (RRSP, TFSA, NON_REGISTERED, etc.)
    account_nickname: str
    symbol: str                 # e.g., "VEQT.TO"
    name: str
    security_type: str          # "ETF", "EQUITY", "CRYPTO", ...
    listing_currency: str       # "CAD" / "USD"
    listing_exchange: str       # "TSX" / "NASDAQ" / ...
    quantity: Decimal
    market_value_cad: Decimal
    book_value_cad: Decimal


class ClassificationComponent(_Frozen):
    """One underlying contribution to a classification.

    MVP: every non-recursive source produces a single self-referential component.
    Phase 2 recursive look-through emits one component per sub-fund.
    """

    symbol: str
    weight: Decimal             # fraction of parent position
    source: ClassificationSource


class DimensionBreakdown(_Frozen):
    """Per-dimension classification result for a single security."""

    buckets: dict[str, Decimal]   # bucket name -> weight; empty when source="unclassified"
    source: ClassificationSource
    as_of: date | None            # source="override" only; day-precision YAML input
    notes: list[str]              # diagnostic warnings ("weights summed to 0.97", etc.)


class SecurityClassification(_Frozen):
    """Full classification for one symbol, normalized to internal types."""

    symbol: str
    asset_class: DimensionBreakdown
    geography: DimensionBreakdown
    sector: DimensionBreakdown
    currency: DimensionBreakdown
    complexity_flag: str | None       # "covered_call_leverage", "leveraged_2x_long", etc.
    components: list[ClassificationComponent]  # phase 2 hook; in MVP always [self]
    fetched_at: datetime              # timezone-aware UTC; drives 24h cache TTL


class ContributionRow(_Frozen):
    """One row in the canonical aggregation output. Tiles group by (dimension, bucket)."""

    dimension: Dimension
    bucket: str
    source_position: str
    source_account_id: str
    underlying: str | None
    value_cad: Decimal
    weight: Decimal               # fraction of total portfolio, 0..1
    source: ClassificationSource


class Kpis(_Frozen):
    """Top-of-page summary numbers."""

    total_value_cad: Decimal
    position_count: int
    hhi_positions: int            # 0..10,000 — POSITION concentration; Phase 2 adds single-name HHI
    top_holding_weight: Decimal   # 0..1
    as_of_snapshot: datetime      # timezone-aware UTC
    cache_stale_minutes: int      # 0 when fresh; positive when rendering from positions_cache


class ExposureSnapshot(_Frozen):
    """Complete output of ExposureService.aggregate()."""

    kpis: Kpis
    contributions: list[ContributionRow]
    warnings: list[str]           # banner text
