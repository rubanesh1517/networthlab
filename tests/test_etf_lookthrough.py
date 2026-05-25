"""Tests for the ETF look-through / classification service."""

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

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


# --- yfinance provider path (Task 5) -----------------------------------


@pytest.fixture
def fake_funds_data():
    """Synthetic yfinance.Ticker(symbol).funds_data shape."""

    class FakeFundsData:
        sector_weightings = {
            "technology": 0.5,
            "financials": 0.3,
            "healthcare": 0.2,
        }
        asset_classes = {
            "stockPosition": 0.99,
            "cashPosition": 0.01,
            "bondPosition": 0.0,
        }

        class FakeTopHoldings:
            def to_dict(self):
                return {}

        top_holdings = FakeTopHoldings()

    return FakeFundsData()


def test_etf_uses_provider_when_override_says_provider(mocker, fake_funds_data, tmp_path):
    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.funds_data = fake_funds_data

    bundle = make_override_bundle(
        "FAKE.TO",
        asset_class="provider",
        sector="provider",
        geography={"US": Decimal("1.0")},
        as_of=date(2026, 1, 1),
    )
    svc = EtfLookthroughService(
        overrides=bundle, complex_flags={}, cache_dir=tmp_path,
    )
    result = svc.classify(
        symbol="FAKE.TO",
        security_type="ETF",
        name="Fake ETF",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result.asset_class.source == "provider"
    assert result.asset_class.buckets["equity"] == Decimal("0.99")
    assert result.asset_class.buckets["cash"] == Decimal("0.01")
    assert result.sector.source == "provider"
    assert result.sector.buckets["technology"] == Decimal("0.5")
    assert result.geography.source == "override"


def test_etf_provider_missing_fields_yields_unclassified(mocker, tmp_path):
    class EmptyFundsData:
        sector_weightings = {}
        asset_classes = {}

        class FakeTopHoldings:
            def to_dict(self):
                return {}

        top_holdings = FakeTopHoldings()

    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.funds_data = EmptyFundsData()

    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
    )
    result = svc.classify(
        symbol="EMPTY.TO",
        security_type="ETF",
        name="Empty ETF",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result.asset_class.source == "unclassified"
    assert result.sector.source == "unclassified"
    assert result.asset_class.buckets == {}


def test_ws_exchange_traded_fund_security_type_is_treated_as_etf(mocker, tmp_path, fake_funds_data):
    """WS returns 'EXCHANGE_TRADED_FUND' (not 'ETF'). Must hit the ETF
    classification chain so sector lookups go to funds_data.sector_weightings,
    not info['sector'] (which doesn't exist for funds)."""
    mocker.patch(
        "networthlab.services.etf_lookthrough.yf.Ticker"
    ).return_value.funds_data = fake_funds_data
    bundle = make_override_bundle(
        "FAKE.TO",
        asset_class="provider",
        sector="provider",
        geography={"US": Decimal("1.0")},
    )
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)
    result = svc.classify(
        symbol="FAKE.TO",
        security_type="EXCHANGE_TRADED_FUND",  # WS shape, NOT "ETF"
        name="Fake Fund",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    # Got real provider data from funds_data, not unclassified.
    assert result.sector.source == "provider"
    assert result.sector.buckets["technology"] == Decimal("0.5")
    assert result.asset_class.source == "provider"
    assert result.asset_class.buckets["equity"] == Decimal("0.99")


def test_ws_cryptocurrency_security_type_classified_as_crypto(tmp_path):
    """WS returns 'CRYPTOCURRENCY' (not 'CRYPTO'). Must classify asset_class as crypto."""
    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
        yfinance_disabled=True,
    )
    result = svc.classify(
        symbol="BTC",
        security_type="CRYPTOCURRENCY",
        name="Bitcoin",
        listing_exchange="",
        listing_currency="CAD",
    )
    assert result.asset_class.source == "heuristic"
    assert result.asset_class.buckets == {"crypto": Decimal("1.0")}


def test_non_etf_asset_class_from_security_type(tmp_path):
    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
        yfinance_disabled=True,
    )
    result_eq = svc.classify(
        symbol="SHOP.TO",
        security_type="EQUITY",
        name="Shopify Inc",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result_eq.asset_class.source == "heuristic"
    assert result_eq.asset_class.buckets == {"equity": Decimal("1.0")}

    result_crypto = svc.classify(
        symbol="BTC",
        security_type="CRYPTO",
        name="Bitcoin",
        listing_exchange="WS_CRYPTO",
        listing_currency="CAD",
    )
    assert result_crypto.asset_class.buckets == {"crypto": Decimal("1.0")}


def test_non_etf_sector_from_yfinance_info(mocker, tmp_path):
    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.info = {"sector": "Technology", "quoteType": "EQUITY"}

    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
    )
    result = svc.classify(
        symbol="AAPL",
        security_type="EQUITY",
        name="Apple Inc",
        listing_exchange="NASDAQ",
        listing_currency="USD",
    )
    assert result.sector.source == "provider"
    assert result.sector.buckets == {"technology": Decimal("1.0")}


