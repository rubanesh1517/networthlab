"""Account display card component."""

import reflex as rx

from ...state.app_state import Account
from ...styles.theme import COLORS


def account_card(account: Account) -> rx.Component:
    """
    Account display card with balance and details.

    Args:
        account: Account model instance
    """
    # Determine color based on balance (positive = green, negative = red)
    balance_color = rx.cond(
        account.balance >= 0,
        COLORS["accent_success"],
        COLORS["accent_danger"],
    )

    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(
                    "wallet",
                    size=18,
                    color=COLORS["accent_primary"],
                ),
                width="36px",
                height="36px",
                display="flex",
                align_items="center",
                justify_content="center",
                border_radius="10px",
                background="rgba(139, 92, 246, 0.15)",
                flex_shrink="0",
            ),
            rx.vstack(
                rx.text(
                    account.name,
                    font_size="14px",
                    font_weight="500",
                    color=COLORS["text_primary"],
                    overflow="hidden",
                    text_overflow="ellipsis",
                    white_space="nowrap",
                ),
                rx.text(
                    rx.cond(
                        account.institution != "",
                        account.institution,
                        account.type,
                    ),
                    font_size="12px",
                    color=COLORS["text_secondary"],
                    overflow="hidden",
                    text_overflow="ellipsis",
                    white_space="nowrap",
                ),
                spacing="0",
                align="start",
                flex="1",
                min_width="0",
            ),
            rx.text(
                "$" + account.balance.to(str),
                font_size="14px",
                font_weight="600",
                color=balance_color,
                flex_shrink="0",
            ),
            spacing="3",
            width="100%",
            align="center",
        ),
        padding="16px",
        border_radius="12px",
        background="rgba(255, 255, 255, 0.02)",
        border=f"1px solid {COLORS['glass_border']}",
        _hover={
            "background": "rgba(255, 255, 255, 0.04)",
            "border": "1px solid rgba(139, 92, 246, 0.2)",
        },
        transition="all 0.2s ease",
        width="100%",
    )
