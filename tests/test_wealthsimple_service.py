"""Tests for WealthsimpleService — session, fetch, normalization, fallback cache."""

import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from networthlab.services.wealthsimple import (
    PositionsResult,
    WealthsimpleAuthError,
    WealthsimpleService,
    _normalize_symbol,
)


def make_account(account_id: str, type_: str, nickname: str) -> dict:
    return {
        "id": account_id,
        "unifiedAccountType": type_,
        "nickname": nickname,
    }


def make_position(
    symbol: str,
    value_cad: str,
    account_id: str,
    security_type: str = "EQUITY",
    exchange: str = "TSX",
):
    return {
        "id": f"pos-{symbol}-{account_id}",
        "accounts": [{"id": account_id}],
        "quantity": "10",
        "averagePrice": {"amount": "10", "currency": "CAD"},
        "marketBookValue": {"amount": "100", "currency": "CAD"},
        "totalValue": {"amount": value_cad, "currency": "CAD"},
        "security": {
            "id": f"sec-{symbol}",
            "currency": "CAD",
            "securityType": security_type,
            "stock": {
                "symbol": symbol,
                "name": f"{symbol} Inc",
                "primaryExchange": exchange,
            },
        },
    }


def test_load_session_returns_none_when_keyring_empty(mocker):
    mocker.patch("networthlab.services.wealthsimple.keyring.get_password", return_value=None)
    assert WealthsimpleService.load_session() is None


def test_load_session_parses_keyring_json(mocker):
    mocker.patch(
        "networthlab.services.wealthsimple.keyring.get_password",
        return_value='{"access_token":"x","refresh_token":"y"}',
    )
    sess = WealthsimpleService.load_session()
    assert sess is not None
    assert sess.access_token == "x"


def test_fetch_positions_normalizes_and_writes_cache(mocker, tmp_path):
    mock_api = mocker.MagicMock()
    mock_api.get_accounts.return_value = [
        make_account("acct-1", "RRSP", "My RRSP"),
        make_account("acct-2", "TFSA", "My TFSA"),
    ]
    mock_api.get_token_info.return_value = {"identity_canonical_id": "identity-1"}
    mock_api.do_graphql_query.return_value = [
        {"node": make_position("VEQT.TO", "5000", "acct-1", "ETF", exchange="TSX")},
        {"node": make_position("AAPL", "1500", "acct-2", "EQUITY", exchange="NASDAQ")},
    ]
    mocker.patch(
        "networthlab.services.wealthsimple.WealthsimpleAPI.from_token",
        return_value=mock_api,
    )

    svc = WealthsimpleService(cache_dir=tmp_path)
    svc._session_override = mocker.MagicMock(access_token="x")

    result = svc.fetch_positions()
    assert isinstance(result, PositionsResult)
    assert result.stale_minutes == 0
    assert len(result.positions) == 2
    symbols = {p.symbol for p in result.positions}
    assert symbols == {"VEQT.TO", "AAPL"}
    veqt = next(p for p in result.positions if p.symbol == "VEQT.TO")
    assert veqt.market_value_cad == Decimal("5000")
    assert veqt.account_type == "RRSP"
    assert veqt.account_nickname == "My RRSP"

    cache_file = tmp_path / "positions_cache.json"
    assert cache_file.is_file()
    cached = json.loads(cache_file.read_text())
    assert cached["positions"][0]["symbol"] in {"VEQT.TO", "AAPL"}

    call = mock_api.do_graphql_query.call_args
    assert call.args[0] == "FetchIdentityPositions"
    assert call.args[1]["includeSecurity"] is True
    assert call.args[1]["includeAccountData"] is True


