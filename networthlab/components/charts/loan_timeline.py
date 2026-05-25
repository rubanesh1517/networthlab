"""Loan payoff timeline stacked bar chart component."""

import reflex as rx

from ...styles.theme import CHART_COLORS, COLORS


def loan_timeline_chart(
    data: list[dict] | rx.Var,
    loan_names: list[str] | rx.Var,
    height: int = 300,
) -> rx.Component:
    """
    Stacked bar chart showing loan payoff timeline.

    Args:
        data: List of dicts with 'year' and balance for each loan
        loan_names: List of loan names for the chart keys
        height: Chart height
    """
    # Create bar components for each loan dynamically
    bars = []
    for i, name in enumerate(loan_names if isinstance(loan_names, list) else []):
        bars.append(
            rx.recharts.bar(
                data_key=name,
                fill=CHART_COLORS[i % len(CHART_COLORS)],
                stack_id="loans",
                name=name,
            )
        )

    return rx.recharts.bar_chart(
        *bars,
        rx.recharts.x_axis(
            data_key="year",
            stroke=COLORS["text_secondary"],
            font_size=12,
            tick_line=False,
            axis_line=False,
            label={"value": "Years", "position": "insideBottom", "offset": -5},
        ),
        rx.recharts.y_axis(
            stroke=COLORS["text_secondary"],
            font_size=12,
            tick_line=False,
            axis_line=False,
            custom_attrs={"tickFormatter": rx.Var("(value) => '$' + (value/1000).toFixed(0) + 'k'")},
        ),
        rx.recharts.cartesian_grid(
            stroke_dasharray="3 3",
            stroke="rgba(255,255,255,0.05)",
            vertical=False,
        ),
        rx.recharts.graphing_tooltip(
            content_style={
                "backgroundColor": COLORS["bg_secondary"],
                "border": f"1px solid {COLORS['glass_border']}",
                "borderRadius": "8px",
                "color": COLORS["text_primary"],
            },
            formatter=rx.Var("(value, name) => ['$' + value.toLocaleString(), name]"),
        ),
        rx.recharts.legend(
            wrapper_style={"paddingTop": "20px"},
        ),
        data=data,
        height=height,
        width="100%",
        margin={"top": 10, "right": 10, "left": 0, "bottom": 20},
    )


def loan_timeline_chart_dynamic(
    data: rx.Var,
    height: int = 300,
) -> rx.Component:
    """
    Dynamic stacked bar chart that handles variable loan names.

    Args:
        data: Var containing list of dicts with 'year' and loan balances
        height: Chart height
    """
    return rx.recharts.bar_chart(
        rx.recharts.bar(
            data_key="Loan 1",
            fill=CHART_COLORS[0],
            stack_id="loans",
            name="Loan 1",
        ),
        rx.recharts.bar(
            data_key="Loan 2",
            fill=CHART_COLORS[1],
            stack_id="loans",
            name="Loan 2",
        ),
        rx.recharts.bar(
            data_key="Loan 3",
            fill=CHART_COLORS[2],
            stack_id="loans",
            name="Loan 3",
        ),
        rx.recharts.x_axis(
            data_key="year",
            stroke=COLORS["text_secondary"],
            font_size=12,
            tick_line=False,
            axis_line=False,
        ),
        rx.recharts.y_axis(
            stroke=COLORS["text_secondary"],
            font_size=12,
            tick_line=False,
            axis_line=False,
            custom_attrs={"tickFormatter": rx.Var("(value) => '$' + (value/1000).toFixed(0) + 'k'")},
        ),
        rx.recharts.cartesian_grid(
            stroke_dasharray="3 3",
            stroke="rgba(255,255,255,0.05)",
            vertical=False,
        ),
        rx.recharts.graphing_tooltip(
            content_style={
                "backgroundColor": COLORS["bg_secondary"],
                "border": f"1px solid {COLORS['glass_border']}",
                "borderRadius": "8px",
                "color": COLORS["text_primary"],
            },
        ),
        rx.recharts.legend(
            wrapper_style={"paddingTop": "10px"},
        ),
        data=data,
        height=height,
        width="100%",
        margin={"top": 10, "right": 10, "left": 0, "bottom": 0},
    )
