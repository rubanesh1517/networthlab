"""Main application state for Reflex."""

import reflex as rx

from networthlab.models import Account, FIREResult, FinancialSnapshot, Projection, UserSettings
from networthlab.services import LunchMoneyService, calculate_fire, project_net_worth


class AppState(rx.State):
    """Global application state."""

    # User settings
    api_token: str = ""
    is_connected: bool = False
    error_message: str = ""

    # Financial data
    accounts: list[dict] = []
    snapshot: dict = {}
    projections: list[dict] = []
    fire_result: dict = {}

    # Settings
    expected_return: float = 7.0  # Percentage for UI
    withdrawal_rate: float = 4.0  # Percentage for UI
    inflation_rate: float = 3.0  # Percentage for UI
    projection_years: int = 30

    # UI state
    is_loading: bool = False

    def set_api_token(self, token: str):
        """Set the API token."""
        self.api_token = token
        self.error_message = ""

    def connect_to_lunch_money(self):
        """Connect to Lunch Money and fetch data."""
        if not self.api_token:
            self.error_message = "Please enter your Lunch Money API token"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            service = LunchMoneyService(self.api_token)

            # Fetch accounts
            accounts = service.get_accounts()
            self.accounts = [a.model_dump() for a in accounts]

            # Build snapshot
            snapshot = service.build_snapshot()
            self.snapshot = snapshot.model_dump()

            # Calculate projections
            settings = UserSettings(
                lunch_money_token=self.api_token,
                expected_return=self.expected_return / 100,
                safe_withdrawal_rate=self.withdrawal_rate / 100,
                inflation_rate=self.inflation_rate / 100,
                projection_years=self.projection_years,
            )

            projections = project_net_worth(snapshot, settings)
            self.projections = [p.model_dump() for p in projections]

            # Calculate FIRE
            fire_result = calculate_fire(
                current_investments=snapshot.investments,
                annual_savings=snapshot.monthly_savings * 12,
                annual_expenses=snapshot.monthly_expenses * 12,
                expected_return=self.expected_return / 100,
                withdrawal_rate=self.withdrawal_rate / 100,
                inflation_rate=self.inflation_rate / 100,
            )
            self.fire_result = fire_result.model_dump()

            self.is_connected = True

        except Exception as e:
            self.error_message = f"Failed to connect: {str(e)}"
            self.is_connected = False

        finally:
            self.is_loading = False

    def recalculate(self):
        """Recalculate projections with current settings."""
        if not self.snapshot:
            return

        self.is_loading = True

        try:
            from decimal import Decimal

            snapshot = FinancialSnapshot(**{
                k: Decimal(str(v)) if isinstance(v, (int, float)) and k != "savings_rate" else v
                for k, v in self.snapshot.items()
            })

            settings = UserSettings(
                lunch_money_token=self.api_token,
                expected_return=self.expected_return / 100,
                safe_withdrawal_rate=self.withdrawal_rate / 100,
                inflation_rate=self.inflation_rate / 100,
                projection_years=self.projection_years,
            )

            projections = project_net_worth(snapshot, settings)
            self.projections = [p.model_dump() for p in projections]

            fire_result = calculate_fire(
                current_investments=snapshot.investments,
                annual_savings=snapshot.monthly_savings * 12,
                annual_expenses=snapshot.monthly_expenses * 12,
                expected_return=self.expected_return / 100,
                withdrawal_rate=self.withdrawal_rate / 100,
                inflation_rate=self.inflation_rate / 100,
            )
            self.fire_result = fire_result.model_dump()

        except Exception as e:
            self.error_message = f"Calculation error: {str(e)}"

        finally:
            self.is_loading = False

    def update_expected_return(self, value: float):
        """Update expected return and recalculate."""
        self.expected_return = value
        self.recalculate()

    def update_withdrawal_rate(self, value: float):
        """Update withdrawal rate and recalculate."""
        self.withdrawal_rate = value
        self.recalculate()

    def update_inflation_rate(self, value: float):
        """Update inflation rate and recalculate."""
        self.inflation_rate = value
        self.recalculate()
