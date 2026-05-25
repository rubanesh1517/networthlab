"""Concentration bar chart — top N positions by weight.

Bars use the palette in rotation and label their $ value at the end of
the bar so you can scan dollar magnitudes without hovering.
"""

import reflex as rx

from ....styles.theme import CHART_COLORS, COLORS


def _palette_cells(n: int = 10) -> list[rx.Component]:
    return [
        rx.recharts.cell(fill=CHART_COLORS[i % len(CHART_COLORS)])
        for i in range(n)
    ]


def concentration_bars(data: rx.Var, height: int = 280) -> rx.Component:
    return rx.recharts.bar_chart(
        rx.recharts.bar(
            *_palette_cells(10),
            data_key="value",
            radius=[0, 4, 4, 0],
            label={
                "position": "right",
                "fill": COLORS["text_primary"],
                "fontSize": 11,
                "formatter": rx.Var(
                    "(value) => '$' + Number(value).toLocaleString('en-US', "
                    "{minimumFractionDigits: 2, maximumFractionDigits: 2})"
                ),
            },
        ),
        rx.recharts.x_axis(type_="number", hide=True),
        rx.recharts.y_axis(
            data_key="name",
            type_="category",
            width=90,
            tick={"fill": COLORS["text_secondary"], "fontSize": 11},
            axis_line=False,
            tick_line=False,
        ),
        rx.recharts.graphing_tooltip(
            cursor={"fill": "rgba(255,255,255,0.04)"},
            content_style={
                "backgroundColor": COLORS["bg_secondary"],
                "border": f"1px solid {COLORS['glass_border']}",
                "borderRadius": "8px",
                "color": COLORS["text_primary"],
                "padding": "8px 12px",
                "fontSize": "12px",
            },
            formatter=rx.Var(
                "(value) => ["
                "'$' + Number(value).toLocaleString('en-US', "
                "{minimumFractionDigits: 2, maximumFractionDigits: 2}), 'Value']"
            ),
        ),
        data=data,
        layout="vertical",
        height=height,
        width="100%",
        margin={"top": 4, "right": 80, "left": 0, "bottom": 4},
    )
