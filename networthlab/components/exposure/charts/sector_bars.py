"""Horizontal bar chart for sector / account / currency breakdowns."""

import reflex as rx

from ....styles.theme import COLORS, CHART_COLORS


def sector_bars(data: rx.Var, height: int = 240) -> rx.Component:
    return rx.recharts.bar_chart(
        rx.recharts.bar(
            data_key="value",
            fill=CHART_COLORS[0],
            radius=[0, 4, 4, 0],
        ),
        rx.recharts.x_axis(type_="number", hide=True),
        rx.recharts.y_axis(
            data_key="name", type_="category", width=110,
            tick={"fill": COLORS["text_secondary"], "fontSize": 11},
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
        data=data,
        layout="vertical",
        height=height,
        width="100%",
        margin={"top": 4, "right": 8, "left": 0, "bottom": 4},
    )
