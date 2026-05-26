"""Readable donut chart with a compact value legend."""

import reflex as rx

from ....styles.theme import CHART_COLORS, COLORS
from ._tooltip import currency_tooltip


def _palette_cells(n: int = 8) -> list[rx.Component]:
    return [rx.recharts.cell(fill=CHART_COLORS[i % len(CHART_COLORS)]) for i in range(n)]


def _legend_row(row: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.box(
            width="8px",
            height="8px",
            border_radius="999px",
            background=row["color"],
            flex_shrink="0",
        ),
        rx.text(
            row["name"],
            font_size="12px",
            color=COLORS["text_primary"],
            overflow="hidden",
            text_overflow="ellipsis",
            white_space="nowrap",
            title=row["name"],
            flex="1",
            min_width="0",
        ),
        rx.text(
            row["percent_fmt"],
            font_size="12px",
            color=COLORS["text_secondary"],
            width="52px",
            text_align="right",
            flex_shrink="0",
        ),
        rx.text(
            row["value_fmt"],
            font_size="12px",
            font_weight="600",
            color=COLORS["text_primary"],
            width="78px",
            text_align="right",
            flex_shrink="0",
        ),
        spacing="2",
        align="center",
        width="100%",
        min_width="0",
    )


def exposure_donut(data: rx.Var, height: int = 250) -> rx.Component:
    chart_height = max(height - 106, 150)
    return rx.vstack(
        rx.box(
            rx.recharts.pie_chart(
                rx.recharts.pie(
                    *_palette_cells(8),
                    data=data,
                    data_key="chart_value",
                    name_key="name",
                    cx="50%",
                    cy="50%",
                    inner_radius="62%",
                    outer_radius="82%",
                    padding_angle=2,
                    stroke=COLORS["bg_secondary"],
                    stroke_width=2,
                ),
                currency_tooltip(),
                height=chart_height,
                width="100%",
            ),
            width="100%",
            min_height=f"{chart_height}px",
        ),
        rx.vstack(
            rx.foreach(data, _legend_row),
            spacing="2",
            width="100%",
            max_height="108px",
            overflow_y="auto",
            padding_right="4px",
        ),
        spacing="2",
        width="100%",
        height=f"{height}px",
    )
