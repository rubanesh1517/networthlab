"""Collapsible sidebar navigation component."""

import reflex as rx

from ...styles.theme import COLORS, GRADIENTS


def nav_item(
    icon: str,
    label: str,
    href: str,
    is_active: rx.Var[bool],
    collapsed: rx.Var[bool],
) -> rx.Component:
    """Navigation item with icon and optional label."""
    return rx.link(
        rx.hstack(
            rx.icon(
                icon,
                size=20,
                color=rx.cond(
                    is_active,
                    COLORS["accent_primary"],
                    COLORS["text_secondary"],
                ),
            ),
            rx.cond(
                ~collapsed,
                rx.text(
                    label,
                    font_size="14px",
                    font_weight=rx.cond(is_active, "500", "400"),
                    color=rx.cond(
                        is_active,
                        COLORS["text_primary"],
                        COLORS["text_secondary"],
                    ),
                ),
                rx.fragment(),
            ),
            spacing="3",
            align="center",
            width="100%",
            padding="12px 16px",
            border_radius="12px",
            background=rx.cond(
                is_active,
                "rgba(139, 92, 246, 0.15)",
                "transparent",
            ),
            _hover={
                "background": "rgba(139, 92, 246, 0.1)",
            },
            transition="all 0.2s ease",
        ),
        href=href,
        width="100%",
        style={"text_decoration": "none"},
    )


def sidebar() -> rx.Component:
    """Collapsible sidebar with navigation and theme toggle."""
    from ...state.app_state import AppState

    return rx.box(
        rx.vstack(
            # Logo section
            rx.hstack(
                rx.box(
                    rx.text(
                        "N",
                        font_size="20px",
                        font_weight="800",
                        style={
                            "background": GRADIENTS["primary"],
                            "background_clip": "text",
                            "-webkit-background-clip": "text",
                            "color": "transparent",
                        },
                    ),
                    width="36px",
                    height="36px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    border_radius="10px",
                    background="rgba(139, 92, 246, 0.2)",
                ),
                rx.cond(
                    ~AppState.sidebar_collapsed,
                    rx.text(
                        "NetWorthLab",
                        font_size="18px",
                        font_weight="700",
                        color=COLORS["text_primary"],
                    ),
                    rx.fragment(),
                ),
                spacing="3",
                align="center",
                padding="20px 16px",
            ),
            # Navigation items
            rx.vstack(
                nav_item(
                    "layout-dashboard",
                    "Dashboard",
                    "/",
                    is_active=AppState.current_page == "dashboard",
                    collapsed=AppState.sidebar_collapsed,
                ),
                nav_item(
                    "pie-chart",
                    "Exposure",
                    "/exposure",
                    is_active=AppState.current_page == "exposure",
                    collapsed=AppState.sidebar_collapsed,
                ),
                nav_item(
                    "flame",
                    "FIRE Calculator",
                    "/fire",
                    is_active=AppState.current_page == "fire",
                    collapsed=AppState.sidebar_collapsed,
                ),
                nav_item(
                    "credit-card",
                    "Loan Tracker",
                    "/loans",
                    is_active=AppState.current_page == "loans",
                    collapsed=AppState.sidebar_collapsed,
                ),
                nav_item(
                    "trending-up",
                    "Projections",
                    "/projections",
                    is_active=AppState.current_page == "projections",
                    collapsed=AppState.sidebar_collapsed,
                ),
                nav_item(
                    "settings",
                    "Settings",
                    "/settings",
                    is_active=AppState.current_page == "settings",
                    collapsed=AppState.sidebar_collapsed,
                ),
                spacing="1",
                width="100%",
                padding="0 8px",
            ),
            # Spacer
            rx.spacer(),
            # Bottom section: Theme toggle and collapse
            rx.vstack(
                # Theme toggle
                rx.hstack(
                    rx.icon(
                        rx.cond(
                            AppState.theme_mode == "dark",
                            "moon",
                            "sun",
                        ),
                        size=18,
                        color=COLORS["text_secondary"],
                    ),
                    rx.cond(
                        ~AppState.sidebar_collapsed,
                        rx.text(
                            rx.cond(
                                AppState.theme_mode == "dark",
                                "Dark Mode",
                                "Light Mode",
                            ),
                            font_size="13px",
                            color=COLORS["text_secondary"],
                        ),
                        rx.fragment(),
                    ),
                    spacing="3",
                    align="center",
                    padding="12px 16px",
                    border_radius="12px",
                    cursor="pointer",
                    _hover={
                        "background": "rgba(255, 255, 255, 0.05)",
                    },
                    on_click=AppState.toggle_theme,
                    width="100%",
                ),
                # Collapse toggle
                rx.hstack(
                    rx.icon(
                        rx.cond(
                            AppState.sidebar_collapsed,
                            "panel-left-open",
                            "panel-left-close",
                        ),
                        size=18,
                        color=COLORS["text_secondary"],
                    ),
                    rx.cond(
                        ~AppState.sidebar_collapsed,
                        rx.text(
                            "Collapse",
                            font_size="13px",
                            color=COLORS["text_secondary"],
                        ),
                        rx.fragment(),
                    ),
                    spacing="3",
                    align="center",
                    padding="12px 16px",
                    border_radius="12px",
                    cursor="pointer",
                    _hover={
                        "background": "rgba(255, 255, 255, 0.05)",
                    },
                    on_click=AppState.toggle_sidebar,
                    width="100%",
                ),
                spacing="1",
                width="100%",
                padding="0 8px 16px 8px",
            ),
            spacing="0",
            height="100vh",
            width="100%",
        ),
        width=rx.cond(AppState.sidebar_collapsed, "72px", "240px"),
        min_width=rx.cond(AppState.sidebar_collapsed, "72px", "240px"),
        height="100vh",
        background=COLORS["bg_secondary"],
        border_right=f"1px solid {COLORS['glass_border']}",
        transition="all 0.3s ease",
        position="fixed",
        left="0",
        top="0",
        z_index="100",
    )
