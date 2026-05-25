"""Projections page for scenario comparison."""

import reflex as rx
from ..components.layout.page_wrapper import page_wrapper
from ..components.cards.chart_card import chart_card
from ..components.forms.scenario_form import scenario_form
from ..state.projection_state import ProjectionState
from ..styles.theme import COLORS, CHART_COLORS


def scenario_card(scenario: dict) -> rx.Component:
    """Individual scenario display card."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    width="12px",
                    height="12px",
                    border_radius="3px",
                    background=scenario.get("color", COLORS["accent_primary"]),
                ),
                rx.text(
                    scenario["name"],
                    font_size="15px",
                    font_weight="600",
                    color=COLORS["text_primary"],
                ),
                rx.spacer(),
                rx.hstack(
                    rx.icon(
                        "pencil",
                        size=14,
                        color=COLORS["text_secondary"],
                        cursor="pointer",
                        on_click=lambda: ProjectionState.edit_scenario(scenario["id"]),
                        _hover={"color": COLORS["accent_primary"]},
                    ),
                    rx.icon(
                        "trash-2",
                        size=14,
                        color=COLORS["text_secondary"],
                        cursor="pointer",
                        on_click=lambda: ProjectionState.delete_scenario(scenario["id"]),
                        _hover={"color": COLORS["accent_danger"]},
                    ),
                    spacing="2",
                ),
                width="100%",
                align="center",
            ),
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "Starting",
                        font_size="11px",
                        color=COLORS["text_secondary"],
                    ),
                    rx.text(
                        f"${scenario['starting_amount']:,.0f}",
                        font_size="13px",
                        font_weight="500",
                        color=COLORS["text_primary"],
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.vstack(
                    rx.text(
                        "Monthly",
                        font_size="11px",
                        color=COLORS["text_secondary"],
                    ),
                    rx.text(
                        f"${scenario['monthly_contribution']:,.0f}",
                        font_size="13px",
                        font_weight="500",
                        color=COLORS["text_primary"],
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.vstack(
                    rx.text(
                        "Return",
                        font_size="11px",
                        color=COLORS["text_secondary"],
                    ),
                    rx.text(
                        f"{scenario['annual_return']}%",
                        font_size="13px",
                        font_weight="500",
                        color=COLORS["text_primary"],
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.vstack(
                    rx.text(
                        "Years",
                        font_size="11px",
                        color=COLORS["text_secondary"],
                    ),
                    rx.text(
                        f"{scenario['years']}",
                        font_size="13px",
                        font_weight="500",
                        color=COLORS["text_primary"],
                    ),
                    spacing="0",
                    align="start",
                ),
                spacing="5",
                width="100%",
                padding_top="12px",
            ),
            spacing="0",
            width="100%",
        ),
        padding="16px",
        border_radius="10px",
        background="rgba(255, 255, 255, 0.02)",
        border=f"1px solid {COLORS['glass_border']}",
        _hover={
            "border": "1px solid rgba(139, 92, 246, 0.2)",
        },
        transition="all 0.2s ease",
    )


def summary_card(summary: dict) -> rx.Component:
    """Scenario summary result card."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    width="10px",
                    height="10px",
                    border_radius="2px",
                    background=summary.get("color", COLORS["accent_primary"]),
                ),
                rx.text(
                    summary["name"],
                    font_size="14px",
                    font_weight="600",
                    color=COLORS["text_primary"],
                ),
                spacing="2",
                align="center",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("Final Value:", font_size="12px", color=COLORS["text_secondary"]),
                    rx.spacer(),
                    rx.text(
                        summary["final_value"],
                        font_size="14px",
                        font_weight="600",
                        color=COLORS["accent_success"],
                    ),
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Total Contributed:", font_size="12px", color=COLORS["text_secondary"]),
                    rx.spacer(),
                    rx.text(
                        summary["total_contributions"],
                        font_size="12px",
                        color=COLORS["text_primary"],
                    ),
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Interest Earned:", font_size="12px", color=COLORS["text_secondary"]),
                    rx.spacer(),
                    rx.text(
                        summary["interest_earned"],
                        font_size="12px",
                        color=COLORS["accent_primary"],
                    ),
                    width="100%",
                ),
                spacing="2",
                width="100%",
                padding_top="8px",
            ),
            spacing="2",
            width="100%",
        ),
        padding="16px",
        border_radius="10px",
        background="rgba(255, 255, 255, 0.02)",
        border=f"1px solid {COLORS['glass_border']}",
    )


