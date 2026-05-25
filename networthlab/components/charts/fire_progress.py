"""FIRE progress radial chart component."""

import reflex as rx
from ...styles.theme import COLORS, GRADIENTS


def fire_progress_ring(
    progress: float | rx.Var[float],
    fire_number: str | rx.Var[str],
    years_to_fire: int | rx.Var[int],
    fire_age: int | rx.Var[int],
) -> rx.Component:
    """
    Radial progress ring showing FIRE progress.

    Args:
        progress: Progress percentage (0-100)
        fire_number: Formatted FIRE target amount
        years_to_fire: Years until FIRE
        fire_age: Age at FIRE
    """
    # Create data for the radial chart
    return rx.box(
        rx.vstack(
            # Custom CSS radial progress
            rx.box(
                rx.box(
                    rx.vstack(
                        rx.text(
                            progress,
                            font_size="42px",
                            font_weight="700",
                            style={
                                "background": GRADIENTS["primary"],
                                "background_clip": "text",
                                "-webkit-background-clip": "text",
                                "color": "transparent",
                            },
                        ),
                        rx.text(
                            "% to FIRE",
                            font_size="14px",
                            color=COLORS["text_secondary"],
                        ),
                        spacing="0",
                        align="center",
                    ),
                    position="absolute",
                    top="50%",
                    left="50%",
                    transform="translate(-50%, -50%)",
                ),
                width="200px",
                height="200px",
                border_radius="50%",
                background=f"conic-gradient({COLORS['accent_primary']} {progress}%, {COLORS['bg_tertiary']} 0%)",
                position="relative",
                _before={
                    "content": '""',
                    "position": "absolute",
                    "top": "10px",
                    "left": "10px",
                    "right": "10px",
                    "bottom": "10px",
                    "borderRadius": "50%",
                    "background": COLORS["bg_secondary"],
                },
            ),
            # Stats below the ring
            rx.hstack(
                rx.vstack(
                    rx.text(
                        fire_number,
                        font_size="18px",
                        font_weight="600",
                        color=COLORS["text_primary"],
                    ),
                    rx.text(
                        "FIRE Target",
                        font_size="12px",
                        color=COLORS["text_secondary"],
                    ),
                    spacing="0",
                    align="center",
                ),
                rx.box(
                    width="1px",
                    height="40px",
                    background=COLORS["glass_border"],
                ),
                rx.vstack(
                    rx.text(
                        years_to_fire,
                        font_size="18px",
                        font_weight="600",
                        color=COLORS["text_primary"],
                    ),
                    rx.text(
                        "Years to Go",
                        font_size="12px",
                        color=COLORS["text_secondary"],
                    ),
                    spacing="0",
                    align="center",
                ),
                rx.box(
                    width="1px",
                    height="40px",
                    background=COLORS["glass_border"],
                ),
                rx.vstack(
                    rx.text(
                        fire_age,
                        font_size="18px",
                        font_weight="600",
                        color=COLORS["text_primary"],
                    ),
                    rx.text(
                        "FIRE Age",
                        font_size="12px",
                        color=COLORS["text_secondary"],
                    ),
                    spacing="0",
                    align="center",
                ),
                spacing="6",
                padding_top="24px",
            ),
            spacing="4",
            align="center",
        ),
        padding="24px",
    )


def fire_mini_progress(
    progress: float | rx.Var[float],
    label: str = "FIRE Progress",
) -> rx.Component:
    """
    Compact horizontal progress bar for FIRE.

    Args:
        progress: Progress percentage (0-100)
        label: Label text
    """
    return rx.vstack(
        rx.hstack(
            rx.text(
                label,
                font_size="13px",
                color=COLORS["text_secondary"],
            ),
            rx.spacer(),
            rx.text(
                f"{progress:.1f}%",
                font_size="13px",
                font_weight="500",
                color=COLORS["text_primary"],
            ),
            width="100%",
        ),
        rx.box(
            rx.box(
                width=f"{progress}%",
                height="100%",
                background=GRADIENTS["primary"],
                border_radius="4px",
                transition="width 0.5s ease",
            ),
            width="100%",
            height="8px",
            background=COLORS["bg_tertiary"],
            border_radius="4px",
            overflow="hidden",
        ),
        spacing="2",
        width="100%",
    )
