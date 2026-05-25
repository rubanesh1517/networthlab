"""Settings page."""

import reflex as rx

from ..components.layout.page_wrapper import page_wrapper
from ..state.app_state import AppState
from ..styles.theme import COLORS


def settings_section(
    title: str,
    description: str,
    *children: rx.Component,
) -> rx.Component:
    """Settings section container."""
    return rx.box(
        rx.vstack(
            rx.vstack(
                rx.text(
                    title,
                    font_size="16px",
                    font_weight="600",
                    color=COLORS["text_primary"],
                ),
                rx.text(
                    description,
                    font_size="13px",
                    color=COLORS["text_secondary"],
                ),
                spacing="1",
                align="start",
                width="100%",
            ),
            rx.box(
                height="1px",
                width="100%",
                background=COLORS["glass_border"],
                margin_y="16px",
            ),
            *children,
            spacing="0",
            width="100%",
        ),
        padding="24px",
        border_radius="16px",
        background=COLORS["glass_bg"],
        backdrop_filter="blur(24px)",
        border=f"1px solid {COLORS['glass_border']}",
    )


def settings_row(
    label: str,
    description: str,
    control: rx.Component,
) -> rx.Component:
    """Settings row with label and control."""
    return rx.hstack(
        rx.vstack(
            rx.text(
                label,
                font_size="14px",
                font_weight="500",
                color=COLORS["text_primary"],
            ),
            rx.text(
                description,
                font_size="12px",
                color=COLORS["text_secondary"],
            ),
            spacing="0",
            align="start",
            flex="1",
        ),
        control,
        width="100%",
        align="center",
        padding_y="12px",
    )


