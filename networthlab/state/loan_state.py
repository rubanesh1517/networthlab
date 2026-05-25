"""Loan tracking state management."""

from typing import Any
from datetime import datetime
import reflex as rx
from pydantic import BaseModel


class Loan(BaseModel):
    """Loan data model."""

    id: str = ""
    name: str = ""
    principal: float = 0.0
    current_balance: float = 0.0
    interest_rate: float = 0.0
    monthly_payment: float = 0.0
    start_date: str = ""
    term_months: int = 0


class LoanState(rx.State):
    """State for loan tracking and calculations."""

    # List of loans
    loans: list[Loan] = []

    # Form state for adding/editing loans
    form_name: str = ""
    form_principal: str = ""
    form_interest_rate: str = ""
    form_monthly_payment: str = ""
    form_start_date: str = ""
    form_term_months: str = ""
    editing_loan_id: str = ""
    show_form: bool = False

    def toggle_form(self) -> None:
        """Toggle loan form visibility."""
        self.show_form = not self.show_form
        if not self.show_form:
            self._reset_form()

    def _reset_form(self) -> None:
        """Reset form fields."""
        self.form_name = ""
        self.form_principal = ""
        self.form_interest_rate = ""
        self.form_monthly_payment = ""
        self.form_start_date = ""
        self.form_term_months = ""
        self.editing_loan_id = ""

    def set_form_name(self, value: str) -> None:
        """Set form name."""
        self.form_name = value

    def set_form_principal(self, value: str) -> None:
        """Set form principal."""
        self.form_principal = value

    def set_form_interest_rate(self, value: str) -> None:
        """Set form interest rate."""
        self.form_interest_rate = value

    def set_form_monthly_payment(self, value: str) -> None:
        """Set form monthly payment."""
        self.form_monthly_payment = value

    def set_form_start_date(self, value: str) -> None:
        """Set form start date."""
        self.form_start_date = value

    def set_form_term_months(self, value: str) -> None:
        """Set form term months."""
        self.form_term_months = value

    def add_loan(self) -> None:
        """Add a new loan from form data."""
        try:
            principal = float(self.form_principal.replace(",", "").replace("$", ""))
            interest_rate = float(self.form_interest_rate.replace("%", ""))
            monthly_payment = float(self.form_monthly_payment.replace(",", "").replace("$", ""))
            term_months = int(self.form_term_months) if self.form_term_months else 0

            loan = Loan(
                id=str(len(self.loans) + 1),
                name=self.form_name,
                principal=principal,
                current_balance=principal,
                interest_rate=interest_rate,
                monthly_payment=monthly_payment,
                start_date=self.form_start_date or datetime.now().strftime("%Y-%m-%d"),
                term_months=term_months,
            )

            self.loans = self.loans + [loan]
            self._reset_form()
            self.show_form = False

        except ValueError:
            pass

    def edit_loan(self, loan_id: str) -> None:
        """Load a loan into the form for editing."""
        for loan in self.loans:
            if loan.id == loan_id:
                self.form_name = loan.name
                self.form_principal = str(loan.principal)
                self.form_interest_rate = str(loan.interest_rate)
                self.form_monthly_payment = str(loan.monthly_payment)
                self.form_start_date = loan.start_date
                self.form_term_months = str(loan.term_months)
                self.editing_loan_id = loan_id
                self.show_form = True
                break

    def update_loan(self) -> None:
        """Update an existing loan."""
        if not self.editing_loan_id:
            return

        try:
            principal = float(self.form_principal.replace(",", "").replace("$", ""))
            interest_rate = float(self.form_interest_rate.replace("%", ""))
            monthly_payment = float(self.form_monthly_payment.replace(",", "").replace("$", ""))
            term_months = int(self.form_term_months) if self.form_term_months else 0

            updated_loans = []
            for loan in self.loans:
                if loan.id == self.editing_loan_id:
                    updated_loans.append(Loan(
                        id=loan.id,
                        name=self.form_name,
                        principal=principal,
                        current_balance=loan.current_balance,
                        interest_rate=interest_rate,
                        monthly_payment=monthly_payment,
                        start_date=self.form_start_date,
                        term_months=term_months,
                    ))
                else:
                    updated_loans.append(loan)

            self.loans = updated_loans
            self._reset_form()
            self.show_form = False

        except ValueError:
            pass

    def delete_loan(self, loan_id: str) -> None:
        """Delete a loan."""
        self.loans = [loan for loan in self.loans if loan.id != loan_id]

    def save_or_update_loan(self) -> None:
        """Save new loan or update existing one."""
        if self.editing_loan_id:
            self.update_loan()
        else:
            self.add_loan()

    @rx.var
    def total_debt(self) -> float:
        """Calculate total debt across all loans."""
        return sum(loan.current_balance for loan in self.loans)

    @rx.var
    def formatted_total_debt(self) -> str:
        """Return formatted total debt."""
        return f"${self.total_debt:,.2f}"

    @rx.var
    def total_monthly_payment(self) -> float:
        """Calculate total monthly payments."""
        return sum(loan.monthly_payment for loan in self.loans)

    @rx.var
    def formatted_monthly_payment(self) -> str:
        """Return formatted monthly payment."""
        return f"${self.total_monthly_payment:,.2f}"

    @rx.var
    def average_interest_rate(self) -> float:
        """Calculate weighted average interest rate."""
        if not self.loans or self.total_debt == 0:
            return 0.0

        weighted_sum = sum(
            loan.interest_rate * loan.current_balance
            for loan in self.loans
        )
        return weighted_sum / self.total_debt

    @rx.var
    def formatted_avg_rate(self) -> str:
        """Return formatted average rate."""
        return f"{self.average_interest_rate:.2f}%"

    def _calculate_payoff_months(self, balance: float, rate: float, payment: float) -> int:
        """Calculate months to pay off a loan."""
        if payment <= 0 or balance <= 0:
            return 0
        if rate <= 0:
            return int(balance / payment) + 1

        monthly_rate = rate / 100 / 12
        if payment <= balance * monthly_rate:
            return 999  # Payment too low, will never pay off

        import math
        months = math.log(payment / (payment - balance * monthly_rate)) / math.log(1 + monthly_rate)
        return int(math.ceil(months))

    @rx.var
    def estimated_payoff_date(self) -> str:
        """Calculate estimated payoff date for all loans."""
        if not self.loans:
            return "No loans"

        max_months = 0
        for loan in self.loans:
            months = self._calculate_payoff_months(
                loan.current_balance,
                loan.interest_rate,
                loan.monthly_payment,
            )
            max_months = max(max_months, months)

        if max_months >= 999:
            return "Never (increase payments)"

        from dateutil.relativedelta import relativedelta

        payoff_date = datetime.now() + relativedelta(months=max_months)
        return payoff_date.strftime("%B %Y")

    @rx.var
    def payoff_timeline_data(self) -> list[dict[str, Any]]:
        """Return data for payoff timeline stacked bar chart."""
        if not self.loans:
            return []

        max_months = 0
        for loan in self.loans:
            months = self._calculate_payoff_months(
                loan.current_balance,
                loan.interest_rate,
                loan.monthly_payment,
            )
            max_months = max(max_months, min(months, 360))  # Cap at 30 years

        # Generate data points at yearly intervals
        data = []
        for year in range(0, min(max_months // 12 + 2, 31)):
            month_num = year * 12
            point: dict[str, Any] = {"year": year}

            for loan in self.loans:
                balance = loan.current_balance
                rate = loan.interest_rate / 100 / 12
                payment = loan.monthly_payment
                name = loan.name or f"Loan {loan.id}"

                # Simulate balance at this point
                current = balance
                for _ in range(month_num):
                    if current <= 0:
                        break
                    interest = current * rate
                    principal_paid = payment - interest
                    current = max(0, current - principal_paid)

                point[name] = round(current, 0)

            data.append(point)

        return data

    @rx.var
    def loan_names(self) -> list[str]:
        """Return list of loan names for chart keys."""
        return [loan.name or f"Loan {loan.id}" for loan in self.loans]

    @rx.var
    def has_loans(self) -> bool:
        """Check if any loans exist."""
        return len(self.loans) > 0
