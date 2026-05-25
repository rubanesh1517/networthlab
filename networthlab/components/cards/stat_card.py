"""Stat card component with trend indicator."""

import reflex as rx

from ...styles.theme import COLORS


def stat_card(
    title: str,
    value: str | rx.Var[str],
    icon: str = "wallet",
    color: str = "purple",
    subtitle: str | rx.Var[str] = "",
    trend: float | None = None,
    width: str | None = None,
) -> rx.Component:
    """
    Glassmorphism stat card with optional trend indicator.

    Args:
        title: Card title
        value: Main value to display
        icon: Lucide icon name
        color: Accent color (purple, blue, green, amber, red)
        subtitle: Optional subtitle text
        trend: Percentage change (positive/negative), static value only
    """
    color_map = {
        "purple": COLORS["accent_primary"],
        "blue": COLORS["accent_secondary"],
        "green": COLORS["accent_success"],
        "amber": COLORS["accent_warning"],
        "red": COLORS["accent_danger"],
    }

    accent_color = color_map.get(color, COLORS["accent_primary"])

    # Build trend component if provided
    trend_component = rx.fragment()
    if trend is not None:
        is_positive = trend >= 0
        trend_component = rx.hstack(
            rx.icon(
                "trending-up" if is_positive else "trending-down",
                size=14,
                color=COLORS["accent_success"] if is_positive else COLORS["accent_danger"],
            ),
            rx.text(
                f"+{trend}%" if is_positive else f"{trend}%",
                font_size="12px",
                font_weight="500",
                color=COLORS["accent_success"] if is_positive else COLORS["accent_danger"],
            ),
            spacing="1",
            align="center",
            padding="4px 8px",
            border_radius="6px",
            background="rgba(16, 185, 129, 0.1)" if is_positive else "rgba(239, 68, 68, 0.1)",
        )

    # Build subtitle component — must use rx.cond so Reflex Vars work,
    # not just Python str (e.g. the Exposure KPI cards pass dynamic Vars).
    subtitle_component = rx.cond(
        subtitle != "",
        rx.text(
            subtitle,
            font_size="12px",
            color=COLORS["text_secondary"],
        ),
        rx.fragment(),
    )

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon(
                        icon,
                        size=20,
                        color=accent_color,
                    ),
                    width="40px",
                    height="40px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    border_radius="10px",
                    background=f"rgba({_hex_to_rgb(accent_color)}, 0.15)",
                ),
                rx.spacer(),
                trend_component,
                width="100%",
                align="center",
            ),
            rx.vstack(
                rx.text(
                    title,
                    font_size="13px",
                    color=COLORS["text_secondary"],
                    font_weight="500",
                ),
                rx.text(
                    value,
                    font_size="28px",
                    font_weight="700",
                    color=COLORS["text_primary"],
                    line_height="1.2",
                ),
                subtitle_component,
                spacing="1",
                align="start",
                width="100%",
            ),
            spacing="4",
            width="100%",
        ),
        padding="20px",
        border_radius="16px",
        background=COLORS["glass_bg"],
        backdrop_filter="blur(24px)",
        border=f"1px solid {COLORS['glass_border']}",
        _hover={
            "border": "1px solid rgba(139, 92, 246, 0.3)",
            "transform": "translateY(-2px)",
        },
        transition="all 0.2s ease",
        flex="1" if width is None else None,
        min_width="200px" if width is None else None,
        width=width,
    )


def _hex_to_rgb(hex_color: str) -> str:
    """Convert hex color to RGB string."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"{r}, {g}, {b}"
