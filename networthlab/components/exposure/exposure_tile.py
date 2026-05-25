"""Reusable tile shell for each dimension."""

import reflex as rx

from ...styles.theme import COLORS


def exposure_tile(
    title: str,
    chart: rx.Component,
    chips: rx.Component | None = None,
    on_click=None,
) -> rx.Component:
    header = rx.flex(
        rx.text(
            title,
            font_size="13px",
            font_weight="600",
            color=COLORS["text_primary"],
            text_transform="uppercase",
            letter_spacing="0.04em",
        ),
        chips if chips is not None else rx.fragment(),
        justify="between",
        align="center",
        margin_bottom="10px",
        width="100%",
    )
    body = rx.box(
        chart,
        width="100%",
        flex_grow="1",
        display="flex",
        align_items="center",
        justify_content="center",
    )
    return rx.box(
        header,
        body,
        padding="16px",
        background=COLORS["bg_secondary"],
        border_radius="12px",
        border=f"1px solid {COLORS['glass_border']}",
        cursor="pointer" if on_click is not None else "default",
        on_click=on_click,
        height="100%",
        display="flex",
        flex_direction="column",
        _hover={"border_color": COLORS["accent_primary"]} if on_click else {},
    )