def test_fetch_positions_must_request_include_security_flag(mocker, tmp_path):
    mock_api = mocker.MagicMock()
    mock_api.get_accounts.return_value = []
    mock_api.get_token_info.return_value = {"identity_canonical_id": "id"}
    mock_api.do_graphql_query.return_value = []
    mocker.patch(
        "networthlab.services.wealthsimple.WealthsimpleAPI.from_token",
        return_value=mock_api,
    )
    svc = WealthsimpleService(cache_dir=tmp_path)
    svc._session_override = mocker.MagicMock(access_token="x")
    svc.fetch_positions()
    assert not mock_api.get_identity_positions.called
    assert mock_api.do_graphql_query.called


def test_fetch_positions_paginates_and_disables_aggregation(mocker, tmp_path):
    mock_api = mocker.MagicMock()
    mock_api.get_accounts.return_value = []
    mock_api.get_token_info.return_value = {"identity_canonical_id": "id"}
    mock_api.do_graphql_query.return_value = []
    mocker.patch(
        "networthlab.services.wealthsimple.WealthsimpleAPI.from_token",
        return_value=mock_api,
    )
    svc = WealthsimpleService(cache_dir=tmp_path)
    svc._session_override = mocker.MagicMock(access_token="x")
    svc.fetch_positions()
    call = mock_api.do_graphql_query.call_args
    variables = call.args[1]
    assert variables["first"] == 100
    assert variables["aggregated"] is False
    # NOTE: WS rejects currencyOverride='CAD' as UNPROCESSABLE_ENTITY, so we
    # don't pass it here — USD→CAD conversion happens client-side via
    # _to_cad() using a yfinance-fetched spot rate.
    assert "currencyOverride" not in variables
    assert call.kwargs.get("load_all_pages") is True


def test_normalize_positions_converts_usd_totalvalue_to_cad():
    """USD totalValue gets multiplied by the FX rate; CAD passes through."""
    from networthlab.services.wealthsimple import WealthsimpleService

    accounts = [
        {"id": "a1", "unifiedAccountType": "RRSP", "nickname": "R"},
    ]
    edges = [
        # USD position: 100 USD * 1.37 = 137.00 CAD
        {"node": {
            "accounts": [{"id": "a1"}],
            "quantity": "1",
            "totalValue": {"amount": "100", "currency": "USD"},
            "marketBookValue": {"amount": "80", "currency": "USD"},
            "security": {
                "id": "sec-aapl", "currency": "USD", "securityType": "EQUITY",
                "stock": {"symbol": "AAPL", "name": "Apple",
                          "primaryExchange": "NASDAQ"},
            },
        }},
        # CAD position: 200 CAD stays 200 CAD
        {"node": {
            "accounts": [{"id": "a1"}],
            "quantity": "2",
            "totalValue": {"amount": "200", "currency": "CAD"},
            "marketBookValue": {"amount": "180", "currency": "CAD"},
            "security": {
                "id": "sec-veqt", "currency": "CAD", "securityType": "ETF",
                "stock": {"symbol": "VEQT", "name": "Vanguard",
                          "primaryExchange": "TSX"},
            },
        }},
    ]
    positions = WealthsimpleService._normalize_positions(
        edges, accounts, usd_cad_rate=Decimal("1.37")
    )
    by_symbol = {p.symbol: p for p in positions}
    assert by_symbol["AAPL"].market_value_cad == Decimal("137.00")
    assert by_symbol["AAPL"].book_value_cad == Decimal("109.60")
    assert by_symbol["VEQT.TO"].market_value_cad == Decimal("200")
    assert by_symbol["VEQT.TO"].book_value_cad == Decimal("180")


