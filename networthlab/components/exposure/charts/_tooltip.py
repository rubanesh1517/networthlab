"""Currency-formatting tooltip for the exposure charts.

Reflex's stock `rx.recharts.graphing_tooltip` does not declare the recharts
`formatter` prop, so any `formatter=...` we pass is silently dropped (the
tooltip ends up showing raw floats like `126628.1852623616`). Subclassing
`GraphingTooltip` to add the field lets us pass the JS formatter through.
"""

from typing import Any

import reflex as rx
from reflex.components.recharts.general import GraphingTooltip

from ....styles.theme import COLORS


class _TooltipWithFormatter(GraphingTooltip):
    """GraphingTooltip + the missing `formatter` recharts prop."""

    formatter: rx.Var[Any]


# JS arrow function that turns recharts' raw (value, name) into a
# (display_value, display_name) pair the tooltip renders.
_CURRENCY_FORMATTER = rx.Var(
    "(value, name) => ["
    "'$' + Number(value).toLocaleString('en-US', "
    "{minimumFractionDigits: 2, maximumFractionDigits: 2}), "
    "name]"
)


def currency_tooltip() -> rx.Component:
    return _TooltipWithFormatter.create(
        formatter=_CURRENCY_FORMATTER,
        separator=": ",
        cursor={"fill": "rgba(255,255,255,0.04)"},
        content_style={
            "backgroundColor": COLORS["bg_secondary"],
            "border": f"1px solid {COLORS['glass_border']}",
            "borderRadius": "8px",
            "color": COLORS["text_primary"],
            "padding": "8px 12px",
            "fontSize": "12px",
        },
        item_style={"color": COLORS["text_primary"]},
        label_style={"color": COLORS["text_secondary"]},
    )
