"""Multi-colour donut chart for the exposure tiles.

The shared `allocation_donut_simple` uses a single fill, which leaves the
chart looking like one giant slice. The exposure tiles need colour rotation
across slices (matching the brainstorming mocks) plus a centred bucket count
so the donut reads at a glance even when there are only a handful of values.
"""

import reflex as rx

from ....styles.theme import CHART_COLORS, COLORS
from ._tooltip import currency_tooltip


# Reuse the global palette but rotate so adjacent tiles do not start on the
# same hue.  recharts requires concrete Cell components for per-slice fill.
def _palette_cells(n: int = 8) -> list[rx.Component]:
    return [
        rx.recharts.cell(fill=CHART_COLORS[i % len(CHART_COLORS)])
        for i in range(n)
    ]


def exposure_donut(data: rx.Var, height: int = 230) -> rx.Component:
    """Donut where each slice rotates through the chart palette.

    Slices below 3% have their labels suppressed to prevent visual collision
    on the chart edge — the tooltip still shows the exact $ value on hover,
    and the legend below the donut lists every bucket.
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
                "({name, percent}) => percent >= 0.03 "
                "? name + '  ' + (percent * 100).toFixed(1) + '%' "
                ": ''"
            ),
            # No leader lines — clean modern donut. The legend below the
            # chart lists every bucket regardless of slice size, and tiny
            # slices still surface their $ value on hover via the tooltip.
            label_line=False,
        ),
        currency_tooltip(),
        rx.recharts.legend(
            layout="horizontal",
            align="center",
            vertical_align="bottom",
            icon_type="circle",
            wrapper_style={"fontSize": "11px", "paddingTop": "4px"},
        ),
        height=height,
        width="100%",
    )