# --- Weight normalization (Task 5 follow-up) ---------------------------

def _make_fd(sector_weightings=None, asset_classes=None):
    class FD:
        pass

    FD.sector_weightings = sector_weightings or {}
    FD.asset_classes = asset_classes or {}

    class TH:
        def to_dict(self):
            return {}

    FD.top_holdings = TH()
    return FD()


def test_provider_sector_weights_below_1_renormalized(mocker, tmp_path):
    mocker.patch(
        "networthlab.services.etf_lookthrough.yf.Ticker"
    ).return_value.funds_data = _make_fd(
        sector_weightings={"tech": 0.5, "financials": 0.3, "healthcare": 0.17},
        asset_classes={"stockPosition": 1.0},
    )
    bundle = make_override_bundle(
        "DRIFT.TO",
        asset_class={"equity": Decimal("1.0")},
        sector="provider",
        geography={"US": Decimal("1.0")},
    )
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)
    result = svc.classify("DRIFT.TO", "ETF", "Drift", "TSX", "CAD")
    total = sum(result.sector.buckets.values())
    assert abs(total - Decimal("1")) < Decimal("0.0001")
    assert any("renormalized" in n for n in result.sector.notes)


def test_provider_sector_weights_above_1_renormalized(mocker, tmp_path):
    mocker.patch(
        "networthlab.services.etf_lookthrough.yf.Ticker"
    ).return_value.funds_data = _make_fd(
        sector_weightings={"tech": 0.6, "financials": 0.5},
        asset_classes={"stockPosition": 1.0},
    )
    bundle = make_override_bundle(
        "DRIFT2.TO",
        asset_class={"equity": Decimal("1.0")},
        sector="provider",
        geography={"US": Decimal("1.0")},
    )
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)
    result = svc.classify("DRIFT2.TO", "ETF", "Drift", "TSX", "CAD")
    total = sum(result.sector.buckets.values())
    assert abs(total - Decimal("1")) < Decimal("0.0001")


def test_provider_asset_class_sub_one_adds_other_remainder(mocker, tmp_path):
    mocker.patch(
        "networthlab.services.etf_lookthrough.yf.Ticker"
    ).return_value.funds_data = _make_fd(
        asset_classes={"stockPosition": 0.95},
    )
    bundle = make_override_bundle(
        "GAP.TO",
        asset_class="provider",
        sector={"tech": Decimal("1.0")},
        geography={"US": Decimal("1.0")},
    )
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)
    result = svc.classify("GAP.TO", "ETF", "Gap", "TSX", "CAD")
    assert result.asset_class.buckets["equity"] == Decimal("0.95")
    assert result.asset_class.buckets["other"] == Decimal("0.05")


def test_provider_asset_class_above_one_preserves_leverage(mocker, tmp_path):
    mocker.patch(
        "networthlab.services.etf_lookthrough.yf.Ticker"
    ).return_value.funds_data = _make_fd(
        asset_classes={"stockPosition": 1.24, "cashPosition": -0.24},
    )
    bundle = make_override_bundle(
        "LEV.TO",
        asset_class="provider",
        sector={"tech": Decimal("1.0")},
        geography={"US": Decimal("1.0")},
    )
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)
    result = svc.classify("LEV.TO", "ETF", "Lev", "TSX", "CAD")
    assert result.asset_class.buckets["equity"] == Decimal("1.24")
    assert "leverage preserved" in result.asset_class.notes[0]


# --- Geography fallbacks (Task 6) -------------------------------------


def test_geography_name_pattern_us(mocker, tmp_path):
    """ETF whose name contains 'S&P 500' classifies as US."""

    class EmptyFD:
        sector_weightings = {}
        asset_classes = {}

        class TH:
            def to_dict(self):
                return {}

        top_holdings = TH()

    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.funds_data = EmptyFD()

    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
    )
    result = svc.classify(
        symbol="SPY",
        security_type="ETF",
        name="SPDR S&P 500 ETF Trust",
        listing_exchange="NYSE",
        listing_currency="USD",
    )
    assert result.geography.source == "heuristic"
    assert result.geography.buckets == {"US": Decimal("1.0")}