def projection_chart(data: rx.Var, scenario_names: list[str]) -> rx.Component:
    """Multi-scenario projection chart."""
    lines = []
    for i, name in enumerate(scenario_names if isinstance(scenario_names, list) else []):
        lines.append(
            rx.recharts.line(
                data_key=name,
                stroke=CHART_COLORS[i % len(CHART_COLORS)],
                stroke_width=2,
                dot=False,
                name=name,
            )
        )

    return rx.recharts.line_chart(
        *lines,
        rx.recharts.x_axis(
            data_key="year",
            stroke=COLORS["text_secondary"],
            font_size=12,
            tick_line=False,
            axis_line=False,
        ),
        rx.recharts.y_axis(
            stroke=COLORS["text_secondary"],
            font_size=12,
            tick_line=False,
            axis_line=False,
            custom_attrs={"tickFormatter": rx.Var("(value) => '$' + (value/1000000).toFixed(1) + 'M'")},
        ),
        rx.recharts.cartesian_grid(
            stroke_dasharray="3 3",
            stroke="rgba(255,255,255,0.05)",
            vertical=False,
        ),
        rx.recharts.graphing_tooltip(
            content_style={
                "backgroundColor": COLORS["bg_secondary"],
                "border": f"1px solid {COLORS['glass_border']}",
                "borderRadius": "8px",
                "color": COLORS["text_primary"],
            },
            formatter=rx.Var("(value, name) => ['$' + value.toLocaleString(), name]"),
        ),
        rx.recharts.legend(
            wrapper_style={"paddingTop": "20px"},
        ),
        data=data,
        height=350,
        width="100%",
        margin={"top": 10, "right": 10, "left": 0, "bottom": 0},
    )