def test_normalize_cash_synthesizes_one_position_per_account():
    """Each account's CAD + USD cash sleeve becomes a single CAD-valued
    Position with symbol='CASH'. Negative balances (margin debt) pass
    through; accounts with zero cash are skipped."""
    from networthlab.services.wealthsimple import WealthsimpleService

    accounts = [
        {"id": "tfsa-1", "unifiedAccountType": "SELF_DIRECTED_TFSA", "nickname": "T"},
        {"id": "rrsp-1", "unifiedAccountType": "SELF_DIRECTED_RRSP", "nickname": "R"},
        {"id": "empty-1", "unifiedAccountType": "CASH", "nickname": "E"},
        {
            "id": "margin-1",
            "unifiedAccountType": "SELF_DIRECTED_NON_REGISTERED_MARGIN",
            "nickname": "M",
        },
    ]
    cash_by_account = {
        "tfsa-1": {"sec-c-cad": "13.71", "sec-c-usd": "1409.48"},   # 13.71 + 1409.48*1.37
        "rrsp-1": {"sec-c-cad": "1131.36", "sec-c-usd": "13456.82"},
        "empty-1": {},                                                # skipped
        "margin-1": {"sec-c-usd": "-21214.27"},                       # negative margin debt
    }
    positions = WealthsimpleService._normalize_cash(
        accounts, cash_by_account, usd_cad_rate=Decimal("1.37")
    )
    by_acct = {p.account_id: p for p in positions}
    assert len(positions) == 3  # empty-1 skipped
    expected_tfsa = Decimal("13.71") + Decimal("1409.48") * Decimal("1.37")
    assert by_acct["tfsa-1"].market_value_cad == expected_tfsa
    assert by_acct["rrsp-1"].symbol == "CASH"
    assert by_acct["rrsp-1"].security_type == "CASH"
    # Negative margin balance flows through as debt:
    assert by_acct["margin-1"].market_value_cad == Decimal("-21214.27") * Decimal("1.37")


def test_fetch_positions_dedupes_account_symbol_pairs(mocker, tmp_path):
    """If WS returns the same (account, symbol) more than once (which
    happens when aggregated=False still groups account ids per security),
    the second occurrence must be discarded — not appended as a duplicate
    Position that would double-count value into the per-account totals."""
    mock_api = mocker.MagicMock()
    mock_api.get_accounts.return_value = [make_account("a1", "RRSP", "R")]
    mock_api.get_token_info.return_value = {"identity_canonical_id": "id"}
    pos = make_position("AMD", "2554.38", "a1", "EQUITY", exchange="NASDAQ")
    mock_api.do_graphql_query.return_value = [
        {"node": pos},
        {"node": pos},  # duplicate edge for the same (account, symbol)
    ]
    mocker.patch(
        "networthlab.services.wealthsimple.WealthsimpleAPI.from_token",
        return_value=mock_api,
    )
    svc = WealthsimpleService(cache_dir=tmp_path)
    svc._session_override = mocker.MagicMock(access_token="x")
    result = svc.fetch_positions()
    assert len(result.positions) == 1
    assert result.positions[0].symbol == "AMD"
    assert result.positions[0].market_value_cad == Decimal("2554.38")


def test_fetch_positions_raises_auth_missing_on_manual_login_required(mocker, tmp_path):
    from ws_api.exceptions import ManualLoginRequired

    mocker.patch(
        "networthlab.services.wealthsimple.WealthsimpleAPI.from_token",
        side_effect=ManualLoginRequired("refresh token rejected"),
    )
    svc = WealthsimpleService(cache_dir=tmp_path)
    svc._session_override = mocker.MagicMock(access_token="x")
    with pytest.raises(WealthsimpleAuthError) as exc_info:
        svc.fetch_positions()
    assert "lunchsimple login" in str(exc_info.value)


def test_fetch_positions_raises_auth_missing_on_login_failed(mocker, tmp_path):
    from ws_api.exceptions import LoginFailedException

    mocker.patch(
        "networthlab.services.wealthsimple.WealthsimpleAPI.from_token",
        side_effect=LoginFailedException("invalid creds"),
    )
    svc = WealthsimpleService(cache_dir=tmp_path)
    svc._session_override = mocker.MagicMock(access_token="x")
    with pytest.raises(WealthsimpleAuthError):
        svc.fetch_positions()


