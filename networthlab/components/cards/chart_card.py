"""Chart container card component."""

import reflex as rx
from ...styles.theme import COLORS


def chart_card(
    title: str,
    *children: rx.Component,
    subtitle: str = "",
    action: rx.Component | None = None,
    height: str = "400px",
    width: str | None = None,
) -> rx.Component:
    """
    Glassmorphism card container for charts.

    Args:
        title: Card title
        children: Chart components to render inside
        subtitle: Optional subtitle
        action: Optional action button/component
        height: Card height
    """
    # Build subtitle component
    subtitle_component = rx.fragment()
    if subtitle:
        subtitle_component = rx.text(
            subtitle,
            font_size="12px",
            color=COLORS["text_secondary"],
        )

    # Build action component
    action_component = rx.fragment()
    if action is not None:
        action_component = action

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text(
                        title,
                        font_size="16px",
                        font_weight="600",
                        color=COLORS["text_primary"],
                    ),
                    subtitle_component,
                    spacing="1",
                    align="start",
                ),
                rx.spacer(),
                action_component,
                width="100%",
                align="center",
            ),
            rx.box(
                *children,
                width="100%",
                height="100%",
                flex="1",
                min_height="0",
            ),
            spacing="4",
            height="100%",
            width="100%",
        ),
        padding="24px",
        border_radius="16px",
        background=COLORS["glass_bg"],
        backdrop_filter="blur(24px)",
        border=f"1px solid {COLORS['glass_border']}",
        height=height,
        flex="1" if width is None else None,
        min_width="300px" if width is None else None,
        width=width,
    )
