"""Tests for exposure data models."""

from datetime import date, datetime, timezone
from decimal import Decimal

from networthlab.models.exposure import (
    ClassificationComponent,
    ContributionRow,
    DimensionBreakdown,
    ExposureSnapshot,
    Kpis,
    Position,
    SecurityClassification,
)


def test_position_construction():
    pos = Position(
        account_id="acct-1",
        account_type="TFSA",
        account_nickname="My TFSA",
        symbol="VEQT.TO",
        name="Vanguard All-Equity ETF Portfolio",
        security_type="ETF",
        listing_currency="CAD",
        listing_exchange="TSX",
        quantity=Decimal("100"),
        market_value_cad=Decimal("3500.50"),
        book_value_cad=Decimal("3200.00"),
    )
    assert pos.symbol == "VEQT.TO"
    assert pos.market_value_cad == Decimal("3500.50")


def test_dimension_breakdown_unclassified_has_empty_buckets():
    d = DimensionBreakdown(buckets={}, source="unclassified", as_of=None, notes=["no data"])
    assert d.source == "unclassified"
    assert d.buckets == {}
    assert d.notes == ["no data"]


def test_dimension_breakdown_override_carries_as_of():
    d = DimensionBreakdown(
        buckets={"US": Decimal("1.0")},
        source="override",
        as_of=date(2026, 1, 15),
        notes=[],
    )
    assert d.as_of == date(2026, 1, 15)
    assert d.source == "override"


def test_classification_component_default_self_reference():
    c = ClassificationComponent(symbol="VEQT.TO", weight=Decimal("1.0"), source="override")
    assert c.weight == Decimal("1.0")


def test_security_classification_holds_four_dimensions():
    breakdown = DimensionBreakdown(buckets={}, source="unclassified", as_of=None, notes=[])
    sc = SecurityClassification(
        symbol="VEQT.TO",
        asset_class=breakdown,
        geography=breakdown,
        sector=breakdown,
        currency=breakdown,
        complexity_flag=None,
        components=[ClassificationComponent(symbol="VEQT.TO", weight=Decimal("1.0"), source="unclassified")],
        fetched_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
    )
    assert sc.symbol == "VEQT.TO"
    assert sc.complexity_flag is None


def test_contribution_row_weight_range():
    row = ContributionRow(
        dimension="sector",
        bucket="Technology",
        source_position="VEQT.TO",
        source_account_id="acct-1",
        underlying=None,
        value_cad=Decimal("710.00"),
        weight=Decimal("0.2033"),
        source="provider",
    )
    assert Decimal("0") <= row.weight <= Decimal("1")


def test_kpis_construction():
    kpis = Kpis(
        total_value_cad=Decimal("100000"),
        position_count=12,
        hhi_positions=1420,
        top_holding_weight=Decimal("0.21"),
        as_of_snapshot=datetime(2026, 5, 24, tzinfo=timezone.utc),
        cache_stale_minutes=0,
    )
    assert kpis.hhi_positions == 1420
    assert kpis.cache_stale_minutes == 0


def test_exposure_snapshot_assembles_full_shape():
    kpis = Kpis(
        total_value_cad=Decimal("0"),
        position_count=0,
        hhi_positions=0,
        top_holding_weight=Decimal("0"),
        as_of_snapshot=datetime(2026, 5, 24, tzinfo=timezone.utc),
        cache_stale_minutes=0,
    )
    snap = ExposureSnapshot(kpis=kpis, contributions=[], warnings=["empty portfolio"])
    assert snap.warnings == ["empty portfolio"]
    assert snap.contributions == []
