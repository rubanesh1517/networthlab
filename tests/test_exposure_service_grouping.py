
from networthlab.models import Position
from networthlab.services.exposure import build_account_groups
from networthlab.services.exposure_config import AccountGroupRule


def _pos(account_id: str, account_type: str, nickname: str) -> Position:
    from decimal import Decimal
    return Position(
        account_id=account_id,
        account_type=account_type,
        account_nickname=nickname,
        symbol="X",
        name="x",
        security_type="EQUITY",
        listing_currency="CAD",
        listing_exchange="TSX",
        quantity=Decimal("1"),
        market_value_cad=Decimal("1"),
        book_value_cad=Decimal("1"),
    )


def test_groups_distinct_account_ids_once():
    positions = [
        _pos("a1", "RRSP", "My RRSP"),
        _pos("a1", "RRSP", "My RRSP"),  # duplicate from same account
        _pos("a2", "TFSA", "TFSA Vault"),
    ]
    rules = [
        AccountGroupRule(name="Special", nicknames=["*Vault*"], types=[], icon=""),
        AccountGroupRule(name="Retirement", nicknames=[], types=["RRSP"], icon=""),
        AccountGroupRule(name="Tax Free Saving", nicknames=[], types=["TFSA"], icon=""),
    ]
    result = build_account_groups(positions, rules)
    assert result == {"a1": "Retirement", "a2": "Special"}


def test_unmatched_falls_to_other():
    positions = [_pos("a1", "NON_REGISTERED", "")]
    result = build_account_groups(positions, [])
    assert result == {"a1": "Other"}
