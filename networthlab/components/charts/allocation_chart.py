"""Asset allocation donut chart component."""

import reflex as rx
from ...styles.theme import COLORS, CHART_COLORS


def allocation_chart(
    data: list[dict] | rx.Var,
    height: int = 300,
) -> rx.Component:
    """
    Asset allocation donut/pie chart.

    Args:
        data: List of dicts with 'name' and 'value' keys
        height: Chart height
    """
    return rx.recharts.pie_chart(
        rx.recharts.pie(
            data=data,
            data_key="value",
            name_key="name",
            cx="50%",
            cy="50%",
            inner_radius="60%",
            outer_radius="80%",
            padding_angle=2,
            label=rx.Var(
                "({name, percent}) => name + ': ' + (percent * 100).toFixed(0) + '%'"
            ),
            label_line=False,
            stroke="none",
        ),
        rx.recharts.graphing_tooltip(
            content_style={
                "backgroundColor": COLORS["bg_secondary"],
                "border": f"1px solid {COLORS['glass_border']}",
                "borderRadius": "8px",
                "color": COLORS["text_primary"],
            },
            formatter=rx.Var("(value) => ['$' + value.toLocaleString(), 'Value']"),
        ),
        rx.recharts.legend(
            layout="vertical",
            align="right",
            vertical_align="middle",
            wrapper_style={"paddingLeft": "20px"},
        ),
        height=height,
        width="100%",
    )


def allocation_donut_simple(
    data: list[dict] | rx.Var,
    height: int = 250,
) -> rx.Component:
    """
    Simple donut chart without external labels.

    Args:
        data: List of dicts with 'name' and 'value' keys
        height: Chart height
    """
    return rx.recharts.pie_chart(
        rx.recharts.pie(
            data=data,
            data_key="value",
            name_key="name",
            cx="50%",
            cy="50%",
            inner_radius="55%",
            outer_radius="75%",
            padding_angle=3,
            stroke="none",
            fill=CHART_COLORS[0],
        ),
        rx.recharts.graphing_tooltip(
            content_style={
                "backgroundColor": COLORS["bg_secondary"],
                "border": f"1px solid {COLORS['glass_border']}",
                "borderRadius": "8px",
                "color": COLORS["text_primary"],
                "fontSize": "12px",
            },
            formatter=rx.Var("(value, name, props) => ['$' + value.toLocaleString(), props.payload.name]"),
        ),
        height=height,
        width="100%",
    )
