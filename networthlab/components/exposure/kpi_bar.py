"""Compact top-of-page KPI strip for the exposure dashboard."""

import reflex as rx

from ...state.exposure_state import ExposureState
from ...styles.theme import COLORS


def _kpi_item(
    title: str,
    value: str | rx.Var[str],
    icon: str,
    color: str,
    subtitle: str | rx.Var[str] = "",
) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon(icon, size=18, color=color),
            width="34px",
            height="34px",
            border_radius="9px",
            display="flex",
            align_items="center",
            justify_content="center",
            background=f"{color}1f",
            border=f"1px solid {color}33",
            flex_shrink="0",
        ),
        rx.vstack(
            rx.text(
                title,
                font_size="11px",
                font_weight="600",
                color=COLORS["text_secondary"],
                line_height="1",
            ),
            rx.text(
                value,
                font_size="20px",
                font_weight="700",
                color=COLORS["text_primary"],
                line_height="1.15",
                white_space="nowrap",
            ),
            rx.cond(
                subtitle != "",
                rx.text(
                    subtitle,
                    font_size="11px",
                    color=COLORS["text_secondary"],
                    line_height="1",
                ),
                rx.fragment(),
            ),
            spacing="1",
            align="start",
            min_width="0",
        ),
        spacing="3",
        align="center",
        min_width="0",
    )


def kpi_bar() -> rx.Component:
    return rx.box(
        rx.flex(
            rx.grid(
                _kpi_item(
                    "Total Value",
                    ExposureState.formatted_total_value_cad,
                    "wallet",
                    COLORS["accent_primary"],
                    "CAD",
                ),
                _kpi_item(
                    "Holdings",
                    ExposureState.formatted_holdings,
                    "layers",
                    COLORS["accent_secondary"],
                    "positions",
                ),
                _kpi_item(
                    "Position HHI",
                    ExposureState.formatted_hhi,
                    "git-branch",
                    ExposureState.concentration_color,
                    ExposureState.concentration_label,
                ),
                _kpi_item(
                    "Top Holding",
                    ExposureState.formatted_top_holding_pct,
                    "trending-up",
                    COLORS["accent_warning"],
                    "of portfolio",
                ),
                _kpi_item(
                    "ETF Allocation",
                    ExposureState.formatted_etf_share,
                    "pie-chart",
                    COLORS["accent_success"],
                    ExposureState.etf_breakdown_subtitle,
                ),
                columns=rx.breakpoints(initial="1", sm="2", md="3", lg="5"),
                gap="14px",
                flex="1",
                width="100%",
            ),
            rx.vstack(
                rx.button(
                    rx.icon("refresh-cw", size=14),
                    "Refresh",
                    on_click=ExposureState.refresh,
                    loading=ExposureState.is_loading,
                    size="2",
                    variant="soft",
                    color_scheme="violet",
                    width="100%",
                ),
                rx.text(
                    ExposureState.last_updated_subtitle,
                    font_size="11px",
                    color=COLORS["text_secondary"],
                    white_space="nowrap",
                ),
                spacing="2",
                align="end",
                min_width="126px",
            ),
            gap="18px",
            align="center",
            direction=rx.breakpoints(initial="column", md="row"),
            width="100%",
        ),
        padding="14px",
        background="rgba(26, 26, 36, 0.72)",
        border=f"1px solid {COLORS['glass_border']}",
        border_radius="12px",
        margin_bottom="18px",
    )