def test_geography_stock_exchange_aggregation(mocker, tmp_path):
    """ETF whose top_holdings are predominantly NASDAQ-listed stocks => US."""

    class FD:
        sector_weightings = {}
        asset_classes = {}

        class TH:
            def to_dict(self):
                return {
                    "Holding Percent": {"NVDA": 0.10, "AAPL": 0.08, "MSFT": 0.07},
                    "exchange": {"NVDA": "NASDAQ", "AAPL": "NASDAQ", "MSFT": "NASDAQ"},
                    "quoteType": {"NVDA": "EQUITY", "AAPL": "EQUITY", "MSFT": "EQUITY"},
                }

        top_holdings = TH()

    mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker").return_value.funds_data = FD()

    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
    )
    result = svc.classify(
        symbol="MYSTERY_BASKET",
        security_type="ETF",
        name="Generic Quality Equity Basket",
        listing_exchange="NEO",
        listing_currency="USD",
    )
    assert result.geography.source == "heuristic"
    assert "US" in result.geography.buckets
    assert result.geography.buckets["US"] == Decimal("1.0")
    assert "top_holdings" in (result.geography.notes[0] if result.geography.notes else "")


def test_geography_non_etf_uses_listing_exchange(tmp_path):
    """For individual stocks, geography is derived directly from listing_exchange."""
    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
        yfinance_disabled=True,
    )
    shop = svc.classify(
        symbol="SHOP.TO",
        security_type="EQUITY",
        name="Shopify Inc",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert shop.geography.source == "heuristic"
    assert shop.geography.buckets == {"CAN": Decimal("1.0")}

    nvda = svc.classify(
        symbol="NVDA",
        security_type="EQUITY",
        name="NVIDIA",
        listing_exchange="NASDAQ",
        listing_currency="USD",
    )
    assert nvda.geography.buckets == {"US": Decimal("1.0")}


def test_etf_geography_listing_exchange_not_used_as_fallback(mocker, tmp_path):
    """Per spec §10: ETF with no override / no provider / no name match / no top_holdings
    must end up Unclassified — NOT default to its listing exchange country."""

    class FD:
        sector_weightings = {}
        asset_classes = {}

        class TH:
            def to_dict(self):
                return {}

        top_holdings = TH()

    mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker").return_value.funds_data = FD()

    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
    )
    result = svc.classify(
        symbol="MYSTERY.TO",
        security_type="ETF",
        name="Mystery Strategy Fund",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result.geography.source == "unclassified"
    assert result.geography.buckets == {}


# --- Cache + staleness (Task 7) ---------------------------------------


def test_cache_avoids_second_yfinance_call(mocker, tmp_path, fake_funds_data):
    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.funds_data = fake_funds_data

    bundle = make_override_bundle("FAKE.TO", asset_class="provider", sector="provider")
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)

    svc.classify("FAKE.TO", "ETF", "Fake ETF", "TSX", "CAD")
    svc.classify("FAKE.TO", "ETF", "Fake ETF", "TSX", "CAD")

    assert mock_ticker.call_count == 1


def test_cache_refetches_after_ttl_expires(mocker, tmp_path, fake_funds_data):
    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.funds_data = fake_funds_data

    import json
    from datetime import timedelta

    bundle = make_override_bundle("FAKE.TO", asset_class="provider", sector="provider")
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)
    svc.classify("FAKE.TO", "ETF", "Fake ETF", "TSX", "CAD")

    cache_file = tmp_path / "yfinance_cache.json"
    data = json.loads(cache_file.read_text())
    stale = datetime.now(timezone.utc) - timedelta(hours=25)
    data["FAKE.TO"]["fetched_at"] = stale.isoformat()
    cache_file.write_text(json.dumps(data))

    svc2 = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)
    svc2.classify("FAKE.TO", "ETF", "Fake ETF", "TSX", "CAD")
    assert mock_ticker.call_count == 2


def test_is_override_stale_helper(tmp_path):
    from datetime import date, timedelta

    bundle = SecurityOverrideBundle(stale_after_days=180, securities={})
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)

    fresh = date.today() - timedelta(days=30)
    old = date.today() - timedelta(days=200)
    assert svc.is_override_stale(fresh) is False
    assert svc.is_override_stale(old) is True
    assert svc.is_override_stale(None) is False


def test_clear_symbols_evicts_only_listed_symbols(mocker, tmp_path, fake_funds_data):
    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.funds_data = fake_funds_data

    bundle = SecurityOverrideBundle(
        stale_after_days=180,
        securities={
            "AAA.TO": SecurityOverride(
                asset_class="provider", sector="provider",
                geography={"US": Decimal("1.0")}, as_of=date(2026, 1, 1),
            ),
            "BBB.TO": SecurityOverride(
                asset_class="provider", sector="provider",
                geography={"US": Decimal("1.0")}, as_of=date(2026, 1, 1),
            ),
        },
    )
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)
    svc.classify("AAA.TO", "ETF", "AAA", "TSX", "CAD")
    svc.classify("BBB.TO", "ETF", "BBB", "TSX", "CAD")
    assert mock_ticker.call_count == 2

    svc.clear_symbols(["AAA.TO"])
    svc.classify("AAA.TO", "ETF", "AAA", "TSX", "CAD")
    svc.classify("BBB.TO", "ETF", "BBB", "TSX", "CAD")
    assert mock_ticker.call_count == 3