def projections() -> rx.Component:
    """Projections page component."""
    return page_wrapper(
        "Projections",
        "Compare different financial scenarios",
        # Include the scenario form modal
        scenario_form(),
        # Main content
        rx.hstack(
            # Scenarios list
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "Scenarios",
                            font_size="16px",
                            font_weight="600",
                            color=COLORS["text_primary"],
                        ),
                        rx.spacer(),
                        rx.hstack(
                            rx.cond(
                                ProjectionState.scenarios.length() == 0,
                                rx.button(
                                    "Add Defaults",
                                    on_click=ProjectionState.add_default_scenarios,
                                    padding="6px 12px",
                                    border_radius="6px",
                                    background="transparent",
                                    border=f"1px solid {COLORS['glass_border']}",
                                    color=COLORS["text_secondary"],
                                    font_size="12px",
                                    cursor="pointer",
                                    _hover={
                                        "background": "rgba(255, 255, 255, 0.05)",
                                    },
                                ),
                            ),
                            rx.button(
                                rx.hstack(
                                    rx.icon("plus", size=14),
                                    rx.text("Add"),
                                    spacing="1",
                                ),
                                on_click=ProjectionState.toggle_form,
                                padding="6px 12px",
                                border_radius="6px",
                                background=COLORS["accent_primary"],
                                color="white",
                                font_size="12px",
                                border="none",
                                cursor="pointer",
                                _hover={
                                    "opacity": "0.9",
                                },
                            ),
                            spacing="2",
                        ),
                        width="100%",
                        align="center",
                    ),
                    rx.cond(
                        ProjectionState.scenarios.length() > 0,
                        rx.vstack(
                            rx.foreach(
                                ProjectionState.scenarios,
                                scenario_card,
                            ),
                            spacing="2",
                            width="100%",
                            padding_top="16px",
                        ),
                        rx.vstack(
                            rx.icon(
                                "line-chart",
                                size=40,
                                color=COLORS["text_secondary"],
                            ),
                            rx.text(
                                "No scenarios yet",
                                font_size="14px",
                                color=COLORS["text_secondary"],
                            ),
                            rx.text(
                                "Add a scenario or load defaults to compare projections",
                                font_size="12px",
                                color=COLORS["text_secondary"],
                                text_align="center",
                            ),
                            spacing="2",
                            align="center",
                            padding="32px 16px",
                            width="100%",
                        ),
                    ),
                    spacing="0",
                    width="100%",
                ),
                padding="20px",
                border_radius="16px",
                background=COLORS["glass_bg"],
                backdrop_filter="blur(24px)",
                border=f"1px solid {COLORS['glass_border']}",
                width="350px",
                min_width="350px",
            ),
            # Chart and results
            rx.vstack(
                rx.cond(
                    ProjectionState.scenarios.length() > 0,
                    rx.vstack(
                        # Comparison chart
                        chart_card(
                            "Scenario Comparison",
                            rx.recharts.line_chart(
                                rx.recharts.line(
                                    data_key="Conservative",
                                    stroke=CHART_COLORS[1],
                                    stroke_width=2,
                                    dot=False,
                                ),
                                rx.recharts.line(
                                    data_key="Moderate",
                                    stroke=CHART_COLORS[0],
                                    stroke_width=2,
                                    dot=False,
                                ),
                                rx.recharts.line(
                                    data_key="Aggressive",
                                    stroke=CHART_COLORS[2],
                                    stroke_width=2,
                                    dot=False,
                                ),
                                rx.recharts.x_axis(
                                    data_key="year",
                                    stroke=COLORS["text_secondary"],
                                    font_size=12,
                                    tick_line=False,
                                    axis_line=False,
                                ),
                                rx.recharts.y_axis(
                                    stroke=COLORS["text_secondary"],
                                    font_size=12,
                                    tick_line=False,
                                    axis_line=False,
                                    custom_attrs={"tickFormatter": rx.Var("(value) => '$' + (value/1000000).toFixed(1) + 'M'")},
                                ),
                                rx.recharts.cartesian_grid(
                                    stroke_dasharray="3 3",
                                    stroke="rgba(255,255,255,0.05)",
                                    vertical=False,
                                ),
                                rx.recharts.graphing_tooltip(
                                    content_style={
                                        "backgroundColor": COLORS["bg_secondary"],
                                        "border": f"1px solid {COLORS['glass_border']}",
                                        "borderRadius": "8px",
                                        "color": COLORS["text_primary"],
                                    },
                                    formatter=rx.Var("(value, name) => ['$' + (value?.toLocaleString() || 0), name]"),
                                ),
                                rx.recharts.legend(
                                    wrapper_style={"paddingTop": "10px"},
                                ),
                                data=ProjectionState.comparison_chart_data,
                                height=300,
                                width="100%",
                            ),
                            subtitle="Side-by-side projection comparison",
                            height="400px",
                            width="100%",
                        ),
                        # Results summary
                        rx.box(
                            rx.vstack(
                                rx.text(
                                    "Final Results",
                                    font_size="16px",
                                    font_weight="600",
                                    color=COLORS["text_primary"],
                                    padding_bottom="12px",
                                ),
                                rx.hstack(
                                    rx.foreach(
                                        ProjectionState.scenario_summaries,
                                        summary_card,
                                    ),
                                    spacing="3",
                                    width="100%",
                                    flex_wrap="wrap",
                                ),
                                width="100%",
                            ),
                            padding="20px",
                            border_radius="16px",
                            background=COLORS["glass_bg"],
                            backdrop_filter="blur(24px)",
                            border=f"1px solid {COLORS['glass_border']}",
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    # Empty state
                    rx.box(
                        rx.vstack(
                            rx.icon(
                                "bar-chart-2",
                                size=64,
                                color=COLORS["text_secondary"],
                            ),
                            rx.text(
                                "Create scenarios to see projections",
                                font_size="16px",
                                color=COLORS["text_secondary"],
                            ),
                            rx.text(
                                "Compare different investment strategies side by side",
                                font_size="14px",
                                color=COLORS["text_secondary"],
                            ),
                            spacing="3",
                            align="center",
                            padding="80px 40px",
                        ),
                        border_radius="16px",
                        background=COLORS["glass_bg"],
                        backdrop_filter="blur(24px)",
                        border=f"1px solid {COLORS['glass_border']}",
                        width="100%",
                    ),
                ),
                flex="1",
                width="100%",
            ),
            spacing="4",
            width="100%",
            align="start",
        ),
    )
