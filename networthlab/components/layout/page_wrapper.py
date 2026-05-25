"""Page layout wrapper component."""

import reflex as rx
from ...styles.theme import COLORS


def page_wrapper(
    title: str,
    subtitle: str = "",
    *children: rx.Component,
) -> rx.Component:
    """Page layout wrapper with header and content area."""
    from ...state.app_state import AppState
    from .sidebar import sidebar

    return rx.box(
        # Sidebar
        sidebar(),
        # Main content area
        rx.box(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.vstack(
                        rx.heading(
                            title,
                            font_size="28px",
                            font_weight="700",
                            color=COLORS["text_primary"],
                        ),
                        rx.cond(
                            subtitle != "",
                            rx.text(
                                subtitle,
                                font_size="14px",
                                color=COLORS["text_secondary"],
                            ),
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.spacer(),
                    # Last updated indicator
                    rx.hstack(
                        rx.icon(
                            "clock",
                            size=14,
                            color=COLORS["text_secondary"],
                        ),
                        rx.text(
                            rx.cond(
                                AppState.last_updated != "",
                                f"Updated {AppState.last_updated}",
                                "Not yet synced",
                            ),
                            font_size="12px",
                            color=COLORS["text_secondary"],
                        ),
                        spacing="2",
                        align="center",
                        padding="8px 12px",
                        border_radius="8px",
                        background="rgba(255, 255, 255, 0.03)",
                    ),
                    width="100%",
                    align="center",
                    padding_bottom="24px",
                ),
                # Page content
                rx.box(
                    *children,
                    width="100%",
                ),
                spacing="0",
                width="100%",
                padding="32px",
                max_width="1400px",
            ),
            margin_left=rx.cond(AppState.sidebar_collapsed, "72px", "240px"),
            width=rx.cond(
                AppState.sidebar_collapsed,
                "calc(100vw - 72px)",
                "calc(100vw - 240px)",
            ),
            min_height="100vh",
            background=COLORS["bg_primary"],
            transition="all 0.3s ease",
        ),
        width="100%",
        min_height="100vh",
        background=COLORS["bg_primary"],
    )
