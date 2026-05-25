"""Loan Tracker page."""

import reflex as rx

from ..components.cards.chart_card import chart_card
from ..components.cards.stat_card import stat_card
from ..components.charts.loan_timeline import loan_timeline_chart_dynamic
from ..components.forms.loan_form import loan_form
from ..components.layout.page_wrapper import page_wrapper
from ..state.loan_state import Loan, LoanState
from ..styles.theme import COLORS


def loan_card(loan: Loan) -> rx.Component:
    """Individual loan display card."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text(
                        loan.name,
                        font_size="16px",
                        font_weight="600",
                        color=COLORS["text_primary"],
                    ),
                    rx.text(
                        loan.interest_rate.to(str) + "% APR",
                        font_size="12px",
                        color=COLORS["text_secondary"],
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.icon(
                        "pencil",
                        size=16,
                        color=COLORS["text_secondary"],
                        cursor="pointer",
                        on_click=lambda: LoanState.edit_loan(loan.id),
                        _hover={"color": COLORS["accent_primary"]},
                    ),
                    rx.icon(
                        "trash-2",
                        size=16,
                        color=COLORS["text_secondary"],
                        cursor="pointer",
                        on_click=lambda: LoanState.delete_loan(loan.id),
                        _hover={"color": COLORS["accent_danger"]},
                    ),
                    spacing="3",
                ),
                width="100%",
                align="center",
            ),
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "Principal",
                        font_size="11px",
                        color=COLORS["text_secondary"],
                    ),
                    rx.text(
                        "$" + loan.principal.to(str),
                        font_size="14px",
                        font_weight="500",
                        color=COLORS["text_primary"],
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.vstack(
                    rx.text(
                        "Monthly",
                        font_size="11px",
                        color=COLORS["text_secondary"],
                    ),
                    rx.text(
                        "$" + loan.monthly_payment.to(str),
                        font_size="14px",
                        font_weight="500",
                        color=COLORS["text_primary"],
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.vstack(
                    rx.text(
                        "Remaining",
                        font_size="11px",
                        color=COLORS["text_secondary"],
                    ),
                    rx.text(
                        "$" + loan.current_balance.to(str),
                        font_size="14px",
                        font_weight="500",
                        color=COLORS["accent_danger"],
                    ),
                    spacing="0",
                    align="start",
                ),
                spacing="6",
                width="100%",
                padding_top="12px",
            ),
            spacing="0",
            width="100%",
        ),
        padding="20px",
        border_radius="12px",
        background="rgba(255, 255, 255, 0.02)",
        border=f"1px solid {COLORS['glass_border']}",
        _hover={
            "border": "1px solid rgba(139, 92, 246, 0.2)",
        },
        transition="all 0.2s ease",
    )


def loan_tracker() -> rx.Component:
    """Loan Tracker page component."""
    return page_wrapper(
        "Loan Tracker",
        "Track your debts and see your payoff timeline",
        # Include the loan form modal
        loan_form(),
        # Stat cards row
        rx.hstack(
            stat_card(
                title="Total Debt",
                value=LoanState.formatted_total_debt,
                icon="credit-card",
                color="red",
            ),
            stat_card(
                title="Monthly Payment",
                value=LoanState.formatted_monthly_payment,
                icon="calendar",
                color="blue",
            ),
            stat_card(
                title="Avg Interest Rate",
                value=LoanState.formatted_avg_rate,
                icon="percent",
                color="amber",
            ),
            stat_card(
                title="Debt Free Date",
                value=LoanState.estimated_payoff_date,
                icon="flag",
                color="green",
            ),
            spacing="4",
            width="100%",
            flex_wrap="wrap",
        ),
        # Add loan button and loans section
        rx.hstack(
            # Loans list
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "Your Loans",
                            font_size="16px",
                            font_weight="600",
                            color=COLORS["text_primary"],
                        ),
                        rx.spacer(),
                        rx.button(
                            rx.hstack(
                                rx.icon("plus", size=14),
                                rx.text("Add Loan"),
                                spacing="2",
                            ),
                            on_click=LoanState.toggle_form,
                            padding="8px 16px",
                            border_radius="8px",
                            background=COLORS["accent_primary"],
                            color="white",
                            font_size="13px",
                            border="none",
                            cursor="pointer",
                            _hover={
                                "opacity": "0.9",
                            },
                        ),
                        width="100%",
                        align="center",
                    ),
                    rx.cond(
                        LoanState.has_loans,
                        rx.vstack(
                            rx.foreach(
                                LoanState.loans,
                                loan_card,
                            ),
                            spacing="3",
                            width="100%",
                            padding_top="16px",
                        ),
                        rx.vstack(
                            rx.icon(
                                "circle-check",
                                size=48,
                                color=COLORS["accent_success"],
                            ),
                            rx.text(
                                "No loans tracked",
                                font_size="16px",
                                color=COLORS["text_secondary"],
                            ),
                            rx.text(
                                "Add a loan to start tracking your debt payoff",
                                font_size="14px",
                                color=COLORS["text_secondary"],
                            ),
                            spacing="3",
                            align="center",
                            padding="48px",
                            width="100%",
                        ),
                    ),
                    spacing="0",
                    width="100%",
                ),
                padding="24px",
                border_radius="16px",
                background=COLORS["glass_bg"],
                backdrop_filter="blur(24px)",
                border=f"1px solid {COLORS['glass_border']}",
                flex="1",
                min_width="350px",
            ),
            # Payoff timeline chart
            rx.cond(
                LoanState.has_loans,
                chart_card(
                    "Payoff Timeline",
                    loan_timeline_chart_dynamic(LoanState.payoff_timeline_data),
                    subtitle="Projected debt balance over time",
                    height="100%",
                ),
                rx.fragment(),
            ),
            spacing="4",
            width="100%",
            align="stretch",
            flex_wrap="wrap",
        ),
        # Payoff strategies section
        rx.cond(
            LoanState.has_loans,
            rx.box(
                rx.vstack(
                    rx.text(
                        "Payoff Strategies",
                        font_size="16px",
                        font_weight="600",
                        color=COLORS["text_primary"],
                        padding_bottom="16px",
                    ),
                    rx.hstack(
                        # Avalanche method
                        rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.icon("mountain", size=20, color=COLORS["accent_secondary"]),
                                    rx.text(
                                        "Avalanche Method",
                                        font_size="14px",
                                        font_weight="600",
                                        color=COLORS["text_primary"],
                                    ),
                                    spacing="2",
                                ),
                                rx.text(
                                    "Pay minimums on all debts, then put extra money toward the highest interest rate debt first.",
                                    font_size="13px",
                                    color=COLORS["text_secondary"],
                                ),
                                rx.box(
                                    rx.text(
                                        "Saves the most money on interest",
                                        font_size="12px",
                                        color=COLORS["accent_success"],
                                    ),
                                    padding="8px 12px",
                                    border_radius="6px",
                                    background="rgba(16, 185, 129, 0.1)",
                                ),
                                spacing="3",
                                align="start",
                            ),
                            padding="20px",
                            border_radius="12px",
                            background="rgba(255, 255, 255, 0.02)",
                            border=f"1px solid {COLORS['glass_border']}",
                            flex="1",
                        ),
                        # Snowball method
                        rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.icon("snowflake", size=20, color=COLORS["accent_primary"]),
                                    rx.text(
                                        "Snowball Method",
                                        font_size="14px",
                                        font_weight="600",
                                        color=COLORS["text_primary"],
                                    ),
                                    spacing="2",
                                ),
                                rx.text(
                                    "Pay minimums on all debts, then put extra money toward the smallest balance first.",
                                    font_size="13px",
                                    color=COLORS["text_secondary"],
                                ),
                                rx.box(
                                    rx.text(
                                        "Fastest psychological wins",
                                        font_size="12px",
                                        color=COLORS["accent_primary"],
                                    ),
                                    padding="8px 12px",
                                    border_radius="6px",
                                    background="rgba(139, 92, 246, 0.1)",
                                ),
                                spacing="3",
                                align="start",
                            ),
                            padding="20px",
                            border_radius="12px",
                            background="rgba(255, 255, 255, 0.02)",
                            border=f"1px solid {COLORS['glass_border']}",
                            flex="1",
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    width="100%",
                ),
                padding="24px",
                border_radius="16px",
                background=COLORS["glass_bg"],
                backdrop_filter="blur(24px)",
                border=f"1px solid {COLORS['glass_border']}",
            ),
            rx.fragment(),
        ),
    )
