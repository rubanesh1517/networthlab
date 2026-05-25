"""Loaders for the exposure feature's YAML config files."""

from __future__ import annotations

import fnmatch
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal, Union

import yaml
from pydantic import BaseModel, ConfigDict


class AccountGroupRule(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    nicknames: list[str]        # glob patterns, possibly empty
    types: list[str]            # WS unifiedAccountType values, possibly empty
    icon: str


class SecurityOverride(BaseModel):
    model_config = ConfigDict(frozen=True)
    # Each dimension is either a buckets dict OR the literal string "provider".
    asset_class: Union[dict[str, Decimal], Literal["provider"]]
    sector: Union[dict[str, Decimal], Literal["provider"]]
    geography: Union[dict[str, Decimal], Literal["provider"]]
    as_of: date


class SecurityOverrideBundle(BaseModel):
    model_config = ConfigDict(frozen=True)
    stale_after_days: int
    securities: dict[str, SecurityOverride]


class ComplexSecurityFlag(BaseModel):
    model_config = ConfigDict(frozen=True)
    flag: str
    leverage: Decimal


# ----------------------------------------------------------------------
# account_groups
# ----------------------------------------------------------------------

def _safe_load(path: Path) -> object:
    """yaml.safe_load with a clear error message that includes the file path."""
    try:
        return yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error in {path}: {exc}") from exc


def load_account_groups(path: Path) -> list[AccountGroupRule]:
    """Parse an account_groups.yaml file. Missing file -> empty list (caller surfaces a banner)."""
    if not path.is_file():
        return []
    raw = _safe_load(path)
    if not raw or "groups" not in raw:
        return []
    rules: list[AccountGroupRule] = []
    for entry in raw["groups"]:
        match = entry.get("match") or {}
        rules.append(
            AccountGroupRule(
                name=entry["name"],
                nicknames=match.get("nicknames") or [],
                types=match.get("types") or [],
                icon=entry.get("icon", "wallet"),
            )
        )
    return rules


def match_account_group(
    nickname: str, account_type: str, rules: list[AccountGroupRule]
) -> str:
    """Apply rules top-to-bottom; nickname matches considered before type matches per rule."""
    for rule in rules:
        if any(fnmatch.fnmatchcase(nickname, pat) for pat in rule.nicknames):
            return rule.name
        if account_type in rule.types:
            return rule.name
    return "Other"


# ----------------------------------------------------------------------
# security_overrides (with example + user file merge)
# ----------------------------------------------------------------------

def _parse_dimension(
    raw: object,
) -> Union[dict[str, Decimal], Literal["provider"]]:
    if raw == "provider":
        return "provider"
    if isinstance(raw, dict):
        return {k: Decimal(str(v)) for k, v in raw.items()}
    raise ValueError(f"Unexpected dimension value: {raw!r}")


def _parse_override(raw: dict) -> SecurityOverride:
    return SecurityOverride(
        asset_class=_parse_dimension(raw["asset_class"]),
        sector=_parse_dimension(raw["sector"]),
        geography=_parse_dimension(raw["geography"]),
        as_of=raw["as_of"] if isinstance(raw["as_of"], date)
              else date.fromisoformat(str(raw["as_of"])),
    )


def _load_overrides_file(path: Path) -> tuple[int | None, dict[str, SecurityOverride]]:
    if not path or not path.is_file():
        return None, {}
    raw = _safe_load(path) or {}
    stale = raw.get("stale_after_days")
    securities_raw = raw.get("securities") or {}
    securities = {symbol: _parse_override(payload) for symbol, payload in securities_raw.items()}
    return stale, securities


def load_security_overrides(
    example_path: Path, user_path: Path | None
) -> SecurityOverrideBundle:
    """Merge committed example with optional user file. User file wins per-symbol."""
    example_stale, example_secs = _load_overrides_file(example_path)
    user_stale, user_secs = _load_overrides_file(user_path) if user_path else (None, {})

    merged_secs = {**example_secs, **user_secs}  # user wins per symbol
    stale = user_stale if user_stale is not None else (example_stale or 180)
    return SecurityOverrideBundle(stale_after_days=stale, securities=merged_secs)


# ----------------------------------------------------------------------
# complex_securities
# ----------------------------------------------------------------------

def load_complex_securities(path: Path) -> dict[str, ComplexSecurityFlag]:
    if not path.is_file():
        return {}
    raw = _safe_load(path) or {}
    return {
        symbol: ComplexSecurityFlag(
            flag=payload["flag"],
            leverage=Decimal(str(payload.get("leverage", 1))),
        )
        for symbol, payload in raw.items()
    }
