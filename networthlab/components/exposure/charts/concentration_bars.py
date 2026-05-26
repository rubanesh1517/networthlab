"""Compact bar list for the top position-concentration view."""

import reflex as rx

from ....styles.theme import COLORS


def _position_row(row: rx.Var) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                row["name"],
                font_size="12px",
                font_weight="600",
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
                font_size="11px",
                color=COLORS["text_secondary"],
                width="48px",
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
        ),
        rx.box(
            rx.box(
                width=row["bar_width"],
                height="100%",
                background=row["bar_color"],
                border_radius="999px",
            ),
            width="100%",
            height="6px",
            background="rgba(255,255,255,0.06)",
            border_radius="999px",
            overflow="hidden",
        ),
        spacing="1",
        width="100%",
    )


def concentration_bars(data: rx.Var, height: int = 280) -> rx.Component:
    return rx.vstack(
        rx.foreach(data, _position_row),
        spacing="3",
        width="100%",
        height=f"{height}px",
        overflow_y="auto",
        padding_right="4px",
    )
