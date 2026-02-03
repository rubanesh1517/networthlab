"""Account and transaction models."""

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


class AccountType(str, Enum):
    """Types of financial accounts."""

    CASH = "cash"
    INVESTMENT = "investment"
    LOAN = "loan"
    REAL_ESTATE = "real_estate"
    CRYPTO = "crypto"
    CREDIT = "credit"
    VEHICLE = "vehicle"
    OTHER_ASSET = "other_asset"
    OTHER_LIABILITY = "other_liability"


class Account(BaseModel):
    """Unified model for assets and plaid accounts from Lunch Money."""

    id: int
    name: str
    type: AccountType
    subtype: str | None = None
    balance: Decimal
    currency: str = "USD"
    institution: str | None = None
    source: str  # "asset" or "plaid"

    @property
    def is_asset(self) -> bool:
        """Check if this is an asset (positive net worth)."""
        return self.type not in (AccountType.LOAN, AccountType.CREDIT, AccountType.OTHER_LIABILITY)

    @property
    def is_liability(self) -> bool:
        """Check if this is a liability (negative net worth)."""
        return not self.is_asset


class Transaction(BaseModel):
    """Transaction from Lunch Money for trend analysis."""

    id: int
    date: date
    amount: Decimal
    category_id: int | None = None
    category_name: str | None = None
    is_income: bool = False
    payee: str | None = None
    recurring_id: int | None = None

    @property
    def is_expense(self) -> bool:
        """Check if this is an expense."""
        return not self.is_income


class RecurringItem(BaseModel):
    """Recurring income or expense."""

    id: int
    amount: Decimal
    cadence: str  # monthly, yearly, etc.
    category: str | None = None
    description: str | None = None
    is_income: bool = False
