"""NetWorthLab - Main application entry point with multi-page routing."""

import reflex as rx

from .pages.dashboard import dashboard
from .pages.exposure import exposure_page
from .pages.fire import fire_calculator
from .pages.loans import loan_tracker
from .pages.projections import projections
from .pages.settings import settings
from .state.app_state import AppState
from .state.exposure_state import ExposureState

# Create the app with styling
app = rx.App(
    theme=rx.theme(
        appearance="dark",
        has_background=True,
        radius="medium",
        accent_color="violet",
    ),
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
    ],
    style={
        "font_family": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "background_color": "#0f0f14",
        "min_height": "100vh",
    },
)


# Define page load handlers
class PageState(AppState):
    """Page-specific state handlers."""

    def on_dashboard_load(self) -> None:
        """Handle dashboard page load."""
        self.current_page = "dashboard"

    def on_exposure_load(self) -> None:
        """Handle exposure page load."""
        self.current_page = "exposure"

    def on_fire_load(self) -> None:
        """Handle FIRE page load."""
        self.current_page = "fire"

    def on_loans_load(self) -> None:
        """Handle loans page load."""
        self.current_page = "loans"

    def on_projections_load(self) -> None:
        """Handle projections page load."""
        self.current_page = "projections"

    def on_settings_load(self) -> None:
        """Handle settings page load."""
        self.current_page = "settings"


# Add pages with routes and on_load handlers
app.add_page(
    dashboard,
    route="/",
    title="Dashboard | NetWorthLab",
    on_load=PageState.on_dashboard_load,
)
app.add_page(
    exposure_page,
    route="/exposure",
    title="Exposure | NetWorthLab",
    on_load=[PageState.on_exposure_load, ExposureState.on_load],
)
app.add_page(
    fire_calculator,
    route="/fire",
    title="FIRE Calculator | NetWorthLab",
    on_load=PageState.on_fire_load,
)
app.add_page(
    loan_tracker,
    route="/loans",
    title="Loan Tracker | NetWorthLab",
    on_load=PageState.on_loans_load,
)
app.add_page(
    projections,
    route="/projections",
    title="Projections | NetWorthLab",
    on_load=PageState.on_projections_load,
)
app.add_page(
    settings,
    route="/settings",
    title="Settings | NetWorthLab",
    on_load=PageState.on_settings_load,
)
