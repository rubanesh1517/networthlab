"""Lunch Money API service wrapper."""

from datetime import date, timedelta
from decimal import Decimal

import httpx
from lunchable import LunchMoney

from networthlab.models.accounts import Account, AccountType, RecurringItem, Transaction
from networthlab.models.projections import FinancialSnapshot


class LunchMoneyService:
    """Service for interacting with Lunch Money API."""

    TYPE_MAPPING = {
        "cash": AccountType.CASH,
        "credit": AccountType.CREDIT,
        "investment": AccountType.INVESTMENT,
        "real estate": AccountType.REAL_ESTATE,
        "loan": AccountType.LOAN,
        "vehicle": AccountType.VEHICLE,
        "cryptocurrency": AccountType.CRYPTO,
        "other liability": AccountType.OTHER_LIABILITY,
        "other asset": AccountType.OTHER_ASSET,
        "employee compensation": AccountType.OTHER_ASSET,
        # Plaid subtypes
        "checking": AccountType.CASH,
        "savings": AccountType.CASH,
        "brokerage": AccountType.INVESTMENT,
        "401k": AccountType.INVESTMENT,
        "ira": AccountType.INVESTMENT,
        "mortgage": AccountType.LOAN,
        "student": AccountType.LOAN,
        "auto": AccountType.LOAN,
        # Plaid types
        "depository": AccountType.CASH,
        "credit": AccountType.CREDIT,
        "loan": AccountType.LOAN,
        "investment": AccountType.INVESTMENT,
    }

    def __init__(self, access_token: str):
        """Initialize with Lunch Money access token."""
        self.client = LunchMoney(access_token=access_token)
        self.access_token = access_token

    def get_accounts(self) -> list[Account]:
        """Fetch all accounts (assets + plaid accounts)."""
        accounts = []

        # Get manual assets
        try:
            assets = self.client.get_assets()
            for asset in assets:
                account_type = self._map_type(asset.type_name, asset.subtype_name)
                accounts.append(
                    Account(
                        id=asset.id,
                        name=asset.display_name or asset.name,
                        type=account_type,
                        subtype=asset.subtype_name,
                        balance=Decimal(str(asset.balance)),
                        currency=asset.currency,
                        institution=asset.institution_name,
                        source="asset",
                    )
                )
        except Exception as e:
            print(f"Warning: Failed to fetch assets: {e}")

        # Get Plaid-linked accounts via direct API call to handle None subtypes
        try:
            plaid_accounts = self._fetch_plaid_accounts_raw()
            for plaid in plaid_accounts:
                account_type = self._map_type(plaid.get("type"), plaid.get("subtype"))
                balance = plaid.get("balance", 0)
                accounts.append(
                    Account(
                        id=plaid["id"],
                        name=plaid.get("display_name") or plaid.get("name", "Unknown"),
                        type=account_type,
                        subtype=plaid.get("subtype"),
                        balance=Decimal(str(balance)) if balance else Decimal(0),
                        currency=plaid.get("currency", "USD"),
                        institution=plaid.get("institution_name"),
                        source="plaid",
                    )
                )
        except Exception as e:
            print(f"Warning: Failed to fetch Plaid accounts: {e}")

        return accounts

    def _fetch_plaid_accounts_raw(self) -> list[dict]:
        """Fetch Plaid accounts directly via API to avoid validation issues."""
        response = httpx.get(
            "https://dev.lunchmoney.app/v1/plaid_accounts",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("plaid_accounts", [])

    def get_transactions(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[Transaction]:
        """Fetch transactions within date range."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        transactions = self.client.get_transactions(start_date=start_date, end_date=end_date)

        return [
            Transaction(
                id=t.id,
                date=t.date,
                amount=Decimal(str(t.amount)),
                category_id=t.category_id,
                category_name=t.category_name,
                is_income=t.is_income if hasattr(t, "is_income") else t.amount < 0,
                payee=t.payee,
                recurring_id=t.recurring_id,
            )
            for t in transactions
        ]

    def get_recurring_items(self) -> list[RecurringItem]:
        """Fetch recurring income and expenses."""
        items = self.client.get_recurring_items()

        return [
            RecurringItem(
                id=item.id,
                amount=Decimal(str(item.amount)) if item.amount else Decimal(0),
                cadence=item.cadence or "monthly",
                category=item.category_id,
                description=item.payee,
                is_income=item.amount < 0 if item.amount else False,
            )
            for item in items
        ]

    def build_snapshot(self) -> FinancialSnapshot:
        """Build a complete financial snapshot from all data."""
        accounts = self.get_accounts()

        # Calculate totals by type
        investments = sum(a.balance for a in accounts if a.type == AccountType.INVESTMENT)
        cash = sum(a.balance for a in accounts if a.type == AccountType.CASH)
        real_estate = sum(a.balance for a in accounts if a.type == AccountType.REAL_ESTATE)
        crypto = sum(a.balance for a in accounts if a.type == AccountType.CRYPTO)
        other_assets = sum(
            a.balance
            for a in accounts
            if a.type in (AccountType.VEHICLE, AccountType.OTHER_ASSET)
        )

        loans = sum(a.balance for a in accounts if a.type == AccountType.LOAN)
        credit = sum(a.balance for a in accounts if a.type == AccountType.CREDIT)
        other_liabilities = sum(
            a.balance for a in accounts if a.type == AccountType.OTHER_LIABILITY
        )

        total_assets = investments + cash + real_estate + crypto + other_assets
        total_liabilities = loans + credit + other_liabilities
        net_worth = total_assets - total_liabilities

        # Calculate monthly cash flow from transactions
        transactions = self.get_transactions()
        if transactions:
            income_txns = [t for t in transactions if t.is_income]
            expense_txns = [t for t in transactions if t.is_expense]

            months = max(1, (date.today() - min(t.date for t in transactions)).days / 30)
            monthly_income = abs(sum(t.amount for t in income_txns)) / Decimal(months)
            monthly_expenses = abs(sum(t.amount for t in expense_txns)) / Decimal(months)
        else:
            monthly_income = Decimal(0)
            monthly_expenses = Decimal(0)

        monthly_savings = monthly_income - monthly_expenses

        return FinancialSnapshot(
            snapshot_date=date.today(),
            net_worth=net_worth,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            investments=investments,
            cash=cash,
            real_estate=real_estate,
            crypto=crypto,
            other_assets=other_assets,
            loans=loans,
            credit=credit,
            other_liabilities=other_liabilities,
            monthly_income=monthly_income,
            monthly_expenses=monthly_expenses,
            monthly_savings=monthly_savings,
        )

    def _map_type(self, type_name: str | None, subtype_name: str | None = None) -> AccountType:
        """Map Lunch Money type names to AccountType enum."""
        if subtype_name:
            subtype_lower = subtype_name.lower()
            if subtype_lower in self.TYPE_MAPPING:
                return self.TYPE_MAPPING[subtype_lower]

        if type_name:
            type_lower = type_name.lower()
            if type_lower in self.TYPE_MAPPING:
                return self.TYPE_MAPPING[type_lower]

        return AccountType.OTHER_ASSET
