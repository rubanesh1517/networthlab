"""Scenario add/edit form component."""

import reflex as rx

from ...styles.theme import COLORS


def form_input(
    label: str,
    placeholder: str,
    value: rx.Var[str],
    on_change: rx.EventHandler,
) -> rx.Component:
    """Styled form input."""
    return rx.vstack(
        rx.text(
            label,
            font_size="13px",
            font_weight="500",
            color=COLORS["text_secondary"],
        ),
        rx.input(
            placeholder=placeholder,
            value=value,
            on_change=on_change,
            width="100%",
            padding="12px 16px",
            border_radius="10px",
            background=COLORS["bg_tertiary"],
            border=f"1px solid {COLORS['glass_border']}",
            color=COLORS["text_primary"],
            font_size="14px",
            _focus={
                "border": f"1px solid {COLORS['accent_primary']}",
                "outline": "none",
            },
            _placeholder={
                "color": COLORS["text_secondary"],
            },
        ),
        spacing="2",
        width="100%",
        align="start",
    )


def color_picker(
    value: rx.Var[str],
    on_change: rx.EventHandler,
    available_colors: list[str],
) -> rx.Component:
    """Color selection component."""
    return rx.vstack(
        rx.text(
            "Chart Color",
            font_size="13px",
            font_weight="500",
            color=COLORS["text_secondary"],
        ),
        rx.hstack(
            *[
                rx.box(
                    width="32px",
                    height="32px",
                    border_radius="8px",
                    background=color,
                    cursor="pointer",
                    border=rx.cond(
                        value == color,
                        "2px solid white",
                        "2px solid transparent",
                    ),
                    _hover={
                        "opacity": "0.8",
                    },
                    on_click=lambda c=color: on_change(c),
                )
                for color in available_colors
            ],
            spacing="2",
        ),
        spacing="2",
        width="100%",
        align="start",
    )


def scenario_form() -> rx.Component:
    """Add/edit scenario form modal."""
    from ...state.projection_state import ProjectionState

    return rx.cond(
        ProjectionState.show_form,
        rx.box(
            rx.box(
                rx.vstack(
                    # Header
                    rx.hstack(
                        rx.text(
                            rx.cond(
                                ProjectionState.editing_scenario_id != "",
                                "Edit Scenario",
                                "Add New Scenario",
                            ),
                            font_size="18px",
                            font_weight="600",
                            color=COLORS["text_primary"],
                        ),
                        rx.spacer(),
                        rx.icon(
                            "x",
                            size=20,
                            color=COLORS["text_secondary"],
                            cursor="pointer",
                            on_click=ProjectionState.toggle_form,
                            _hover={"color": COLORS["text_primary"]},
                        ),
                        width="100%",
                        align="center",
                    ),
                    # Form fields
                    form_input(
                        "Scenario Name",
                        "e.g., Aggressive Growth",
                        ProjectionState.form_name,
                        ProjectionState.set_form_name,
                    ),
                    rx.hstack(
                        form_input(
                            "Starting Amount",
                            "$100,000",
                            ProjectionState.form_starting_amount,
                            ProjectionState.set_form_starting_amount,
                        ),
                        form_input(
                            "Monthly Contribution",
                            "$2,000",
                            ProjectionState.form_monthly_contribution,
                            ProjectionState.set_form_monthly_contribution,
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    rx.hstack(
                        form_input(
                            "Annual Return (%)",
                            "7.0",
                            ProjectionState.form_annual_return,
                            ProjectionState.set_form_annual_return,
                        ),
                        form_input(
                            "Years to Project",
                            "30",
                            ProjectionState.form_years,
                            ProjectionState.set_form_years,
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    # Color picker
                    rx.vstack(
                        rx.text(
                            "Chart Color",
                            font_size="13px",
                            font_weight="500",
                            color=COLORS["text_secondary"],
                        ),
                        rx.hstack(
                            rx.foreach(
                                ProjectionState.available_colors,
                                lambda color: rx.box(
                                    width="32px",
                                    height="32px",
                                    border_radius="8px",
                                    background=color,
                                    cursor="pointer",
                                    border=rx.cond(
                                        ProjectionState.form_color == color,
                                        "2px solid white",
                                        "2px solid transparent",
                                    ),
                                    _hover={"opacity": "0.8"},
                                    on_click=lambda: ProjectionState.set_form_color(color),
                                ),
                            ),
                            spacing="2",
                        ),
                        spacing="2",
                        width="100%",
                        align="start",
                    ),
                    # Action buttons
                    rx.hstack(
                        rx.button(
                            "Cancel",
                            on_click=ProjectionState.toggle_form,
                            padding="12px 24px",
                            border_radius="10px",
                            background="transparent",
                            border=f"1px solid {COLORS['glass_border']}",
                            color=COLORS["text_secondary"],
                            font_size="14px",
                            font_weight="500",
                            cursor="pointer",
                            _hover={
                                "background": "rgba(255, 255, 255, 0.05)",
                            },
                        ),
                        rx.button(
                            rx.cond(
                                ProjectionState.editing_scenario_id != "",
                                "Update Scenario",
                                "Add Scenario",
                            ),
                            on_click=ProjectionState.save_or_update_scenario,
                            padding="12px 24px",
                            border_radius="10px",
                            background=COLORS["accent_primary"],
                            color="white",
                            font_size="14px",
                            font_weight="500",
                            border="none",
                            cursor="pointer",
                            _hover={
                                "opacity": "0.9",
                            },
                        ),
                        spacing="3",
                        width="100%",
                        justify="end",
                        padding_top="8px",
                    ),
                    spacing="4",
                    width="100%",
                ),
                max_width="500px",
                width="90%",
                padding="24px",
                border_radius="16px",
                background=COLORS["bg_secondary"],
                border=f"1px solid {COLORS['glass_border']}",
            ),
            position="fixed",
            top="0",
            left="0",
            right="0",
            bottom="0",
            background="rgba(0, 0, 0, 0.7)",
            backdrop_filter="blur(4px)",
            display="flex",
            align_items="center",
            justify_content="center",
            z_index="1000",
        ),
    )
