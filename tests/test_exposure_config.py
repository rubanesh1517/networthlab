"""Tests for exposure config loaders."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from networthlab.services.exposure_config import (
    AccountGroupRule,
    ComplexSecurityFlag,
    SecurityOverride,
    load_account_groups,
    load_complex_securities,
    load_security_overrides,
    match_account_group,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


# ----- account_groups loader -----

def test_load_account_groups_returns_rules_in_order(tmp_path):
    f = tmp_path / "account_groups.yaml"
    f.write_text(
        """
groups:
  - name: "Custom"
    match: { nicknames: ["*Pattern*"] }
    icon: "home"
  - name: Retirement
    match: { types: [RRSP] }
    icon: "piggy-bank"
""".strip()
    )
    rules = load_account_groups(f)
    assert len(rules) == 2
    assert rules[0].name == "Custom"
    assert rules[1].name == "Retirement"


def test_load_account_groups_missing_file_returns_empty():
    rules = load_account_groups(Path("/nonexistent/path.yaml"))
    assert rules == []


def test_match_account_group_nickname_pattern_wins_over_type():
    rules = [
        AccountGroupRule(name="Special", nicknames=["*Vault*"], types=[], icon="home"),
        AccountGroupRule(name="Retirement", nicknames=[], types=["RRSP"], icon="piggy-bank"),
    ]
    matched = match_account_group(
        nickname="My Vault RRSP",
        account_type="RRSP",
        rules=rules,
    )
    assert matched == "Special"


def test_match_account_group_type_fallback_when_no_nickname_matches():
    rules = [
        AccountGroupRule(name="Special", nicknames=["*Vault*"], types=[], icon="home"),
        AccountGroupRule(name="Retirement", nicknames=[], types=["RRSP"], icon="piggy-bank"),
    ]
    matched = match_account_group(
        nickname="Regular RRSP",
        account_type="RRSP",
        rules=rules,
    )
    assert matched == "Retirement"


def test_match_account_group_unmatched_returns_other():
    rules = [AccountGroupRule(name="Retirement", nicknames=[], types=["RRSP"], icon="piggy-bank")]
    matched = match_account_group(nickname="Some Account", account_type="TFSA", rules=rules)
    assert matched == "Other"


def test_match_account_group_empty_rules_returns_other():
    matched = match_account_group(nickname="Anything", account_type="RRSP", rules=[])
    assert matched == "Other"


# ----- security_overrides loader -----

def test_load_security_overrides_parses_buckets_and_as_of(tmp_path):
    f = tmp_path / "security_overrides.yaml"
    f.write_text(
        """
stale_after_days: 90
securities:
  VEQT.TO:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 0.5, CAN: 0.5 }
    as_of: "2026-01-15"
""".strip()
    )
    bundle = load_security_overrides(f, None)
    assert bundle.stale_after_days == 90
    veqt = bundle.securities["VEQT.TO"]
    assert veqt.asset_class == {"equity": Decimal("1.0")}
    assert veqt.sector == "provider"
    assert veqt.geography == {"US": Decimal("0.5"), "CAN": Decimal("0.5")}
    assert veqt.as_of == date(2026, 1, 15)


def test_load_security_overrides_user_file_overrides_example(tmp_path):
    example = tmp_path / "example.yaml"
    user = tmp_path / "user.yaml"
    example.write_text(
        """
stale_after_days: 180
securities:
  AAA:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-01-01"
  BBB:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-01-01"
""".strip()
    )
    user.write_text(
        """
stale_after_days: 90
securities:
  AAA:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { CAN: 1.0 }
    as_of: "2026-04-01"
""".strip()
    )
    bundle = load_security_overrides(example, user)
    assert bundle.stale_after_days == 90  # user file wins
    assert bundle.securities["AAA"].geography == {"CAN": Decimal("1.0")}
    assert bundle.securities["BBB"].geography == {"US": Decimal("1.0")}  # passthrough


def test_load_security_overrides_missing_user_file_is_fine(tmp_path):
    example = tmp_path / "example.yaml"
    example.write_text(
        """
stale_after_days: 180
securities:
  AAA:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-01-01"
""".strip()
    )
    bundle = load_security_overrides(example, tmp_path / "missing.yaml")
    assert bundle.stale_after_days == 180
    assert "AAA" in bundle.securities


# ----- complex_securities loader -----

def test_load_complex_securities_parses_flags(tmp_path):
    f = tmp_path / "complex.yaml"
    f.write_text(
        """
HYLD.TO: { flag: covered_call_leverage, leverage: 1.25 }
HXD.TO:  { flag: leveraged_inverse, leverage: -1.0 }
""".strip()
    )
    flags = load_complex_securities(f)
    assert flags["HYLD.TO"] == ComplexSecurityFlag(flag="covered_call_leverage", leverage=Decimal("1.25"))
    assert flags["HXD.TO"].leverage == Decimal("-1.0")


def test_load_complex_securities_missing_file_returns_empty():
    flags = load_complex_securities(Path("/nonexistent.yaml"))
    assert flags == {}


# ----- repo-bundled example files load ----

def test_committed_example_yamls_are_loadable():
    """Smoke test that the committed example files parse end-to-end."""
    bundle = load_security_overrides(REPO_ROOT / "config" / "security_overrides.example.yaml", None)
    assert bundle.stale_after_days == 180
    assert "VEQT.TO" in bundle.securities

    rules = load_account_groups(REPO_ROOT / "config" / "account_groups.example.yaml")
    assert any(r.name == "Retirement" for r in rules)

    flags = load_complex_securities(REPO_ROOT / "config" / "complex_securities.yaml")
    assert "HYLD.TO" in flags


# ----- YAML parse-error surfacing -----

def test_malformed_account_groups_raises_with_file_path(tmp_path):
    f = tmp_path / "bad_account_groups.yaml"
    f.write_text("groups:\n  - name: 'Unterminated\n")  # unterminated string
    with pytest.raises(ValueError) as exc_info:
        load_account_groups(f)
    assert str(f) in str(exc_info.value)


def test_malformed_security_overrides_raises_with_file_path(tmp_path):
    f = tmp_path / "bad_overrides.yaml"
    f.write_text("securities:\n  AAA: { unterminated\n")
    with pytest.raises(ValueError) as exc_info:
        load_security_overrides(f, None)
    assert str(f) in str(exc_info.value)


def test_malformed_complex_securities_raises_with_file_path(tmp_path):
    f = tmp_path / "bad_complex.yaml"
    f.write_text("AAA: { unterminated\n")
    with pytest.raises(ValueError) as exc_info:
        load_complex_securities(f)
    assert str(f) in str(exc_info.value)
