"""Market exposure page — full composition arrives in Task 14."""

import reflex as rx


def exposure_page() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("Exposure", size="6"),
            rx.text("This page is under construction."),
            spacing="3",
        ),
        height="100vh",
    )
