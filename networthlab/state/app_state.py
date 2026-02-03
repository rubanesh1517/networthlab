"""Main application state for Reflex."""

from decimal import Decimal

import reflex as rx

from networthlab.models import FinancialSnapshot, UserSettings
from networthlab.services import LunchMoneyService, calculate_fire, project_net_worth


class AppState(rx.State):
    """Global application state."""

    # User settings
    api_token: str = ""
    is_connected: bool = False
    error_message: str = ""

    # Financial data (stored as simple types for Reflex compatibility)
    accounts: list[dict] = []
    _snapshot: dict = {}
    projections: list[dict] = []
    _fire_result: dict = {}

    # Settings
    expected_return: float = 7.0  # Percentage for UI
    withdrawal_rate: float = 4.0  # Percentage for UI
    inflation_rate: float = 3.0  # Percentage for UI
    projection_years: int = 30

    # UI state
    is_loading: bool = False

    # Computed properties for display
    @rx.var
    def net_worth_display(self) -> str:
        if self._snapshot and "net_worth" in self._snapshot:
            value = float(self._snapshot["net_worth"])
            return f"${value:,.0f}"
        return "$0"

    @rx.var
    def investments_display(self) -> str:
        if self._snapshot and "investments" in self._snapshot:
            value = float(self._snapshot["investments"])
            return f"${value:,.0f}"
        return "$0"

    @rx.var
    def monthly_savings_display(self) -> str:
        if self._snapshot and "monthly_savings" in self._snapshot:
            value = float(self._snapshot["monthly_savings"])
            return f"${value:,.0f}"
        return "$0"

    @rx.var
    def fire_year_display(self) -> str:
        if self._fire_result and "fire_year" in self._fire_result:
            year = self._fire_result["fire_year"]
            if year > 0:
                return str(year)
            return "50+ years"
        return "—"

    @rx.var
    def fire_progress_percent(self) -> float:
        if self._fire_result and "fire_progress" in self._fire_result:
            return min(100.0, float(self._fire_result["fire_progress"]) * 100)
        return 0.0

    @rx.var
    def fire_progress_display(self) -> str:
        return f"{self.fire_progress_percent:.1f}%"

    @rx.var
    def fire_number_display(self) -> str:
        if self._fire_result and "fire_number" in self._fire_result:
            value = float(self._fire_result["fire_number"])
            return f"${value:,.0f}"
        return "$0"

    @rx.var
    def has_fire_result(self) -> bool:
        return bool(self._fire_result)

    @rx.var
    def expected_return_display(self) -> str:
        return f"Expected Return: {self.expected_return:.1f}%"

    @rx.var
    def withdrawal_rate_display(self) -> str:
        return f"Withdrawal Rate: {self.withdrawal_rate:.1f}%"

    @rx.var
    def inflation_rate_display(self) -> str:
        return f"Inflation Rate: {self.inflation_rate:.1f}%"

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
            self.accounts = [
                {
                    "id": a.id,
                    "name": a.name,
                    "type": a.type.value,
                    "balance": float(a.balance),
                    "balance_display": f"${float(a.balance):,.2f}",
                }
                for a in accounts
            ]

            # Build snapshot
            snapshot = service.build_snapshot()
            self._snapshot = {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in snapshot.model_dump().items()
            }

            # Calculate projections
            settings = UserSettings(
                lunch_money_token=self.api_token,
                expected_return=self.expected_return / 100,
                safe_withdrawal_rate=self.withdrawal_rate / 100,
                inflation_rate=self.inflation_rate / 100,
                projection_years=self.projection_years,
            )

            projections = project_net_worth(snapshot, settings)
            self.projections = [
                {k: float(v) if isinstance(v, Decimal) else v for k, v in p.model_dump().items()}
                for p in projections
            ]

            # Calculate FIRE
            fire_result = calculate_fire(
                current_investments=snapshot.investments,
                annual_savings=snapshot.monthly_savings * 12,
                annual_expenses=snapshot.monthly_expenses * 12,
                expected_return=self.expected_return / 100,
                withdrawal_rate=self.withdrawal_rate / 100,
                inflation_rate=self.inflation_rate / 100,
            )
            self._fire_result = {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in fire_result.model_dump().items()
            }

            self.is_connected = True

        except Exception as e:
            self.error_message = f"Failed to connect: {str(e)}"
            self.is_connected = False

        finally:
            self.is_loading = False

    def recalculate(self):
        """Recalculate projections with current settings."""
        if not self._snapshot:
            return

        self.is_loading = True

        try:
            # Reconstruct snapshot from stored data
            snapshot = FinancialSnapshot(
                snapshot_date=self._snapshot.get("snapshot_date"),
                net_worth=Decimal(str(self._snapshot.get("net_worth", 0))),
                total_assets=Decimal(str(self._snapshot.get("total_assets", 0))),
                total_liabilities=Decimal(str(self._snapshot.get("total_liabilities", 0))),
                investments=Decimal(str(self._snapshot.get("investments", 0))),
                cash=Decimal(str(self._snapshot.get("cash", 0))),
                real_estate=Decimal(str(self._snapshot.get("real_estate", 0))),
                crypto=Decimal(str(self._snapshot.get("crypto", 0))),
                other_assets=Decimal(str(self._snapshot.get("other_assets", 0))),
                loans=Decimal(str(self._snapshot.get("loans", 0))),
                credit=Decimal(str(self._snapshot.get("credit", 0))),
                other_liabilities=Decimal(str(self._snapshot.get("other_liabilities", 0))),
                monthly_income=Decimal(str(self._snapshot.get("monthly_income", 0))),
                monthly_expenses=Decimal(str(self._snapshot.get("monthly_expenses", 0))),
                monthly_savings=Decimal(str(self._snapshot.get("monthly_savings", 0))),
            )

            settings = UserSettings(
                lunch_money_token=self.api_token,
                expected_return=self.expected_return / 100,
                safe_withdrawal_rate=self.withdrawal_rate / 100,
                inflation_rate=self.inflation_rate / 100,
                projection_years=self.projection_years,
            )

            projections = project_net_worth(snapshot, settings)
            self.projections = [
                {k: float(v) if isinstance(v, Decimal) else v for k, v in p.model_dump().items()}
                for p in projections
            ]

            fire_result = calculate_fire(
                current_investments=snapshot.investments,
                annual_savings=snapshot.monthly_savings * 12,
                annual_expenses=snapshot.monthly_expenses * 12,
                expected_return=self.expected_return / 100,
                withdrawal_rate=self.withdrawal_rate / 100,
                inflation_rate=self.inflation_rate / 100,
            )
            self._fire_result = {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in fire_result.model_dump().items()
            }

        except Exception as e:
            self.error_message = f"Calculation error: {str(e)}"

        finally:
            self.is_loading = False

    def update_expected_return(self, value: list):
        """Update expected return and recalculate."""
        self.expected_return = value[0] if isinstance(value, list) else value
        self.recalculate()

    def update_withdrawal_rate(self, value: list):
        """Update withdrawal rate and recalculate."""
        self.withdrawal_rate = value[0] if isinstance(value, list) else value
        self.recalculate()

    def update_inflation_rate(self, value: list):
        """Update inflation rate and recalculate."""
        self.inflation_rate = value[0] if isinstance(value, list) else value
        self.recalculate()
