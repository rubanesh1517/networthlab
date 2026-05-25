"""Pure aggregation logic — takes positions + classifications + grouping rules
and produces an ExposureSnapshot for the UI to render."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from networthlab.models import (
    ContributionRow,
    DimensionBreakdown,
    ExposureSnapshot,
    Kpis,
    Position,
    SecurityClassification,
)
from networthlab.services.exposure_config import (
    AccountGroupRule,
    match_account_group,
)


def build_account_groups(
    positions: list[Position], rules: list[AccountGroupRule]
) -> dict[str, str]:
    """For each distinct account_id in positions, resolve its group name."""
    out: dict[str, str] = {}
    seen_account_ids: set[str] = set()
    for p in positions:
        if p.account_id in seen_account_ids:
            continue
        seen_account_ids.add(p.account_id)
        out[p.account_id] = match_account_group(
            nickname=p.account_nickname,
            account_type=p.account_type,
            rules=rules,
        )
    return out


def _dimension_rows(
    dimension: str,
    breakdown: DimensionBreakdown,
    pos: Position,
    total_portfolio: Decimal,
) -> list[ContributionRow]:
    """Convert a dimension breakdown into contribution rows for a position."""
    if not breakdown.buckets:
        return [
            ContributionRow(
                dimension=dimension,
                bucket="Unclassified",
                source_position=pos.symbol,
                source_account_id=pos.account_id,
                underlying=None,
                value_cad=pos.market_value_cad,
                weight=(pos.market_value_cad / total_portfolio) if total_portfolio else Decimal("0"),
                source="unclassified",
            )
        ]
    rows: list[ContributionRow] = []
    for bucket, weight in breakdown.buckets.items():
        slice_value = pos.market_value_cad * weight
        rows.append(
            ContributionRow(
                dimension=dimension,
                bucket=bucket,
                source_position=pos.symbol,
                source_account_id=pos.account_id,
                underlying=None,
                value_cad=slice_value,
                weight=(slice_value / total_portfolio) if total_portfolio else Decimal("0"),
                source=breakdown.source,
            )
        )
    return rows


def _concentration_row(pos: Position, total: Decimal) -> ContributionRow:
    """Create a concentration row for a single position."""
    return ContributionRow(
        dimension="concentration",
        bucket=pos.symbol,
        source_position=pos.symbol,
        source_account_id=pos.account_id,
        underlying=None,
        value_cad=pos.market_value_cad,
        weight=(pos.market_value_cad / total) if total else Decimal("0"),
        source="provider",
    )


def _account_row(pos: Position, group_name: str, total: Decimal) -> ContributionRow:
    """Create an account grouping row for a position."""
    return ContributionRow(
        dimension="account",
        bucket=group_name,
        source_position=pos.symbol,
        source_account_id=pos.account_id,
        underlying=None,
        value_cad=pos.market_value_cad,
        weight=(pos.market_value_cad / total) if total else Decimal("0"),
        source="provider",
    )


def aggregate(
    positions: list[Position],
    classifications: dict[str, SecurityClassification],
    account_groups: dict[str, str],
) -> ExposureSnapshot:
    """Build the full snapshot. Pure function — no IO.

    Aggregates positions across all dimensions (asset_class, sector, geography,
    currency, account, concentration) and computes summary KPIs.
    """
    total = sum((p.market_value_cad for p in positions), start=Decimal("0"))
    contributions: list[ContributionRow] = []
    unclassified_dims: set[str] = set()

    for pos in positions:
        cls = classifications.get(pos.symbol)
        if cls is None:
            # Position with no classification gets marked as unclassified for non-currency dims
            unclassified_dims.update(["asset_class", "sector", "geography"])
            for dim in ("asset_class", "sector", "geography"):
                contributions.append(
                    ContributionRow(
                        dimension=dim,
                        bucket="Unclassified",
                        source_position=pos.symbol,
                        source_account_id=pos.account_id,
                        underlying=None,
                        value_cad=pos.market_value_cad,
                        weight=(pos.market_value_cad / total) if total else Decimal("0"),
                        source="unclassified",
                    )
                )
            # Currency falls back to listing currency
            contributions.append(
                ContributionRow(
                    dimension="currency",
                    bucket=pos.listing_currency,
                    source_position=pos.symbol,
                    source_account_id=pos.account_id,
                    underlying=None,
                    value_cad=pos.market_value_cad,
                    weight=(pos.market_value_cad / total) if total else Decimal("0"),
                    source="heuristic",
                )
            )
        else:
            # Process each dimension from the classification
            for dim_name, breakdown in (
                ("asset_class", cls.asset_class),
                ("sector", cls.sector),
                ("geography", cls.geography),
                ("currency", cls.currency),
            ):
                if breakdown.source == "unclassified":
                    unclassified_dims.add(dim_name)
                contributions.extend(_dimension_rows(dim_name, breakdown, pos, total))

        # Every position gets concentration and account rows
        contributions.append(_concentration_row(pos, total))
        contributions.append(
            _account_row(pos, account_groups.get(pos.account_id, "Other"), total)
        )

    # Calculate KPIs
    if positions:
        weights = [(p.market_value_cad / total) if total else Decimal("0") for p in positions]
        hhi = int(sum(((w * 100) ** 2) for w in weights))
        top_weight = max(weights)
    else:
        hhi = 0
        top_weight = Decimal("0")

    # Build warnings for unclassified dimensions
    warnings: list[str] = []
    if unclassified_dims:
        warnings.append(
            f"Unclassified positions in dimensions: {', '.join(sorted(unclassified_dims))}"
        )

    return ExposureSnapshot(
        kpis=Kpis(
            total_value_cad=total,
            position_count=len(positions),
            hhi_positions=hhi,
            top_holding_weight=top_weight,
            as_of_snapshot=datetime.now(timezone.utc),
            cache_stale_minutes=0,
        ),
        contributions=contributions,
        warnings=warnings,
    )
