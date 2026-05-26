"""Reusable tile shell for each dimension."""

import reflex as rx

from ...styles.theme import COLORS


def exposure_tile(
    title: str,
    chart: rx.Component,
    chips: rx.Component | None = None,
    on_click=None,
) -> rx.Component:
    header = rx.vstack(
        rx.flex(
            rx.text(
                title,
                font_size="14px",
                font_weight="700",
                color=COLORS["text_primary"],
                line_height="1.2",
            ),
            rx.icon("chevron-right", size=16, color=COLORS["text_secondary"])
            if on_click is not None
            else rx.fragment(),
            justify="between",
            align="center",
            width="100%",
        ),
        chips if chips is not None else rx.fragment(),
        spacing="2",
        align="start",
        width="100%",
    )
    body = rx.box(
        chart,
        width="100%",
        flex_grow="1",
        display="flex",
        align_items="stretch",
        justify_content="center",
        min_height="0",
    )
    return rx.box(
        header,
        body,
        padding="18px",
        background="linear-gradient(180deg, rgba(26,26,36,0.96), rgba(21,21,30,0.96))",
        border_radius="12px",
        border=f"1px solid {COLORS['glass_border']}",
        cursor="pointer" if on_click is not None else "default",
        on_click=on_click,
        height="100%",
        min_height="336px",
        display="flex",
        flex_direction="column",
        gap="14px",
        box_shadow="0 18px 50px rgba(0, 0, 0, 0.18)",
        transition="border-color 0.16s ease, transform 0.16s ease, background 0.16s ease",
        _hover={
            "border_color": "rgba(139, 92, 246, 0.45)",
            "transform": "translateY(-1px)",
            "background": "linear-gradient(180deg, rgba(30,30,42,0.98), rgba(22,22,32,0.98))",
        }
        if on_click
        else {},
    )
