"""Top-of-page KPI bar — 4 cards + refresh button."""

import reflex as rx

from ...state.exposure_state import ExposureState
from ...styles.theme import COLORS


def _kpi_card(label: str, value, subtitle: rx.Component | None = None) -> rx.Component:
    """`value` may be a Reflex Var or a plain string/int; Reflex renders either."""
    return rx.box(
        rx.text(
            label,
            font_size="11px",
            color=COLORS["text_secondary"],
            text_transform="uppercase",
        ),
        rx.text(value, font_size="22px", font_weight="700", color=COLORS["text_primary"]),
        subtitle if subtitle is not None else rx.fragment(),
        padding="14px 18px",
        background=COLORS["bg_secondary"],
        border_left=f"3px solid {COLORS['accent_primary']}",
        border_radius="8px",
        flex="1",
        min_width="160px",
    )


def kpi_bar() -> rx.Component:
    return rx.flex(
        _kpi_card("Total Value", ExposureState.formatted_total_value_cad),
        _kpi_card("Holdings", ExposureState.position_count),
        _kpi_card(
            "Concentration (HHI)",
            ExposureState.hhi_positions,
            subtitle=rx.text(
                ExposureState.concentration_label,
                font_size="11px",
                color=ExposureState.concentration_color,
            ),
        ),
        _kpi_card("Top Holding", ExposureState.formatted_top_holding_pct),
        rx.box(
            rx.button(
                rx.icon("refresh-cw", size=16),
                "Refresh",
                on_click=ExposureState.refresh,
                loading=ExposureState.is_loading,
            ),
            margin_left="auto",
            align_self="center",
        ),
        gap="12px",
        wrap="wrap",
        width="100%",
        margin_bottom="20px",
    )
