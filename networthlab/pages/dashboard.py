"""Dashboard page - main overview of financial data."""

import reflex as rx
from ..components.layout.page_wrapper import page_wrapper
from ..components.cards.stat_card import stat_card
from ..components.cards.chart_card import chart_card
from ..components.cards.account_card import account_card
from ..components.charts.net_worth_chart import net_worth_chart
from ..components.charts.allocation_chart import allocation_donut_simple
from ..state.app_state import AppState
from ..state.fire_state import FIREState
from ..styles.theme import COLORS


def dashboard() -> rx.Component:
    """Dashboard page component."""
    return page_wrapper(
        "Dashboard",
        "Your financial overview at a glance",
        # Stat cards row
        rx.hstack(
            stat_card(
                title="Net Worth",
                value=AppState.formatted_net_worth,
                trend=2.3,
                icon="wallet",
                color="purple",
            ),
            stat_card(
                title="Total Assets",
                value=AppState.formatted_assets,
                trend=1.8,
                icon="trending-up",
                color="green",
            ),
            stat_card(
                title="Total Liabilities",
                value=AppState.formatted_liabilities,
                trend=-0.5,
                icon="credit-card",
                color="red",
            ),
            stat_card(
                title="FIRE Progress",
                value=FIREState.formatted_fire_progress,
                icon="flame",
                color="amber",
            ),
            spacing="4",
            width="100%",
            flex_wrap="wrap",
        ),
        # Charts row
        rx.hstack(
            chart_card(
                "Net Worth Over Time",
                net_worth_chart(AppState.net_worth_chart_data),
                subtitle="Last 12 months",
            ),
            chart_card(
                "Asset Allocation",
                allocation_donut_simple(AppState.allocation_data),
                subtitle="By account type",
            ),
            spacing="4",
            width="100%",
            align="stretch",
        ),
        # Accounts section
        rx.vstack(
            rx.hstack(
                rx.text(
                    "Your Accounts",
                    font_size="18px",
                    font_weight="600",
                    color=COLORS["text_primary"],
                ),
                rx.spacer(),
                rx.button(
                    rx.hstack(
                        rx.icon("refresh-cw", size=14),
                        rx.text("Sync"),
                        spacing="2",
                    ),
                    on_click=AppState.load_accounts,
                    padding="8px 16px",
                    border_radius="8px",
                    background="rgba(139, 92, 246, 0.15)",
                    color=COLORS["accent_primary"],
                    font_size="13px",
                    border="none",
                    cursor="pointer",
                    _hover={
                        "background": "rgba(139, 92, 246, 0.25)",
                    },
                ),
                width="100%",
                align="center",
                padding_bottom="16px",
            ),
            # Loading state
            rx.cond(
                AppState.is_loading,
                rx.hstack(
                    rx.spinner(size="3"),
                    rx.text(
                        "Loading accounts...",
                        font_size="14px",
                        color=COLORS["text_secondary"],
                    ),
                    spacing="3",
                    padding="24px",
                    justify="center",
                    width="100%",
                ),
                rx.fragment(),
            ),
            # Error state
            rx.cond(
                AppState.error_message != "",
                rx.box(
                    rx.hstack(
                        rx.icon("circle-alert", size=16, color=COLORS["accent_danger"]),
                        rx.text(
                            AppState.error_message,
                            font_size="14px",
                            color=COLORS["accent_danger"],
                        ),
                        spacing="2",
                    ),
                    padding="16px",
                    border_radius="8px",
                    background="rgba(239, 68, 68, 0.1)",
                    width="100%",
                ),
                rx.fragment(),
            ),
            # Accounts grid - investments
            rx.cond(
                AppState.has_investment_accounts,
                rx.vstack(
                    rx.text(
                        "Investments",
                        font_size="14px",
                        font_weight="500",
                        color=COLORS["text_secondary"],
                        padding_bottom="8px",
                    ),
                    rx.grid(
                        rx.foreach(
                            AppState.investment_accounts,
                            account_card,
                        ),
                        columns="3",
                        spacing="3",
                        width="100%",
                    ),
                    width="100%",
                    align="start",
                    padding_bottom="16px",
                ),
                rx.fragment(),
            ),
            # Accounts grid - cash
            rx.cond(
                AppState.has_cash_accounts,
                rx.vstack(
                    rx.text(
                        "Cash & Savings",
                        font_size="14px",
                        font_weight="500",
                        color=COLORS["text_secondary"],
                        padding_bottom="8px",
                    ),
                    rx.grid(
                        rx.foreach(
                            AppState.cash_accounts,
                            account_card,
                        ),
                        columns="3",
                        spacing="3",
                        width="100%",
                    ),
                    width="100%",
                    align="start",
                    padding_bottom="16px",
                ),
                rx.fragment(),
            ),
            # Accounts grid - credit
            rx.cond(
                AppState.has_credit_accounts,
                rx.vstack(
                    rx.text(
                        "Credit Cards",
                        font_size="14px",
                        font_weight="500",
                        color=COLORS["text_secondary"],
                        padding_bottom="8px",
                    ),
                    rx.grid(
                        rx.foreach(
                            AppState.credit_accounts,
                            account_card,
                        ),
                        columns="3",
                        spacing="3",
                        width="100%",
                    ),
                    width="100%",
                    align="start",
                ),
                rx.fragment(),
            ),
            # Accounts grid - loans
            rx.cond(
                AppState.has_loan_accounts,
                rx.vstack(
                    rx.text(
                        "Loans",
                        font_size="14px",
                        font_weight="500",
                        color=COLORS["text_secondary"],
                        padding_bottom="8px",
                    ),
                    rx.grid(
                        rx.foreach(
                            AppState.loan_accounts,
                            account_card,
                        ),
                        columns="3",
                        spacing="3",
                        width="100%",
                    ),
                    width="100%",
                    align="start",
                ),
                rx.fragment(),
            ),
            # Empty state
            rx.cond(
                ~AppState.has_accounts & ~AppState.is_loading,
                rx.vstack(
                    rx.icon(
                        "wallet",
                        size=48,
                        color=COLORS["text_secondary"],
                    ),
                    rx.text(
                        "No accounts connected",
                        font_size="16px",
                        color=COLORS["text_secondary"],
                    ),
                    rx.text(
                        "Configure your Lunch Money API token in Settings to see your accounts",
                        font_size="14px",
                        color=COLORS["text_secondary"],
                    ),
                    rx.link(
                        rx.button(
                            "Go to Settings",
                            padding="12px 24px",
                            border_radius="10px",
                            background=COLORS["accent_primary"],
                            color="white",
                            font_size="14px",
                            border="none",
                            cursor="pointer",
                        ),
                        href="/settings",
                    ),
                    spacing="3",
                    align="center",
                    padding="48px",
                    width="100%",
                ),
                rx.fragment(),
            ),
            width="100%",
            padding="24px",
            border_radius="16px",
            background=COLORS["glass_bg"],
            backdrop_filter="blur(24px)",
            border=f"1px solid {COLORS['glass_border']}",
        ),
    )
