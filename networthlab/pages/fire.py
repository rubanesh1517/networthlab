"""FIRE Calculator page."""

import reflex as rx

from ..components.cards.chart_card import chart_card
from ..components.cards.stat_card import stat_card
from ..components.charts.fire_progress import fire_progress_ring
from ..components.charts.net_worth_chart import net_worth_projection_chart
from ..components.layout.page_wrapper import page_wrapper
from ..state.fire_state import FIREState
from ..styles.theme import COLORS


def slider_input(
    label: str,
    value: rx.Var,
    on_change: rx.EventHandler,
    min_val: int,
    max_val: int,
    step: int = 1,
    suffix: str = "",
) -> rx.Component:
    """Custom slider input component."""
    return rx.vstack(
        rx.hstack(
            rx.text(
                label,
                font_size="13px",
                color=COLORS["text_secondary"],
            ),
            rx.spacer(),
            rx.text(
                f"{value}{suffix}",
                font_size="14px",
                font_weight="500",
                color=COLORS["text_primary"],
            ),
            width="100%",
        ),
        rx.slider(
            value=[value],
            on_change=on_change,
            min=min_val,
            max=max_val,
            step=step,
            width="100%",
        ),
        spacing="2",
        width="100%",
    )


def text_input(
    label: str,
    value: rx.Var[str] | str,
    on_change: rx.EventHandler,
    placeholder: str = "",
) -> rx.Component:
    """Styled text input."""
    return rx.vstack(
        rx.text(
            label,
            font_size="13px",
            color=COLORS["text_secondary"],
        ),
        rx.input(
            value=value,
            on_change=on_change,
            placeholder=placeholder,
            width="100%",
            min_width="120px",
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
        spacing="2",
        width="100%",
        min_width="140px",
        flex="1",
        align="start",
    )


def fire_calculator() -> rx.Component:
    """FIRE Calculator page component."""
    return page_wrapper(
        "FIRE Calculator",
        "Plan your path to Financial Independence, Retire Early",
        # Top row: Progress ring and stats
        rx.hstack(
            # FIRE Progress Ring Card
            rx.box(
                fire_progress_ring(
                    progress=FIREState.fire_progress_percent,
                    fire_number=FIREState.formatted_fire_number,
                    years_to_fire=FIREState.years_to_fire,
                    fire_age=FIREState.fire_age,
                ),
                padding="16px",
                border_radius="16px",
                background=COLORS["glass_bg"],
                backdrop_filter="blur(24px)",
                border=f"1px solid {COLORS['glass_border']}",
                flex="1",
                min_width="300px",
            ),
            # Stats column - use hstack for horizontal layout
            rx.hstack(
                stat_card(
                    title="FIRE Year",
                    value=FIREState.fire_year,
                    icon="calendar",
                    color="amber",
                ),
                stat_card(
                    title="Monthly Passive Income",
                    value=FIREState.formatted_monthly_income,
                    icon="banknote",
                    color="green",
                    subtitle="At 4% withdrawal rate",
                ),
                spacing="4",
                flex="1",
            ),
            spacing="4",
            width="100%",
            align="stretch",
            flex_wrap="wrap",
        ),
        # Inputs section
        rx.hstack(
            # Personal Info
            rx.box(
                rx.vstack(
                    rx.text(
                        "Your Information",
                        font_size="16px",
                        font_weight="600",
                        color=COLORS["text_primary"],
                        padding_bottom="16px",
                    ),
                    rx.hstack(
                        text_input(
                            "Current Age",
                            FIREState.current_age_str,
                            FIREState.set_current_age,
                            "30",
                        ),
                        text_input(
                            "Target Retirement Age",
                            FIREState.retirement_age_str,
                            FIREState.set_retirement_age,
                            "65",
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    text_input(
                        "Current Investment Portfolio",
                        FIREState.formatted_current_investments,
                        FIREState.set_current_investments,
                        "$100,000",
                    ),
                    rx.hstack(
                        text_input(
                            "Annual Expenses",
                            FIREState.formatted_annual_expenses,
                            FIREState.set_annual_expenses,
                            "$50,000",
                        ),
                        text_input(
                            "Monthly Contribution",
                            FIREState.formatted_monthly_contribution,
                            FIREState.set_monthly_contribution,
                            "$2,000",
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                ),
                padding="24px",
                border_radius="16px",
                background=COLORS["glass_bg"],
                backdrop_filter="blur(24px)",
                border=f"1px solid {COLORS['glass_border']}",
                flex="1",
            ),
            # Assumptions
            rx.box(
                rx.vstack(
                    rx.text(
                        "Assumptions",
                        font_size="16px",
                        font_weight="600",
                        color=COLORS["text_primary"],
                        padding_bottom="16px",
                    ),
                    slider_input(
                        "Expected Annual Return",
                        FIREState.expected_return,
                        FIREState.set_expected_return,
                        1,
                        15,
                        suffix="%",
                    ),
                    slider_input(
                        "Inflation Rate",
                        FIREState.inflation_rate,
                        FIREState.set_inflation_rate,
                        0,
                        8,
                        suffix="%",
                    ),
                    slider_input(
                        "Safe Withdrawal Rate",
                        FIREState.withdrawal_rate,
                        FIREState.set_withdrawal_rate,
                        2,
                        6,
                        suffix="%",
                    ),
                    # Info box
                    rx.box(
                        rx.hstack(
                            rx.icon("info", size=14, color=COLORS["accent_secondary"]),
                            rx.text(
                                "The 4% rule suggests you can withdraw 4% of your portfolio annually with low risk of running out of money over 30 years.",
                                font_size="12px",
                                color=COLORS["text_secondary"],
                            ),
                            spacing="2",
                            align="start",
                        ),
                        padding="12px",
                        border_radius="8px",
                        background="rgba(59, 130, 246, 0.1)",
                        margin_top="8px",
                    ),
                    spacing="4",
                    width="100%",
                ),
                padding="24px",
                border_radius="16px",
                background=COLORS["glass_bg"],
                backdrop_filter="blur(24px)",
                border=f"1px solid {COLORS['glass_border']}",
                flex="1",
            ),
            spacing="4",
            width="100%",
            align="stretch",
        ),
        # Projection chart
        chart_card(
            "3-Scenario Projection",
            net_worth_projection_chart(FIREState.projection_data, height=350),
            subtitle="Comparing conservative, expected, and aggressive growth scenarios",
            height="450px",
            width="100%",
        ),
        # Year-by-year table
        rx.box(
            rx.vstack(
                rx.text(
                    "Year-by-Year Breakdown",
                    font_size="16px",
                    font_weight="600",
                    color=COLORS["text_primary"],
                    padding_bottom="16px",
                ),
                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Year"),
                                rx.table.column_header_cell("Age"),
                                rx.table.column_header_cell("Balance"),
                                rx.table.column_header_cell("Contributions"),
                                rx.table.column_header_cell("Interest"),
                                rx.table.column_header_cell("Progress"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                FIREState.yearly_breakdown,
                                lambda row: rx.table.row(
                                    rx.table.cell(row["year"]),
                                    rx.table.cell(row["age"]),
                                    rx.table.cell(row["balance"]),
                                    rx.table.cell(row["contributions"]),
                                    rx.table.cell(row["interest"]),
                                    rx.table.cell(
                                        rx.box(
                                            rx.text(
                                                row["progress"],
                                                font_size="12px",
                                                color=COLORS["text_primary"],
                                            ),
                                            padding="4px 8px",
                                            border_radius="4px",
                                            background="rgba(139, 92, 246, 0.2)",
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    width="100%",
                    overflow_x="auto",
                    max_height="400px",
                    overflow_y="auto",
                ),
                width="100%",
            ),
            padding="24px",
            border_radius="16px",
            background=COLORS["glass_bg"],
            backdrop_filter="blur(24px)",
            border=f"1px solid {COLORS['glass_border']}",
        ),
    )
