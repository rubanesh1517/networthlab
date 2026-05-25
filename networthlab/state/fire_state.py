"""FIRE (Financial Independence Retire Early) calculator state."""

from typing import Any

import reflex as rx


class FIREState(rx.State):
    """State for FIRE calculations."""

    # User inputs
    current_age: int = 30
    retirement_age: int = 65
    annual_expenses: float = 50000.0
    monthly_contribution: float = 2000.0
    current_investments: float = 100000.0

    # Assumptions
    expected_return: float = 7.0  # Annual return %
    inflation_rate: float = 2.5  # Inflation %
    withdrawal_rate: float = 4.0  # Safe withdrawal rate %

    # Scenario comparison
    conservative_return: float = 5.0
    aggressive_return: float = 9.0

    def set_current_age(self, value: str) -> None:
        """Set current age."""
        try:
            self.current_age = int(value)
        except ValueError:
            pass

    def set_retirement_age(self, value: str) -> None:
        """Set retirement age."""
        try:
            self.retirement_age = int(value)
        except ValueError:
            pass

    def set_annual_expenses(self, value: str) -> None:
        """Set annual expenses."""
        try:
            self.annual_expenses = float(value.replace(",", "").replace("$", ""))
        except ValueError:
            pass

    def set_monthly_contribution(self, value: str) -> None:
        """Set monthly contribution."""
        try:
            self.monthly_contribution = float(value.replace(",", "").replace("$", ""))
        except ValueError:
            pass

    def set_current_investments(self, value: str) -> None:
        """Set current investments value."""
        try:
            self.current_investments = float(value.replace(",", "").replace("$", ""))
        except ValueError:
            pass

    def set_expected_return(self, value: list[float]) -> None:
        """Set expected return from slider."""
        if value:
            self.expected_return = float(value[0])

    def set_inflation_rate(self, value: list[float]) -> None:
        """Set inflation rate from slider."""
        if value:
            self.inflation_rate = float(value[0])

    def set_withdrawal_rate(self, value: list[float]) -> None:
        """Set withdrawal rate from slider."""
        if value:
            self.withdrawal_rate = float(value[0])

    @rx.var
    def current_age_str(self) -> str:
        """Return current age as string."""
        return str(self.current_age)

    @rx.var
    def retirement_age_str(self) -> str:
        """Return retirement age as string."""
        return str(self.retirement_age)

    @rx.var
    def formatted_current_investments(self) -> str:
        """Return formatted current investments."""
        return f"${self.current_investments:,.0f}"

    @rx.var
    def formatted_annual_expenses(self) -> str:
        """Return formatted annual expenses."""
        return f"${self.annual_expenses:,.0f}"

    @rx.var
    def formatted_monthly_contribution(self) -> str:
        """Return formatted monthly contribution."""
        return f"${self.monthly_contribution:,.0f}"

    @rx.var
    def fire_number(self) -> float:
        """Calculate FIRE number (amount needed to retire)."""
        if self.withdrawal_rate <= 0:
            return 0.0
        return self.annual_expenses / (self.withdrawal_rate / 100)

    @rx.var
    def formatted_fire_number(self) -> str:
        """Return formatted FIRE number."""
        return f"${self.fire_number:,.0f}"

    @rx.var
    def fire_progress_percent(self) -> float:
        """Calculate progress toward FIRE number."""
        if self.fire_number <= 0:
            return 0.0
        progress = (self.current_investments / self.fire_number) * 100
        return round(min(progress, 100), 1)  # Cap at 100%

    @rx.var
    def formatted_fire_progress(self) -> str:
        """Return formatted FIRE progress string."""
        return f"{self.fire_progress_percent:.1f}%"

    @rx.var
    def years_to_fire(self) -> int:
        """Calculate years until FIRE is achieved."""
        if self.fire_number <= self.current_investments:
            return 0

        target = self.fire_number
        current = self.current_investments
        monthly_rate = self.expected_return / 100 / 12
        monthly_contrib = self.monthly_contribution

        if monthly_rate <= 0:
            if monthly_contrib <= 0:
                return 99  # Never
            return int((target - current) / (monthly_contrib * 12))

        years = 0
        while current < target and years < 100:
            for _ in range(12):  # Monthly compounding
                current = current * (1 + monthly_rate) + monthly_contrib
            years += 1

        return years

    @rx.var
    def fire_year(self) -> int:
        """Calculate the year FIRE will be achieved."""
        from datetime import datetime
        return datetime.now().year + self.years_to_fire

    @rx.var
    def fire_age(self) -> int:
        """Calculate age at FIRE."""
        return self.current_age + self.years_to_fire

    @rx.var
    def monthly_passive_income(self) -> float:
        """Calculate monthly passive income at FIRE."""
        return (self.fire_number * (self.withdrawal_rate / 100)) / 12

    @rx.var
    def formatted_monthly_income(self) -> str:
        """Return formatted monthly passive income."""
        return f"${self.monthly_passive_income:,.0f}"

    def _calculate_projection(self, return_rate: float, years: int = 40) -> list[dict]:
        """Calculate investment projection for given return rate."""
        data = []
        current = self.current_investments
        monthly_rate = return_rate / 100 / 12

        for year in range(years + 1):
            data.append({
                "year": year,
                "value": round(current, 0),
            })
            for _ in range(12):
                current = current * (1 + monthly_rate) + self.monthly_contribution

        return data

    @rx.var
    def projection_data(self) -> list[dict[str, Any]]:
        """Return projection data for chart."""
        years = max(self.years_to_fire + 10, 30)
        data = []

        conservative = self.current_investments
        expected = self.current_investments
        aggressive = self.current_investments

        monthly_conservative = self.conservative_return / 100 / 12
        monthly_expected = self.expected_return / 100 / 12
        monthly_aggressive = self.aggressive_return / 100 / 12

        for year in range(years + 1):
            data.append({
                "year": year,
                "conservative": round(conservative, 0),
                "expected": round(expected, 0),
                "aggressive": round(aggressive, 0),
                "fire_target": round(self.fire_number, 0),
            })

            for _ in range(12):
                conservative = conservative * (1 + monthly_conservative) + self.monthly_contribution
                expected = expected * (1 + monthly_expected) + self.monthly_contribution
                aggressive = aggressive * (1 + monthly_aggressive) + self.monthly_contribution

        return data

    @rx.var
    def yearly_breakdown(self) -> list[dict[str, Any]]:
        """Return year-by-year breakdown table data."""
        data = []
        current = self.current_investments
        monthly_rate = self.expected_return / 100 / 12
        annual_contribution = self.monthly_contribution * 12

        for year in range(1, min(self.years_to_fire + 5, 41)):
            start_balance = current

            for _ in range(12):
                current = current * (1 + monthly_rate) + self.monthly_contribution

            interest = current - start_balance - annual_contribution
            progress = min((current / self.fire_number) * 100, 100) if self.fire_number > 0 else 0

            data.append({
                "year": year,
                "age": self.current_age + year,
                "balance": f"${current:,.0f}",
                "contributions": f"${annual_contribution:,.0f}",
                "interest": f"${interest:,.0f}",
                "progress": f"{progress:.1f}%",
            })

        return data
