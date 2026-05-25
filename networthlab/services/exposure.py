"""Pure aggregation logic — takes positions + classifications + grouping rules
and produces an ExposureSnapshot for the UI to render."""

from __future__ import annotations

from networthlab.models import Position
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
