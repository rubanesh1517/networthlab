"""Status chips for exposure tiles: unclassified, leverage, stale, cache-stale."""

import reflex as rx

_BASE = {
    "padding": "2px 8px",
    "border_radius": "9999px",
    "font_size": "11px",
    "font_weight": "500",
    "letter_spacing": "0.02em",
}


def _chip(label: str, color: str, bg: str) -> rx.Component:
    return rx.box(
        rx.text(label, color=color),
        background=bg,
        **_BASE,
    )


def unclassified_chip() -> rx.Component:
    return _chip("Unclassified", color="#fbbf24", bg="rgba(245, 158, 11, 0.12)")


def leverage_chip() -> rx.Component:
    return _chip("Leverage", color="#f87171", bg="rgba(239, 68, 68, 0.12)")


def stale_override_chip() -> rx.Component:
    return _chip("Review override", color="#9ca3af", bg="rgba(255,255,255,0.06)")


def stale_cache_chip(minutes: int) -> rx.Component:
    return _chip(f"Stale by {minutes}m", color="#9ca3af", bg="rgba(255,255,255,0.06)")


def review_complex_chip() -> rx.Component:
    """Yellow chip: stockPosition > 1.0 but symbol not in complex_securities.yaml."""
    return _chip("Review complex", color="#fbbf24", bg="rgba(245, 158, 11, 0.12)")
