"""Status chips for exposure tiles: unclassified, leverage, stale, cache-stale."""

import reflex as rx

_BASE = {
    "padding": "3px 8px",
    "border_radius": "9999px",
    "font_size": "10px",
    "font_weight": "600",
    "line_height": "1",
    "white_space": "nowrap",
}


def _chip(label: str, color: str, bg: str, border: str) -> rx.Component:
    return rx.box(
        rx.text(label, color=color),
        background=bg,
        border=border,
        **_BASE,
    )


def unclassified_chip() -> rx.Component:
    return _chip(
        "Unclassified",
        color="#fcd34d",
        bg="rgba(245, 158, 11, 0.10)",
        border="1px solid rgba(245, 158, 11, 0.22)",
    )


def leverage_chip() -> rx.Component:
    return _chip(
        "Leverage",
        color="#fca5a5",
        bg="rgba(239, 68, 68, 0.10)",
        border="1px solid rgba(239, 68, 68, 0.24)",
    )


def stale_override_chip() -> rx.Component:
    return _chip(
        "Review override",
        color="#cbd5e1",
        bg="rgba(148, 163, 184, 0.08)",
        border="1px solid rgba(148, 163, 184, 0.16)",
    )


def stale_cache_chip(minutes: int) -> rx.Component:
    return _chip(
        f"Stale by {minutes}m",
        color="#cbd5e1",
        bg="rgba(148, 163, 184, 0.08)",
        border="1px solid rgba(148, 163, 184, 0.16)",
    )


def review_complex_chip() -> rx.Component:
    """Yellow chip: stockPosition > 1.0 but symbol not in complex_securities.yaml."""
    return _chip(
        "Review complex",
        color="#fcd34d",
        bg="rgba(245, 158, 11, 0.10)",
        border="1px solid rgba(245, 158, 11, 0.22)",
    )
