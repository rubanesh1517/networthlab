"""Tests for the ETF look-through / classification service."""

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from networthlab.models import DimensionBreakdown
from networthlab.services.etf_lookthrough import EtfLookthroughService
from networthlab.services.exposure_config import (
    SecurityOverride,
    SecurityOverrideBundle,
)


def make_override_bundle(symbol: str, **dimensions) -> SecurityOverrideBundle:
    """Helper to build a 1-symbol bundle for unit tests."""
    default_dims = {
        "asset_class": {"equity": Decimal("1.0")},
        "sector": "provider",
        "geography": {"US": Decimal("1.0")},
        "as_of": date(2026, 1, 1),
    }
    default_dims.update(dimensions)
    return SecurityOverrideBundle(
        stale_after_days=180,
        securities={symbol: SecurityOverride(**default_dims)},
    )


def test_override_full_classification_no_yfinance_call():
    bundle = make_override_bundle(
        "VEQT.TO",
        asset_class={"equity": Decimal("1.0")},
        sector={"tech": Decimal("0.5"), "financials": Decimal("0.5")},
        geography={"US": Decimal("0.45"), "CAN": Decimal("0.30"), "INTL_DEV": Decimal("0.25")},
        as_of=date(2026, 1, 15),
    )
    svc = EtfLookthroughService(
        overrides=bundle,
        complex_flags={},
        cache_dir=Path("/tmp/nonexistent_cache_dir_for_test"),
    )
    result = svc.classify(
        symbol="VEQT.TO",
        security_type="ETF",
        name="Vanguard All-Equity ETF Portfolio",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result.asset_class.source == "override"
    assert result.asset_class.buckets == {"equity": Decimal("1.0")}
    assert result.sector.source == "override"
    assert result.sector.buckets["tech"] == Decimal("0.5")
    assert result.geography.source == "override"
    assert result.geography.as_of == date(2026, 1, 15)
    assert result.complexity_flag is None


def test_complexity_flag_populated_when_symbol_in_complex_dict():
    from networthlab.services.exposure_config import ComplexSecurityFlag

    bundle = make_override_bundle("HYLD.TO")
    flags = {"HYLD.TO": ComplexSecurityFlag(flag="covered_call_leverage", leverage=Decimal("1.25"))}
    svc = EtfLookthroughService(
        overrides=bundle,
        complex_flags=flags,
        cache_dir=Path("/tmp/nonexistent_cache_dir_for_test"),
    )
    result = svc.classify(
        symbol="HYLD.TO",
        security_type="ETF",
        name="Hamilton Enhanced US Covered Call",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result.complexity_flag == "covered_call_leverage"


def test_unknown_symbol_returns_all_unclassified_when_no_yfinance(tmp_path):
    """Without an override or yfinance hit, every dimension is unclassified."""
    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
        yfinance_disabled=True,  # explicit disable for unit-test isolation
    )
    result = svc.classify(
        symbol="MYSTERY.TO",
        security_type="ETF",
        name="Mystery ETF",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result.asset_class.source == "unclassified"
    assert result.asset_class.buckets == {}
    assert result.geography.source == "unclassified"


def test_currency_dimension_always_derived_from_listing_currency():
    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=Path("/tmp/nonexistent"),
        yfinance_disabled=True,
    )
    result = svc.classify(
        symbol="ANY.TO",
        security_type="EQUITY",
        name="Anything",
        listing_exchange="TSX",
        listing_currency="USD",
    )
    assert result.currency.source == "heuristic"
    assert result.currency.buckets == {"USD": Decimal("1.0")}


def test_override_geography_with_drift_is_renormalized(tmp_path):
    bundle = make_override_bundle(
        "DRIFT.TO",
        asset_class={"equity": Decimal("1.0")},
        sector="provider",
        geography={
            "US": Decimal("0.448"),
            "CAN": Decimal("0.306"),
            "INTL_DEV": Decimal("0.177"),
            "EM": Decimal("0.072"),
        },  # sums to 1.003
        as_of=date(2026, 1, 15),
    )
    svc = EtfLookthroughService(
        overrides=bundle,
        complex_flags={},
        cache_dir=tmp_path,
        yfinance_disabled=True,
    )
    result = svc.classify(
        symbol="DRIFT.TO",
        security_type="ETF",
        name="Drifty Fund",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    total = sum(result.geography.buckets.values())
    assert abs(total - Decimal("1")) < Decimal("0.0001")
    assert any("renormalized" in n for n in result.geography.notes)


def test_override_asset_class_under_one_adds_other_remainder(tmp_path):
    bundle = make_override_bundle(
        "GAP_OV.TO",
        asset_class={"equity": Decimal("0.95")},
        sector="provider",
        geography={"US": Decimal("1.0")},
        as_of=date(2026, 1, 1),
    )
    svc = EtfLookthroughService(
        overrides=bundle,
        complex_flags={},
        cache_dir=tmp_path,
        yfinance_disabled=True,
    )
    result = svc.classify(
        symbol="GAP_OV.TO",
        security_type="ETF",
        name="Gap",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result.asset_class.buckets["equity"] == Decimal("0.95")
    assert result.asset_class.buckets["other"] == Decimal("0.05")


def test_override_asset_class_above_one_preserves_leverage(tmp_path):
    bundle = make_override_bundle(
        "LEV_OV.TO",
        asset_class={"equity": Decimal("1.25")},
        sector="provider",
        geography={"US": Decimal("1.0")},
        as_of=date(2026, 1, 1),
    )
    svc = EtfLookthroughService(
        overrides=bundle,
        complex_flags={},
        cache_dir=tmp_path,
        yfinance_disabled=True,
    )
    result = svc.classify(
        symbol="LEV_OV.TO",
        security_type="ETF",
        name="Lev",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result.asset_class.buckets["equity"] == Decimal("1.25")
    assert "leverage preserved" in result.asset_class.notes[0]
