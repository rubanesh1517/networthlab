"""Market exposure dashboard page — 2×3 grid + drill-down modal."""

import reflex as rx

from ..components.exposure.charts.concentration_bars import concentration_bars
from ..components.exposure.charts.exposure_donut import exposure_donut
from ..components.exposure.charts.sector_bars import sector_bars
from ..components.exposure.chips import (
    leverage_chip,
    review_complex_chip,
    stale_override_chip,
    unclassified_chip,
)
from ..components.exposure.chips import (
    stale_cache_chip as _stale_cache_chip,
)
from ..components.exposure.drilldown_modal import drilldown_modal
from ..components.exposure.exposure_tile import exposure_tile
from ..components.exposure.kpi_bar import kpi_bar
from ..components.layout.page_wrapper import page_wrapper
from ..state.exposure_state import ExposureState
from ..styles.theme import COLORS


def _auth_banner() -> rx.Component:
    return rx.box(
        rx.text(
            "No Wealthsimple session found in keyring. Run ",
            rx.code("lunchsimple login"),
            " to connect.",
            color=COLORS["text_primary"],
        ),
        padding="14px 18px",
        background="rgba(239, 68, 68, 0.08)",
        border_left="3px solid #ef4444",
        border_radius="8px",
        margin_bottom="20px",
    )


def _empty_state() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.icon("inbox", size=32, color=COLORS["text_secondary"]),
            rx.text(
                "No positions found in your Wealthsimple accounts.",
                color=COLORS["text_secondary"],
                font_size="14px",
            ),
            spacing="2",
        ),
        padding="48px",
        background=COLORS["bg_secondary"],
        border_radius="12px",
    )


def _chip_strip(chip_types) -> rx.Component:
    """Render per-tile chip list. Each chip type maps to a chip component.

    Spec §9.5: all warning chips appear inline on tiles, including the
    portfolio-wide signals (leverage / review_complex / stale_cache) — the
    state populates them into every tile's chip list when applicable.
    """
    return rx.hstack(
        rx.foreach(
            chip_types,
            lambda t: rx.match(
                t,
                ("unclassified", unclassified_chip()),
                ("leverage", leverage_chip()),
                ("review_complex", review_complex_chip()),
                ("stale_override", stale_override_chip()),
                ("stale_cache", _stale_cache_chip(ExposureState.cache_stale_minutes)),
                rx.fragment(),
            ),
        ),
        spacing="1",
    )


def _grid() -> rx.Component:
    tile_specs = [
        ("Asset Class", "asset_class",
         exposure_donut(ExposureState.asset_class_data, height=220),
         ExposureState.asset_class_chips),
        ("Geography", "geography",
         exposure_donut(ExposureState.geography_data, height=220),
         ExposureState.geography_chips),
        ("Sector", "sector",
         sector_bars(ExposureState.sector_data, height=240),
         ExposureState.sector_chips),
        ("Position Concentration", "concentration",
         concentration_bars(ExposureState.concentration_data, height=260),
         ExposureState.concentration_chips),
        ("Currency", "currency",
         exposure_donut(ExposureState.currency_data, height=220),
         ExposureState.currency_chips),
        ("Account Groups", "account",
         sector_bars(ExposureState.account_data, height=240),
         ExposureState.account_chips),
    ]
    return rx.grid(
        *[
            exposure_tile(
                title=title,
                chart=chart,
                chips=_chip_strip(chips),
                on_click=lambda dim=dim: ExposureState.open_drilldown(dim, ""),
            )
            for title, dim, chart, chips in tile_specs
        ],
        columns=rx.breakpoints(initial="1", sm="2", lg="3"),
        gap="14px",
        width="100%",
    )


def _warnings_banner() -> rx.Component:
    return rx.cond(
        ExposureState.warnings.length() > 0,
        rx.box(
            rx.vstack(
                rx.foreach(
                    ExposureState.warnings,
                    lambda w: rx.text(w, font_size="12px", color=COLORS["text_secondary"]),
                ),
                spacing="1",
                align="start",
            ),
            padding="10px 14px",
            background="rgba(245, 158, 11, 0.08)",
            border_left="3px solid #f59e0b",
            border_radius="6px",
            margin_bottom="12px",
        ),
        rx.fragment(),
    )


def _body() -> rx.Component:
    """Main body — only rendered when authenticated."""
    return rx.fragment(
        rx.cond(
            ExposureState.error_message != "",
            rx.box(
                rx.text(ExposureState.error_message, color="#f87171"),
                padding="10px",
                margin_bottom="12px",
            ),
            rx.fragment(),
        ),
        _warnings_banner(),
        rx.cond(
            ExposureState.is_empty,
            _empty_state(),
            rx.fragment(
                kpi_bar(),
                _grid(),
                drilldown_modal(),
            ),
        ),
    )


def exposure_page() -> rx.Component:
    # page_wrapper signature: (title, subtitle, *children).
    return page_wrapper(
        "Exposure",
        "Portfolio diversification by market exposure",
        rx.cond(
            ExposureState.auth_required,
            _auth_banner(),
            _body(),
        ),
    )
