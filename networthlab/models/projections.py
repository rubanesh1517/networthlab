"""Projection and calculation result models."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class FinancialSnapshot(BaseModel):
    """Current financial state."""

    snapshot_date: date
    net_worth: Decimal
    total_assets: Decimal
    total_liabilities: Decimal

    # Asset breakdown
    investments: Decimal = Decimal(0)
    cash: Decimal = Decimal(0)
    real_estate: Decimal = Decimal(0)
    crypto: Decimal = Decimal(0)
    other_assets: Decimal = Decimal(0)

    # Liability breakdown
    loans: Decimal = Decimal(0)
    credit: Decimal = Decimal(0)
    other_liabilities: Decimal = Decimal(0)

    # Cash flow (monthly averages)
    monthly_income: Decimal = Decimal(0)
    monthly_expenses: Decimal = Decimal(0)
    monthly_savings: Decimal = Decimal(0)

    @property
    def savings_rate(self) -> float:
        """Calculate savings rate as percentage."""
        if self.monthly_income == 0:
            return 0.0
        return float(self.monthly_savings / self.monthly_income) * 100


class Projection(BaseModel):
    """Single year projection."""

    year: int
    net_worth: Decimal
    investments: Decimal
    loan_balance: Decimal
    fire_progress: float  # 0.0 to 1.0


class FIREResult(BaseModel):
    """FIRE calculation result."""

    fire_number: Decimal
    current_investments: Decimal
    annual_expenses: Decimal
    years_to_fire: int
    fire_year: int  # -1 if not achievable
    fire_progress: float  # 0.0 to 1.0

    @property
    def is_achievable(self) -> bool:
        """Check if FIRE is achievable within reasonable timeframe."""
        return self.fire_year > 0

    @property
    def is_already_fire(self) -> bool:
        """Check if already at FIRE number."""
        return self.years_to_fire == 0


class LoanPayoffResult(BaseModel):
    """Loan payoff calculation result."""

    account_id: int
    account_name: str
    current_balance: Decimal
    interest_rate: float
    monthly_payment: Decimal
    months_to_payoff: int
    payoff_date: date
    total_interest: Decimal

    @property
    def years_to_payoff(self) -> int:
        """Get years to payoff."""
        return self.months_to_payoff // 12

    @property
    def remaining_months(self) -> int:
        """Get remaining months after years."""
        return self.months_to_payoff % 12