def settings() -> rx.Component:
    """Settings page component."""
    return page_wrapper(
        "Settings",
        "Configure your NetWorthLab experience",
        # API Configuration
        settings_section(
            "Lunch Money Integration",
            "Connect to Lunch Money to import your financial accounts",
            rx.vstack(
                rx.text(
                    "API Access Token",
                    font_size="13px",
                    font_weight="500",
                    color=COLORS["text_secondary"],
                ),
                rx.hstack(
                    rx.input(
                        placeholder="Enter your Lunch Money API token",
                        value=AppState.access_token,
                        on_change=AppState.set_access_token,
                        type="password",
                        width="100%",
                        padding="12px 16px",
                        border_radius="10px",
                        background=COLORS["bg_tertiary"],
                        border=f"1px solid {COLORS['glass_border']}",
                        color=COLORS["text_primary"],
                        font_size="14px",
                        _focus={
                            "border": f"1px solid {COLORS['accent_primary']}",
                            "outline": "none",
                        },
                    ),
                    rx.button(
                        rx.cond(
                            AppState.is_loading,
                            rx.spinner(size="2"),
                            rx.text("Connect"),
                        ),
                        on_click=AppState.load_accounts,
                        padding="12px 24px",
                        border_radius="10px",
                        background=COLORS["accent_primary"],
                        color="white",
                        font_size="14px",
                        border="none",
                        cursor="pointer",
                        _hover={
                            "opacity": "0.9",
                        },
                        _disabled={
                            "opacity": "0.5",
                            "cursor": "not-allowed",
                        },
                        disabled=AppState.is_loading,
                    ),
                    spacing="3",
                    width="100%",
                ),
                # Connection status
                rx.cond(
                    AppState.is_connected,
                    rx.hstack(
                        rx.icon("circle-check", size=14, color=COLORS["accent_success"]),
                        rx.text(
                            f"Connected - {AppState.accounts.length()} accounts loaded",
                            font_size="13px",
                            color=COLORS["accent_success"],
                        ),
                        spacing="2",
                        padding_top="8px",
                    ),
                ),
                rx.cond(
                    AppState.error_message != "",
                    rx.hstack(
                        rx.icon("circle-alert", size=14, color=COLORS["accent_danger"]),
                        rx.text(
                            AppState.error_message,
                            font_size="13px",
                            color=COLORS["accent_danger"],
                        ),
                        spacing="2",
                        padding_top="8px",
                    ),
                ),
                # Help text
                rx.box(
                    rx.hstack(
                        rx.icon("info", size=14, color=COLORS["accent_secondary"]),
                        rx.vstack(
                            rx.text(
                                "How to get your API token:",
                                font_size="12px",
                                font_weight="500",
                                color=COLORS["text_primary"],
                            ),
                            rx.text(
                                "1. Log in to Lunch Money",
                                font_size="12px",
                                color=COLORS["text_secondary"],
                            ),
                            rx.text(
                                "2. Go to Settings > Developers",
                                font_size="12px",
                                color=COLORS["text_secondary"],
                            ),
                            rx.text(
                                "3. Create a new access token",
                                font_size="12px",
                                color=COLORS["text_secondary"],
                            ),
                            spacing="1",
                            align="start",
                        ),
                        spacing="3",
                        align="start",
                    ),
                    padding="16px",
                    border_radius="8px",
                    background="rgba(59, 130, 246, 0.1)",
                    margin_top="16px",
                ),
                spacing="2",
                width="100%",
                align="start",
            ),
        ),
        # Appearance
        settings_section(
            "Appearance",
            "Customize how NetWorthLab looks",
            settings_row(
                "Theme",
                "Choose between dark and light mode",
                rx.hstack(
                    rx.button(
                        rx.hstack(
                            rx.icon("moon", size=14),
                            rx.text("Dark"),
                            spacing="2",
                        ),
                        on_click=lambda: AppState.set_theme_mode("dark"),
                        padding="8px 16px",
                        border_radius="8px",
                        background=rx.cond(
                            AppState.theme_mode == "dark",
                            COLORS["accent_primary"],
                            "transparent",
                        ),
                        border=rx.cond(
                            AppState.theme_mode == "dark",
                            "none",
                            f"1px solid {COLORS['glass_border']}",
                        ),
                        color=rx.cond(
                            AppState.theme_mode == "dark",
                            "white",
                            COLORS["text_secondary"],
                        ),
                        font_size="13px",
                        cursor="pointer",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon("sun", size=14),
                            rx.text("Light"),
                            spacing="2",
                        ),
                        on_click=lambda: AppState.set_theme_mode("light"),
                        padding="8px 16px",
                        border_radius="8px",
                        background=rx.cond(
                            AppState.theme_mode == "light",
                            COLORS["accent_primary"],
                            "transparent",
                        ),
                        border=rx.cond(
                            AppState.theme_mode == "light",
                            "none",
                            f"1px solid {COLORS['glass_border']}",
                        ),
                        color=rx.cond(
                            AppState.theme_mode == "light",
                            "white",
                            COLORS["text_secondary"],
                        ),
                        font_size="13px",
                        cursor="pointer",
                    ),
                    spacing="2",
                ),
            ),
            settings_row(
                "Sidebar",
                "Toggle sidebar collapsed state",
                rx.switch(
                    checked=AppState.sidebar_collapsed,
                    on_change=lambda _: AppState.toggle_sidebar(),
                ),
            ),
        ),
        # About
        settings_section(
            "About",
            "Information about NetWorthLab",
            rx.vstack(
                rx.hstack(
                    rx.text("Version", font_size="13px", color=COLORS["text_secondary"]),
                    rx.spacer(),
                    rx.text("1.0.0", font_size="13px", color=COLORS["text_primary"]),
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Built with", font_size="13px", color=COLORS["text_secondary"]),
                    rx.spacer(),
                    rx.hstack(
                        rx.link(
                            "Reflex",
                            href="https://reflex.dev",
                            font_size="13px",
                            color=COLORS["accent_primary"],
                            is_external=True,
                        ),
                        rx.text("+", font_size="13px", color=COLORS["text_secondary"]),
                        rx.link(
                            "Lunch Money",
                            href="https://lunchmoney.app",
                            font_size="13px",
                            color=COLORS["accent_primary"],
                            is_external=True,
                        ),
                        spacing="2",
                    ),
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
        ),
        # Data Management
        settings_section(
            "Data Management",
            "Manage your locally stored data",
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text(
                            "Clear Local Data",
                            font_size="14px",
                            font_weight="500",
                            color=COLORS["text_primary"],
                        ),
                        rx.text(
                            "Remove all locally stored scenarios, loans, and settings",
                            font_size="12px",
                            color=COLORS["text_secondary"],
                        ),
                        spacing="0",
                        align="start",
                        flex="1",
                    ),
                    rx.button(
                        "Clear Data",
                        padding="8px 16px",
                        border_radius="8px",
                        background="transparent",
                        border=f"1px solid {COLORS['accent_danger']}",
                        color=COLORS["accent_danger"],
                        font_size="13px",
                        cursor="pointer",
                        _hover={
                            "background": "rgba(239, 68, 68, 0.1)",
                        },
                    ),
                    width="100%",
                    align="center",
                ),
                spacing="3",
                width="100%",
            ),
        ),
    )
