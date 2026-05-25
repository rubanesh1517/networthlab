"""Net worth area chart component."""

import reflex as rx
from ...styles.theme import COLORS, CHART_COLORS


def net_worth_chart(
    data: list[dict] | rx.Var,
    height: int = 300,
) -> rx.Component:
    """
    Net worth area chart with gradient fill.

    Args:
        data: List of dicts with 'month' and 'value' keys
        height: Chart height
    """
    return rx.recharts.area_chart(
        rx.recharts.area(
            data_key="value",
            stroke=CHART_COLORS[0],
            fill=CHART_COLORS[0],
            fill_opacity=0.3,
            type_="monotone",
            stroke_width=2,
        ),
        rx.recharts.x_axis(
            data_key="month",
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
            formatter=rx.Var("(value) => ['$' + (value?.toLocaleString() || 0), 'Net Worth']"),
        ),
        data=data,
        height=height,
        width="100%",
        margin={"top": 10, "right": 10, "left": 0, "bottom": 0},
    )


def net_worth_projection_chart(
    data: list[dict] | rx.Var,
    height: int = 300,
) -> rx.Component:
    """
    Net worth chart with projection bands.

    Args:
        data: List of dicts with 'year', 'conservative', 'expected', 'aggressive', 'fire_target'
        height: Chart height
    """
    return rx.recharts.composed_chart(
        rx.recharts.area(
            data_key="aggressive",
            stroke=CHART_COLORS[2],
            fill=CHART_COLORS[2],
            fill_opacity=0.2,
            type_="monotone",
            stroke_width=2,
            name="Aggressive (9%)",
        ),
        rx.recharts.area(
            data_key="expected",
            stroke=CHART_COLORS[0],
            fill=CHART_COLORS[0],
            fill_opacity=0.2,
            type_="monotone",
            stroke_width=2,
            name="Expected (7%)",
        ),
        rx.recharts.area(
            data_key="conservative",
            stroke=CHART_COLORS[1],
            fill=CHART_COLORS[1],
            fill_opacity=0.2,
            type_="monotone",
            stroke_width=2,
            name="Conservative (5%)",
        ),
        rx.recharts.line(
            data_key="fire_target",
            stroke=COLORS["accent_warning"],
            stroke_width=2,
            stroke_dasharray="5 5",
            dot=False,
            name="FIRE Target",
        ),
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
            custom_attrs={"tickFormatter": rx.Var("(value) => '$' + (value/1000000).toFixed(1) + 'M'")},
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
            formatter=rx.Var("(value, name) => ['$' + (value?.toLocaleString() || 0), name]"),
        ),
        rx.recharts.legend(
            wrapper_style={"paddingTop": "20px"},
        ),
        data=data,
        height=height,
        width="100%",
        margin={"top": 10, "right": 10, "left": 0, "bottom": 20},
    )
