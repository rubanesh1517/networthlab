"""Reflex state for the /exposure page."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import reflex as rx

from networthlab.services.etf_lookthrough import EtfLookthroughService
from networthlab.services.exposure import aggregate, build_account_groups
from networthlab.services.exposure_config import (
    load_account_groups,
    load_complex_securities,
    load_security_overrides,
)
from networthlab.services.wealthsimple import (
    PositionsResult,
    WealthsimpleAuthError,
    WealthsimpleService,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = REPO_ROOT / "config"
USER_CONFIG_DIR = Path.home() / ".networthlab"


class ExposureState(rx.State):
    is_loading: bool = False
    auth_required: bool = False
    error_message: str = ""
    warnings: list[str] = []

    total_value_cad: float = 0.0
    position_count: int = 0
    hhi_positions: int = 0
    top_holding_weight: float = 0.0
    cache_stale_minutes: int = 0
    last_updated: str = ""

    asset_class_data: list[dict[str, Any]] = []
    geography_data: list[dict[str, Any]] = []
    sector_data: list[dict[str, Any]] = []
    currency_data: list[dict[str, Any]] = []
    account_data: list[dict[str, Any]] = []
    concentration_data: list[dict[str, Any]] = []

    drilldown_open: bool = False
    drilldown_dimension: str = ""
    drilldown_bucket: str = ""
    drilldown_rows: list[dict[str, Any]] = []

    has_leverage: bool = False
    has_review_complex: bool = False

    asset_class_chips: list[str] = []
    geography_chips: list[str] = []
    sector_chips: list[str] = []
    currency_chips: list[str] = []
    concentration_chips: list[str] = []
    account_chips: list[str] = []

    is_empty: bool = False
    needs_account_config: bool = False

    drilldown_sort_key: str = "value_cad_num"
    drilldown_sort_desc: bool = True

    # Position-concentration drilldown: top-10 by default with a "show all" expander.
    show_all_concentration: bool = False
    total_concentration_count: int = 0

    _contributions: list[dict[str, Any]] = []

    async def on_load(self) -> None:
        """First page load — do not bust the yfinance cache."""
        await self._do_refresh(force_refresh=False)

    async def refresh(self) -> None:
        """Refresh button handler — bust cache for currently-held symbols (spec §11)."""
        await self._do_refresh(force_refresh=True)

    async def _do_refresh(self, force_refresh: bool) -> None:
        self.is_loading = True
        self.error_message = ""
        self.auth_required = False
        try:
            await self._refresh_impl(force_refresh=force_refresh)
        except WealthsimpleAuthError as exc:
            self.auth_required = True
            self.error_message = str(exc)
            self.is_empty = False
        except Exception as exc:  # noqa: BLE001
            self.error_message = f"Unexpected error: {exc!s}"
        finally:
            self.is_loading = False

    async def _refresh_impl(self, force_refresh: bool) -> None:
        ws_svc = WealthsimpleService(cache_dir=USER_CONFIG_DIR)
        result: PositionsResult = ws_svc.fetch_positions()

        config_warnings: list[str] = []

        try:
            bundle = load_security_overrides(
                CONFIG_DIR / "security_overrides.example.yaml",
                USER_CONFIG_DIR / "security_overrides.yaml",
            )
        except ValueError as exc:
            config_warnings.append(str(exc))
            try:
                bundle = load_security_overrides(
                    CONFIG_DIR / "security_overrides.example.yaml", None
                )
            except ValueError:
                from networthlab.services.exposure_config import SecurityOverrideBundle
                bundle = SecurityOverrideBundle(stale_after_days=180, securities={})

        try:
            complex_flags = load_complex_securities(CONFIG_DIR / "complex_securities.yaml")
        except ValueError as exc:
            config_warnings.append(str(exc))
            complex_flags = {}

        user_groups_path = USER_CONFIG_DIR / "account_groups.yaml"
        try:
            account_rules = load_account_groups(user_groups_path)
        except ValueError as exc:
            config_warnings.append(str(exc))
            account_rules = []

        self.needs_account_config = not account_rules
        if self.needs_account_config:
            config_warnings.append(
                f"No {user_groups_path} — all accounts shown as 'Other'. "
                f"Copy config/account_groups.example.yaml to {user_groups_path} and edit."
            )

        result.warnings.extend(config_warnings)

        lookup = EtfLookthroughService(
            overrides=bundle,
            complex_flags=complex_flags,
            cache_dir=USER_CONFIG_DIR,
        )
        if force_refresh:
            held_symbols = list({p.symbol for p in result.positions})
            lookup.clear_symbols(held_symbols)

        classifications = {
            p.symbol: lookup.classify(
                symbol=p.symbol,
                security_type=p.security_type,
                name=p.name,
                listing_exchange=p.listing_exchange,
                listing_currency=p.listing_currency,
            )
            for p in result.positions
        }

        account_groups = build_account_groups(result.positions, account_rules)
        snap = aggregate(result.positions, classifications, account_groups)

        self.total_value_cad = float(snap.kpis.total_value_cad)
        self.position_count = snap.kpis.position_count
        self.hhi_positions = snap.kpis.hhi_positions
        self.top_holding_weight = float(snap.kpis.top_holding_weight)
        self.cache_stale_minutes = result.stale_minutes
        self.last_updated = snap.kpis.as_of_snapshot.strftime("%H:%M UTC")
        self.warnings = list(snap.warnings) + list(result.warnings)

        self.asset_class_data = _aggregate_for_chart(snap.contributions, "asset_class")
        self.geography_data = _aggregate_for_chart(snap.contributions, "geography")
        self.sector_data = _aggregate_for_chart(snap.contributions, "sector")
        self.currency_data = _aggregate_for_chart(snap.contributions, "currency")
        self.account_data = _aggregate_for_chart(snap.contributions, "account")
        self.concentration_data = _aggregate_for_chart(
            snap.contributions, "concentration", top_n=10
        )

        self.has_leverage = any(cls.complexity_flag for cls in classifications.values())
        self.has_review_complex = any(
            cls.asset_class.buckets.get("equity", Decimal("1.0")) > Decimal("1.0")
            and cls.symbol not in complex_flags
            for cls in classifications.values()
        )

        def _dim_has_unclassified(dim: str) -> bool:
            return any(
                r.dimension == dim and r.source == "unclassified"
                for r in snap.contributions
            )

        def _dim_has_stale_override(dim_attr: str) -> bool:
            # Only meaningful for asset_class / sector / geography (override-sourced dims).
            return any(
                getattr(cls, dim_attr).source == "override"
                and lookup.is_override_stale(getattr(cls, dim_attr).as_of)
                for cls in classifications.values()
            )

        # Portfolio-wide signals that appear on every tile per spec §9.5:
        # Leverage / Review complex / Stale data are not dim-specific — they
        # apply to the whole snapshot, so each tile surfaces them too.
        portfolio_chips: list[str] = []
        if self.has_leverage:
            portfolio_chips.append("leverage")
        if self.has_review_complex:
            portfolio_chips.append("review_complex")
        if result.stale_minutes > 60:
            portfolio_chips.append("stale_cache")

        def _build_chips(dim: str, dim_attr: str | None = None) -> list[str]:
            chips: list[str] = []
            if _dim_has_unclassified(dim):
                chips.append("unclassified")
            if dim_attr and _dim_has_stale_override(dim_attr):
                chips.append("stale_override")
            chips.extend(portfolio_chips)
            return chips

        self.asset_class_chips = _build_chips("asset_class", "asset_class")
        self.geography_chips = _build_chips("geography", "geography")
        self.sector_chips = _build_chips("sector", "sector")
        self.currency_chips = _build_chips("currency")
        self.concentration_chips = _build_chips("concentration")
        # Account tile additionally flags missing user config.
        account_chips = _build_chips("account")
        if self.needs_account_config and "unclassified" not in account_chips:
            account_chips.insert(0, "unclassified")
        self.account_chips = account_chips

        self.is_empty = len(result.positions) == 0

        self._contributions = [
            {
                **r.model_dump(mode="json"),
                "value_cad_fmt": f"${float(r.value_cad):,.2f}",
                "weight_pct": f"{float(r.weight) * 100:.2f}%",
                "value_cad_num": float(r.value_cad),
                "weight_num": float(r.weight),
            }
            for r in snap.contributions
        ]

    @rx.var
    def formatted_total_value_cad(self) -> str:
        return f"${self.total_value_cad:,.2f}"

    @rx.var
    def formatted_top_holding_pct(self) -> str:
        return f"{self.top_holding_weight * 100:.2f}%"

    @rx.var
    def formatted_hhi(self) -> str:
        return f"{self.hhi_positions:,}"

    @rx.var
    def formatted_holdings(self) -> str:
        return f"{self.position_count}"

    @rx.var
    def concentration_label(self) -> str:
        return "concentrated" if self.hhi_positions > 2500 else "diversified"

    @rx.var
    def concentration_color(self) -> str:
        return "#f59e0b" if self.hhi_positions > 2500 else "#10b981"

    @rx.var
    def last_updated_subtitle(self) -> str:
        return f"Updated {self.last_updated}" if self.last_updated else "Not yet synced"

    def open_drilldown(self, dimension: str, bucket: str = "") -> None:
        self.drilldown_dimension = dimension
        self.drilldown_bucket = bucket
        self.drilldown_open = True
        self.show_all_concentration = False
        if bucket:
            rows = [
                r for r in self._contributions
                if r["dimension"] == dimension and r["bucket"] == bucket
            ]
        else:
            rows = [r for r in self._contributions if r["dimension"] == dimension]
        self.drilldown_sort_key = "value_cad_num"
        self.drilldown_sort_desc = True
        rows = sorted(rows, key=lambda r: r["value_cad_num"], reverse=True)
        # Spec §9.4: concentration tile defaults to top 10; "show all" expands.
        if dimension == "concentration" and not bucket:
            self.total_concentration_count = len(rows)
            rows = rows[:10]
        else:
            self.total_concentration_count = 0
        self.drilldown_rows = rows

    def expand_concentration(self) -> None:
        """Show-all button on the concentration drilldown — replaces the top-10
        slice with every concentration row, sorted by current sort key."""
        self.show_all_concentration = True
        rows = [
            r for r in self._contributions if r["dimension"] == "concentration"
        ]
        reverse = self.drilldown_sort_desc
        key = self.drilldown_sort_key
        self.drilldown_rows = sorted(
            rows, key=lambda r: r.get(key, ""), reverse=reverse
        )

    def close_drilldown(self) -> None:
        self.drilldown_open = False
        self.drilldown_rows = []

    def set_drilldown_open(self, is_open: bool) -> None:
        self.drilldown_open = is_open
        if not is_open:
            self.drilldown_rows = []

    def set_drilldown_sort(self, key: str) -> None:
        if self.drilldown_sort_key == key:
            self.drilldown_sort_desc = not self.drilldown_sort_desc
        else:
            self.drilldown_sort_key = key
            self.drilldown_sort_desc = True
        self.drilldown_rows = sorted(
            self.drilldown_rows,
            key=lambda r: r.get(key, ""),
            reverse=self.drilldown_sort_desc,
        )


def _aggregate_for_chart(
    contributions: list, dimension: str, top_n: int | None = None
) -> list[dict[str, Any]]:
    """Sum value_cad by bucket and sort by value descending."""
    sums: dict[str, Decimal] = {}
    for row in contributions:
        if row.dimension != dimension:
            continue
        sums[row.bucket] = sums.get(row.bucket, Decimal("0")) + row.value_cad
    items = sorted(
        ({"name": k, "value": float(v)} for k, v in sums.items()),
        key=lambda item: item["value"],
        reverse=True,
    )
    if top_n is not None:
        items = items[:top_n]
    return items
