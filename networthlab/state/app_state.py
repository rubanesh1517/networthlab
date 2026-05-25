"""Main application state management."""

from datetime import datetime
from typing import Any

import reflex as rx
from pydantic import BaseModel


class Account(BaseModel):
    """Account data model."""

    id: int = 0
    name: str = ""
    institution: str = ""
    type: str = "Other"
    balance: float = 0.0
    currency: str = "USD"
    subtype: str = ""


class AppState(rx.State):
    """Primary application state."""

    # UI state
    theme_mode: str = "dark"
    sidebar_collapsed: bool = False
    current_page: str = "dashboard"
    last_updated: str = ""

    # Lunch Money connection
    is_connected: bool = False
    access_token: str = ""

    # Account data from Lunch Money
    accounts: list[Account] = []
    total_assets: float = 0.0
    total_liabilities: float = 0.0

    # Historical net worth data
    net_worth_history: list[dict[str, Any]] = []

    # Loading states
    is_loading: bool = False
    error_message: str = ""

    def toggle_theme(self) -> None:
        """Toggle between dark and light mode."""
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"

    def toggle_sidebar(self) -> None:
        """Toggle sidebar collapsed state."""
        self.sidebar_collapsed = not self.sidebar_collapsed

    def set_page(self, page: str) -> None:
        """Set the current page for navigation highlighting."""
        self.current_page = page

    def set_access_token(self, token: str) -> None:
        """Set the Lunch Money access token."""
        self.access_token = token

    def set_theme_mode(self, mode: str) -> None:
        """Set the theme mode."""
        self.theme_mode = mode

    async def load_accounts(self) -> None:
        """Load accounts from Lunch Money API."""
        if not self.access_token:
            self.error_message = "No access token configured"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            from lunchable import LunchMoney

            lunch = LunchMoney(access_token=self.access_token)
            print("\n" + "="*60)
            print("LOADING ACCOUNTS FROM LUNCH MONEY")
            print("="*60)

            # Get assets
            assets = lunch.get_assets()
            print(f"\n[ASSETS] Found {len(assets)} manual assets from Lunch Money")
            self.accounts = []
            self.total_assets = 0.0
            self.total_liabilities = 0.0

            # Types that should be treated as liabilities (even if balance is positive)
            liability_types = ["loan", "mortgage", "student loan", "auto loan", "personal loan",
                              "other liability", "credit", "credit card"]

            for asset in assets:
                account_type = (asset.type_name or "Other").lower()
                account_subtype = (asset.subtype_name or "").lower()

                # Debug: Print raw asset data
                print(f"\n[ASSET] ID: {asset.id}")
                print(f"  name: {asset.name}")
                print(f"  display_name: {asset.display_name}")
                print(f"  type_name: {asset.type_name}")
                print(f"  subtype_name: {asset.subtype_name}")
                print(f"  balance: {asset.balance}")
                print(f"  institution_name: {asset.institution_name}")

                account = Account(
                    id=asset.id,
                    name=asset.display_name or asset.name,
                    institution=asset.institution_name or "",
                    type=asset.type_name or "Other",
                    balance=float(asset.balance) if asset.balance else 0.0,
                    currency=asset.currency or "USD",
                    subtype=asset.subtype_name or "",
                )
                self.accounts.append(account)
                print(f"  -> Mapped to: {account.name} | {account.type} | ${account.balance:,.2f}")

                balance = float(asset.balance) if asset.balance else 0.0

                # Check if this is a liability type account
                is_liability = (
                    account_type in liability_types
                    or account_subtype in liability_types
                    or "loan" in account_type
                    or "loan" in account_subtype
                    or "mortgage" in account_type
                    or "mortgage" in account_subtype
                )

                if is_liability:
                    # Liability accounts: positive balance = debt owed
                    self.total_liabilities += abs(balance)
                elif balance >= 0:
                    self.total_assets += balance
                else:
                    self.total_liabilities += abs(balance)

            # Also get plaid accounts - use raw API call to handle None subtypes
            try:
                import requests

                # Make raw API call to avoid pydantic validation issues with None subtype
                headers = {"Authorization": f"Bearer {self.access_token}"}
                response = requests.get(
                    "https://dev.lunchmoney.app/v1/plaid_accounts",
                    headers=headers
                )
                response.raise_for_status()
                plaid_data = response.json().get("plaid_accounts", [])

                # Filter to only active accounts
                active_plaid = [p for p in plaid_data if p.get("status") == "active"]
                print(f"\n[PLAID ACCOUNTS] Found {len(plaid_data)} total, {len(active_plaid)} active")
                for plaid in active_plaid:
                    plaid_type = (plaid.get("type") or "Other").lower()
                    plaid_subtype = (plaid.get("subtype") or "").lower()

                    # Debug: Print raw plaid data
                    print(f"\n[PLAID] ID: {plaid.get('id')}")
                    print(f"  name: {plaid.get('name')}")
                    print(f"  type: {plaid.get('type')}")
                    print(f"  subtype: {plaid.get('subtype')}")
                    print(f"  balance: {plaid.get('balance')}")
                    print(f"  institution_name: {plaid.get('institution_name')}")
                    print(f"  status: {plaid.get('status')}")

                    balance_val = plaid.get("balance")
                    account = Account(
                        id=plaid.get("id", 0),
                        name=plaid.get("name") or "Unnamed Account",
                        institution=plaid.get("institution_name") or "",
                        type=plaid.get("type") or "Other",
                        balance=float(balance_val) if balance_val is not None else 0.0,
                        currency=plaid.get("currency") or "USD",
                        subtype=plaid.get("subtype") or "",
                    )
                    self.accounts.append(account)
                    print(f"  -> Mapped to: {account.name} | {account.type} | ${account.balance:,.2f}")

                    balance = float(balance_val) if balance_val is not None else 0.0

                    # Check if this is a liability type account
                    is_liability = (
                        plaid_type in liability_types
                        or plaid_subtype in liability_types
                        or "loan" in plaid_type
                        or "loan" in plaid_subtype
                        or "mortgage" in plaid_type
                        or "mortgage" in plaid_subtype
                    )

                    if is_liability:
                        # Liability accounts: positive balance = debt owed
                        self.total_liabilities += abs(balance)
                    elif balance >= 0:
                        self.total_assets += balance
                    else:
                        self.total_liabilities += abs(balance)
            except Exception as plaid_error:
                # Plaid accounts may have validation issues, continue with assets only
                print(f"\n[WARNING] Error loading Plaid accounts: {plaid_error}")
                print("Continuing with manual assets only...")

            self.is_connected = True
            self.last_updated = datetime.now().strftime("%I:%M %p")

            # Debug: Print summary
            print("\n" + "="*60)
            print("SUMMARY")
            print("="*60)
            print(f"Total accounts loaded: {len(self.accounts)}")
            print(f"Total Assets: ${self.total_assets:,.2f}")
            print(f"Total Liabilities: ${self.total_liabilities:,.2f}")
            print(f"Net Worth: ${self.total_assets - self.total_liabilities:,.2f}")
            print("="*60 + "\n")

        except Exception as e:
            self.error_message = str(e)
            self.is_connected = False
            print(f"\n[ERROR] {e}\n")
        finally:
            self.is_loading = False

    @rx.var
    def net_worth(self) -> float:
        """Calculate total net worth."""
        return self.total_assets - self.total_liabilities

    @rx.var
    def formatted_net_worth(self) -> str:
        """Return formatted net worth string."""
        return f"${self.net_worth:,.2f}"

    @rx.var
    def formatted_assets(self) -> str:
        """Return formatted assets string."""
        return f"${self.total_assets:,.2f}"

    @rx.var
    def formatted_liabilities(self) -> str:
        """Return formatted liabilities string."""
        return f"${self.total_liabilities:,.2f}"

    @rx.var
    def investment_accounts(self) -> list[Account]:
        """Return only investment accounts."""
        investment_types = ["investment", "brokerage", "retirement", "401k", "ira", "roth"]
        return [
            a for a in self.accounts
            if a.type.lower() in investment_types
            or a.subtype.lower() in investment_types
        ]

    @rx.var
    def cash_accounts(self) -> list[Account]:
        """Return only cash/checking/savings accounts."""
        cash_types = ["cash", "checking", "savings", "bank"]
        return [
            a for a in self.accounts
            if a.type.lower() in cash_types
            or a.subtype.lower() in cash_types
        ]

    @rx.var
    def credit_accounts(self) -> list[Account]:
        """Return only credit accounts."""
        return [
            a for a in self.accounts
            if a.type.lower() == "credit"
            or a.subtype.lower() == "credit card"
        ]

    @rx.var
    def loan_accounts(self) -> list[Account]:
        """Return only loan accounts."""
        loan_types = ["loan", "mortgage", "student loan", "auto loan", "personal loan", "other liability"]
        return [
            a for a in self.accounts
            if a.type.lower() in loan_types
            or a.subtype.lower() in loan_types
            or "loan" in a.type.lower()
            or "loan" in a.subtype.lower()
            or "mortgage" in a.type.lower()
            or "mortgage" in a.subtype.lower()
        ]

    @rx.var
    def has_loan_accounts(self) -> bool:
        """Check if any loan accounts exist."""
        return len(self.loan_accounts) > 0

    @rx.var
    def allocation_data(self) -> list[dict[str, Any]]:
        """Return data formatted for allocation pie chart."""
        categories: dict[str, float] = {}

        for account in self.accounts:
            account_type = account.type
            balance = account.balance

            if balance > 0:  # Only positive balances for allocation
                if account_type in categories:
                    categories[account_type] += balance
                else:
                    categories[account_type] = balance

        return [
            {"name": name, "value": round(value, 2)}
            for name, value in categories.items()
        ]

    @rx.var
    def net_worth_chart_data(self) -> list[dict[str, Any]]:
        """Return net worth history for chart."""
        if self.net_worth_history:
            return self.net_worth_history

        # Generate sample data if no history
        current = self.net_worth if self.net_worth > 0 else 100000
        data = []
        for i in range(12):
            month_offset = 11 - i
            factor = 1 - (month_offset * 0.02)  # 2% growth per month
            data.append({
                "month": f"M{i + 1}",
                "value": round(current * factor, 2),
            })
        return data

    @rx.var
    def has_accounts(self) -> bool:
        """Check if any accounts are loaded."""
        return len(self.accounts) > 0

    @rx.var
    def has_investment_accounts(self) -> bool:
        """Check if any investment accounts exist."""
        return len(self.investment_accounts) > 0

    @rx.var
    def has_cash_accounts(self) -> bool:
        """Check if any cash accounts exist."""
        return len(self.cash_accounts) > 0

    @rx.var
    def has_credit_accounts(self) -> bool:
        """Check if any credit accounts exist."""
        return len(self.credit_accounts) > 0
