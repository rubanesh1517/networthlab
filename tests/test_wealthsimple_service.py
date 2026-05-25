"""Tests for WealthsimpleService — session, fetch, normalization, fallback cache."""

import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from networthlab.services.wealthsimple import (
    PositionsResult,
    WealthsimpleAuthError,
    WealthsimpleService,
)


def make_account(account_id: str, type_: str, nickname: str) -> dict:
    return {
        "id": account_id,
        "unifiedAccountType": type_,
        "nickname": nickname,
    }


def make_position(symbol: str, value_cad: str, account_id: str, security_type: str = "EQUITY"):
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
                "primaryExchange": "TSX",
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
        {"node": make_position("VEQT.TO", "5000", "acct-1", "ETF")},
        {"node": make_position("AAPL", "1500", "acct-2", "EQUITY")},
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
    assert call.kwargs.get("load_all_pages") is True


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


def test_fetch_positions_raises_when_no_session(mocker, tmp_path):
    mocker.patch("networthlab.services.wealthsimple.keyring.get_password", return_value=None)
    svc = WealthsimpleService(cache_dir=tmp_path)
    with pytest.raises(WealthsimpleAuthError):
        svc.fetch_positions()
