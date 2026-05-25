from datetime import datetime, timezone
from decimal import Decimal

from networthlab.models import (
    ClassificationComponent,
    DimensionBreakdown,
    Position,
    SecurityClassification,
)
from networthlab.services.exposure import aggregate


def make_position(
    symbol: str, account_id: str, account_type: str, value: str
) -> Position:
    return Position(
        account_id=account_id,
        account_type=account_type,
        account_nickname=f"nick-{account_id}",
        symbol=symbol,
        name=f"name-{symbol}",
        security_type="ETF" if symbol.endswith(".TO") else "EQUITY",
        listing_currency="CAD" if symbol.endswith(".TO") else "USD",
        listing_exchange="TSX" if symbol.endswith(".TO") else "NASDAQ",
        quantity=Decimal("1"),
        market_value_cad=Decimal(value),
        book_value_cad=Decimal(value),
    )


def full_breakdown(buckets: dict[str, str], source="provider") -> DimensionBreakdown:
    return DimensionBreakdown(
        buckets={k: Decimal(v) for k, v in buckets.items()},
        source=source,
        as_of=None,
        notes=[],
    )


def make_classification(symbol: str, asset, sector, geo, currency) -> SecurityClassification:
    return SecurityClassification(
        symbol=symbol,
        asset_class=full_breakdown(asset),
        sector=full_breakdown(sector),
        geography=full_breakdown(geo),
        currency=full_breakdown(currency, source="heuristic"),
        complexity_flag=None,
        components=[ClassificationComponent(symbol=symbol, weight=Decimal("1"), source="provider")],
        fetched_at=datetime.now(timezone.utc),
    )


def test_aggregate_produces_six_dimensions():
    positions = [make_position("VEQT.TO", "a1", "RRSP", "1000")]
    classifications = {
        "VEQT.TO": make_classification(
            "VEQT.TO",
            asset={"equity": "1.0"},
            sector={"tech": "0.5", "financials": "0.5"},
            geo={"US": "0.6", "CAN": "0.4"},
            currency={"CAD": "1.0"},
        )
    }
    snap = aggregate(positions, classifications, account_groups={"a1": "Retirement"})
    dims = {row.dimension for row in snap.contributions}
    assert dims == {"asset_class", "geography", "sector", "concentration", "currency", "account"}


def test_aggregate_weights_sum_to_one_per_dimension():
    positions = [
        make_position("VEQT.TO", "a1", "RRSP", "1000"),
        make_position("AAPL", "a2", "TFSA", "500"),
    ]
    classifications = {
        "VEQT.TO": make_classification(
            "VEQT.TO",
            asset={"equity": "1.0"},
            sector={"tech": "1.0"},
            geo={"US": "1.0"},
            currency={"CAD": "1.0"},
        ),
        "AAPL": make_classification(
            "AAPL",
            asset={"equity": "1.0"},
            sector={"tech": "1.0"},
            geo={"US": "1.0"},
            currency={"USD": "1.0"},
        ),
    }
    snap = aggregate(
        positions,
        classifications,
        account_groups={"a1": "Retirement", "a2": "Tax Free Saving"},
    )
    for dim in ["asset_class", "geography", "sector", "currency", "account", "concentration"]:
        total = sum(r.weight for r in snap.contributions if r.dimension == dim)
        assert abs(total - Decimal("1")) < Decimal("0.0001"), f"{dim} total = {total}"


def test_aggregate_hhi_position_concentration():
    """HHI = Σ (weight × 100)² over each position. Equal weights => low HHI."""
    positions = [
        make_position("A", "x", "RRSP", "1000"),
        make_position("B", "x", "RRSP", "1000"),
        make_position("C", "x", "RRSP", "1000"),
        make_position("D", "x", "RRSP", "1000"),
    ]
    classifications = {
        sym: make_classification(
            sym,
            asset={"equity": "1.0"},
            sector={"tech": "1.0"},
            geo={"US": "1.0"},
            currency={"CAD": "1.0"},
        )
        for sym in ["A", "B", "C", "D"]
    }
    snap = aggregate(positions, classifications, account_groups={"x": "Retirement"})
    assert snap.kpis.hhi_positions == 2500
    assert snap.kpis.position_count == 4
    assert snap.kpis.total_value_cad == Decimal("4000")
    assert snap.kpis.top_holding_weight == Decimal("0.25")


def test_aggregate_unclassified_positions_attributed_to_unknown_bucket():
    positions = [make_position("MYSTERY", "a1", "RRSP", "100")]
    classifications = {
        "MYSTERY": SecurityClassification(
            symbol="MYSTERY",
            asset_class=DimensionBreakdown(buckets={}, source="unclassified", as_of=None, notes=[]),
            sector=DimensionBreakdown(buckets={}, source="unclassified", as_of=None, notes=[]),
            geography=DimensionBreakdown(buckets={}, source="unclassified", as_of=None, notes=[]),
            currency=DimensionBreakdown(
                buckets={"CAD": Decimal("1.0")},
                source="heuristic",
                as_of=None,
                notes=[],
            ),
            complexity_flag=None,
            components=[
                ClassificationComponent(
                    symbol="MYSTERY", weight=Decimal("1"), source="unclassified"
                )
            ],
            fetched_at=datetime.now(timezone.utc),
        )
    }
    snap = aggregate(positions, classifications, account_groups={"a1": "Retirement"})
    asset_rows = [r for r in snap.contributions if r.dimension == "asset_class"]
    assert any(r.bucket == "Unclassified" for r in asset_rows)
    assert any(w in snap.warnings[0].lower() for w in ["unclassified"])


def test_aggregate_empty_portfolio_returns_zero_kpis():
    snap = aggregate(positions=[], classifications={}, account_groups={})
    assert snap.kpis.total_value_cad == Decimal("0")
    assert snap.kpis.position_count == 0
    assert snap.kpis.hhi_positions == 0
    assert snap.contributions == []
