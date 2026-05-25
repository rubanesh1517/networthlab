"""Loan add/edit form component."""

import reflex as rx
from ...styles.theme import COLORS


def form_input(
    label: str,
    placeholder: str,
    value: rx.Var[str],
    on_change: rx.EventHandler,
    input_type: str = "text",
) -> rx.Component:
    """Styled form input."""
    return rx.vstack(
        rx.text(
            label,
            font_size="13px",
            font_weight="500",
            color=COLORS["text_secondary"],
        ),
        rx.input(
            placeholder=placeholder,
            value=value,
            on_change=on_change,
            type=input_type,
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
                "box_shadow": f"0 0 0 2px rgba(139, 92, 246, 0.2)",
            },
            _placeholder={
                "color": COLORS["text_secondary"],
            },
        ),
        spacing="2",
        width="100%",
        align="start",
    )


def loan_form() -> rx.Component:
    """Add/edit loan form modal."""
    from ...state.loan_state import LoanState

    return rx.cond(
        LoanState.show_form,
        rx.box(
            rx.box(
                rx.vstack(
                    # Header
                    rx.hstack(
                        rx.text(
                            rx.cond(
                                LoanState.editing_loan_id != "",
                                "Edit Loan",
                                "Add New Loan",
                            ),
                            font_size="18px",
                            font_weight="600",
                            color=COLORS["text_primary"],
                        ),
                        rx.spacer(),
                        rx.icon(
                            "x",
                            size=20,
                            color=COLORS["text_secondary"],
                            cursor="pointer",
                            on_click=LoanState.toggle_form,
                            _hover={"color": COLORS["text_primary"]},
                        ),
                        width="100%",
                        align="center",
                    ),
                    # Form fields
                    form_input(
                        "Loan Name",
                        "e.g., Car Loan, Mortgage",
                        LoanState.form_name,
                        LoanState.set_form_name,
                    ),
                    rx.hstack(
                        form_input(
                            "Principal Amount",
                            "$0.00",
                            LoanState.form_principal,
                            LoanState.set_form_principal,
                        ),
                        form_input(
                            "Interest Rate (%)",
                            "5.5",
                            LoanState.form_interest_rate,
                            LoanState.set_form_interest_rate,
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    rx.hstack(
                        form_input(
                            "Monthly Payment",
                            "$0.00",
                            LoanState.form_monthly_payment,
                            LoanState.set_form_monthly_payment,
                        ),
                        form_input(
                            "Term (Months)",
                            "60",
                            LoanState.form_term_months,
                            LoanState.set_form_term_months,
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    form_input(
                        "Start Date",
                        "YYYY-MM-DD",
                        LoanState.form_start_date,
                        LoanState.set_form_start_date,
                    ),
                    # Action buttons
                    rx.hstack(
                        rx.button(
                            "Cancel",
                            on_click=LoanState.toggle_form,
                            padding="12px 24px",
                            border_radius="10px",
                            background="transparent",
                            border=f"1px solid {COLORS['glass_border']}",
                            color=COLORS["text_secondary"],
                            font_size="14px",
                            font_weight="500",
                            cursor="pointer",
                            _hover={
                                "background": "rgba(255, 255, 255, 0.05)",
                            },
                        ),
                        rx.button(
                            rx.cond(
                                LoanState.editing_loan_id != "",
                                "Update Loan",
                                "Add Loan",
                            ),
                            on_click=LoanState.save_or_update_loan,
                            padding="12px 24px",
                            border_radius="10px",
                            background=COLORS["accent_primary"],
                            color="white",
                            font_size="14px",
                            font_weight="500",
                            border="none",
                            cursor="pointer",
                            _hover={
                                "opacity": "0.9",
                            },
                        ),
                        spacing="3",
                        width="100%",
                        justify="end",
                        padding_top="8px",
                    ),
                    spacing="4",
                    width="100%",
                ),
                max_width="500px",
                width="90%",
                padding="24px",
                border_radius="16px",
                background=COLORS["bg_secondary"],
                border=f"1px solid {COLORS['glass_border']}",
            ),
            position="fixed",
            top="0",
            left="0",
            right="0",
            bottom="0",
            background="rgba(0, 0, 0, 0.7)",
            backdrop_filter="blur(4px)",
            display="flex",
            align_items="center",
            justify_content="center",
            z_index="1000",
        ),
    )
