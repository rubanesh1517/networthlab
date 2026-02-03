"""User settings models."""

from decimal import Decimal

from pydantic import BaseModel, Field


class LoanSettings(BaseModel):
    """Settings for a specific loan."""

    account_id: int
    interest_rate: float = Field(ge=0, le=1, description="Annual interest rate as decimal")
    extra_monthly_payment: Decimal = Decimal(0)


class UserSettings(BaseModel):
    """User configuration and preferences."""

    # Lunch Money API
    lunch_money_token: str = ""

    # FIRE assumptions
    safe_withdrawal_rate: float = Field(
        default=0.04, ge=0.02, le=0.10, description="Safe withdrawal rate (default 4%)"
    )
    expected_return: float = Field(
        default=0.07, ge=0.0, le=0.20, description="Expected annual investment return (default 7%)"
    )
    inflation_rate: float = Field(
        default=0.03, ge=0.0, le=0.10, description="Expected inflation rate (default 3%)"
    )

    # Loan settings
    loans: list[LoanSettings] = []

    # Display preferences
    currency: str = "USD"
    projection_years: int = Field(default=30, ge=5, le=50)