def test_fetch_positions_falls_back_to_cache_on_api_failure(mocker, tmp_path):
    cache_file = tmp_path / "positions_cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "positions": [
                    {
                        "account_id": "acct-1",
                        "account_type": "RRSP",
                        "account_nickname": "My RRSP",
                        "symbol": "VEQT.TO",
                        "name": "Vanguard All-Equity",
                        "security_type": "ETF",
                        "listing_currency": "CAD",
                        "listing_exchange": "TSX",
                        "quantity": "10",
                        "market_value_cad": "5000",
                        "book_value_cad": "4800",
                    }
                ],
            }
        )
    )

    mocker.patch(
        "networthlab.services.wealthsimple.WealthsimpleAPI.from_token",
        side_effect=RuntimeError("network down"),
    )

    svc = WealthsimpleService(cache_dir=tmp_path)
    svc._session_override = mocker.MagicMock(access_token="x")
    result = svc.fetch_positions()
    assert result.stale_minutes >= 0
    assert len(result.positions) == 1
    assert result.warnings


def test_normalize_symbol_adds_tsx_suffix():
    """Wealthsimple returns 'VEQT'; yfinance + overrides need 'VEQT.TO'."""
    assert _normalize_symbol("VEQT", "TSX") == "VEQT.TO"
    assert _normalize_symbol("XEQT", "TSX") == "XEQT.TO"
    assert _normalize_symbol("VFV", "TSX") == "VFV.TO"


def test_normalize_symbol_leaves_us_symbols_alone():
    """NASDAQ/NYSE listings need no suffix in yfinance."""
    assert _normalize_symbol("AAPL", "NASDAQ") == "AAPL"
    assert _normalize_symbol("VOO", "NYSE") == "VOO"
    assert _normalize_symbol("QQQM", "NMS") == "QQQM"


def test_normalize_symbol_passthrough_when_already_suffixed():
    """If WS already gave us a suffix (e.g. 'QQC.F'), don't double-suffix."""
    assert _normalize_symbol("QQC.F", "TSX") == "QQC.F"
    assert _normalize_symbol("VEQT.TO", "TSX") == "VEQT.TO"


def test_normalize_symbol_handles_other_exchanges():
    assert _normalize_symbol("HXT", "TSXV") == "HXT.V"
    assert _normalize_symbol("XYZ", "NEO") == "XYZ.NE"


def test_normalize_symbol_unknown_exchange_passes_through():
    assert _normalize_symbol("MYSTERY", "WS_INTERNAL") == "MYSTERY"
    assert _normalize_symbol("BARE", "") == "BARE"


def test_fetch_positions_normalizes_symbol_via_exchange(mocker, tmp_path):
    """End-to-end: a bare WS symbol on TSX should land in Position.symbol as
    'VEQT.TO' so override lookups + yfinance fetches both hit."""
    mock_api = mocker.MagicMock()
    mock_api.get_accounts.return_value = [make_account("acct-1", "RRSP", "My RRSP")]
    mock_api.get_token_info.return_value = {"identity_canonical_id": "id"}
    mock_api.do_graphql_query.return_value = [
        {"node": make_position("VEQT", "5000", "acct-1", "ETF")},
    ]
    mocker.patch(
        "networthlab.services.wealthsimple.WealthsimpleAPI.from_token",
        return_value=mock_api,
    )
    svc = WealthsimpleService(cache_dir=tmp_path)
    svc._session_override = mocker.MagicMock(access_token="x")

    result = svc.fetch_positions()
    assert len(result.positions) == 1
    assert result.positions[0].symbol == "VEQT.TO"


def test_fetch_positions_raises_when_no_session(mocker, tmp_path):
    mocker.patch("networthlab.services.wealthsimple.keyring.get_password", return_value=None)
    svc = WealthsimpleService(cache_dir=tmp_path)
    with pytest.raises(WealthsimpleAuthError):
        svc.fetch_positions()
