"""Multi-colour donut chart for the exposure tiles.

The shared `allocation_donut_simple` uses a single fill, which leaves the
chart looking like one giant slice. The exposure tiles need colour rotation
across slices (matching the brainstorming mocks) plus a centred bucket count
so the donut reads at a glance even when there are only a handful of values.
"""

import reflex as rx

from ....styles.theme import CHART_COLORS, COLORS


# Reuse the global palette but rotate so adjacent tiles do not start on the
# same hue.  recharts requires concrete Cell components for per-slice fill.
def _palette_cells(n: int = 8) -> list[rx.Component]:
    return [
        rx.recharts.cell(fill=CHART_COLORS[i % len(CHART_COLORS)])
        for i in range(n)
    ]


def exposure_donut(data: rx.Var, height: int = 230) -> rx.Component:
    """Donut where each slice rotates through the chart palette.

    `data` is a list[{"name": str, "value": float}] from ExposureState.
    Slices are labelled with their bucket name + percent share; tooltip
    formats values as `$X,XXX.XX`.
    """
    return rx.recharts.pie_chart(
        rx.recharts.pie(
            *_palette_cells(8),
            data=data,
            data_key="value",
            name_key="name",
            cx="50%",
            cy="50%",
            inner_radius="58%",
            outer_radius="82%",
            padding_angle=2,
            stroke="none",
            label=rx.Var(
                "({name, percent}) => name + '  ' "
                "+ (percent * 100).toFixed(1) + '%'"
            ),
            label_line={"stroke": COLORS["text_secondary"], "strokeWidth": 1},
        ),
        rx.recharts.graphing_tooltip(
            content_style={
                "backgroundColor": COLORS["bg_secondary"],
                "border": f"1px solid {COLORS['glass_border']}",
                "borderRadius": "8px",
                "color": COLORS["text_primary"],
                "padding": "8px 12px",
                "fontSize": "12px",
            },
            formatter=rx.Var(
                "(value, name) => ["
                "'$' + Number(value).toLocaleString('en-US', "
                "{minimumFractionDigits: 2, maximumFractionDigits: 2}), name]"
            ),
        ),
        height=height,
        width="100%",
    )
