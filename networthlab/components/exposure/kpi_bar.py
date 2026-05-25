"""Top-of-page KPI bar — uses the project's `stat_card` design idiom."""

import reflex as rx

from ...components.cards.stat_card import stat_card
from ...state.exposure_state import ExposureState


def kpi_bar() -> rx.Component:
    return rx.vstack(
        rx.flex(
            stat_card(
                title="Total Value",
                value=ExposureState.formatted_total_value_cad,
                icon="wallet",
                color="purple",
                subtitle="CAD",
            ),
            stat_card(
                title="Holdings",
                value=ExposureState.formatted_holdings,
                icon="layers",
                color="blue",
                subtitle="positions",
            ),
            stat_card(
                title="Concentration (HHI)",
                value=ExposureState.formatted_hhi,
                icon="git-branch",
                color="green",
                subtitle=ExposureState.concentration_label,
            ),
            stat_card(
                title="Top Holding",
                value=ExposureState.formatted_top_holding_pct,
                icon="trending-up",
                color="amber",
                subtitle="of portfolio",
            ),
            gap="14px",
            wrap="wrap",
            width="100%",
        ),
        rx.hstack(
            rx.spacer(),
            rx.button(
                rx.icon("refresh-cw", size=14),
                "Refresh",
                on_click=ExposureState.refresh,
                loading=ExposureState.is_loading,
                size="2",
                variant="soft",
                color_scheme="violet",
            ),
            width="100%",
            margin_top="6px",
        ),
        spacing="2",
        width="100%",
        margin_bottom="22px",
    )
