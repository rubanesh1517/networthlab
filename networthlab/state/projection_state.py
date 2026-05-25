"""Projection and scenario comparison state."""

from typing import Any
import reflex as rx


class ProjectionState(rx.State):
    """State for financial projections and scenarios."""

    # Scenarios list
    scenarios: list[dict[str, Any]] = []

    # Form state
    form_name: str = ""
    form_starting_amount: str = ""
    form_monthly_contribution: str = ""
    form_annual_return: str = ""
    form_years: str = ""
    form_color: str = "#8b5cf6"
    editing_scenario_id: str = ""
    show_form: bool = False

    # Available colors for scenarios
    available_colors: list[str] = [
        "#8b5cf6",  # Purple
        "#3b82f6",  # Blue
        "#10b981",  # Green
        "#f59e0b",  # Amber
        "#ef4444",  # Red
        "#ec4899",  # Pink
        "#06b6d4",  # Cyan
    ]

    def toggle_form(self) -> None:
        """Toggle scenario form visibility."""
        self.show_form = not self.show_form
        if not self.show_form:
            self._reset_form()

    def _reset_form(self) -> None:
        """Reset form fields."""
        self.form_name = ""
        self.form_starting_amount = ""
        self.form_monthly_contribution = ""
        self.form_annual_return = ""
        self.form_years = ""
        self.form_color = self.available_colors[len(self.scenarios) % len(self.available_colors)]
        self.editing_scenario_id = ""

    def set_form_name(self, value: str) -> None:
        """Set form name."""
        self.form_name = value

    def set_form_starting_amount(self, value: str) -> None:
        """Set form starting amount."""
        self.form_starting_amount = value

    def set_form_monthly_contribution(self, value: str) -> None:
        """Set form monthly contribution."""
        self.form_monthly_contribution = value

    def set_form_annual_return(self, value: str) -> None:
        """Set form annual return."""
        self.form_annual_return = value

    def set_form_years(self, value: str) -> None:
        """Set form years."""
        self.form_years = value

    def set_form_color(self, value: str) -> None:
        """Set form color."""
        self.form_color = value

    def add_scenario(self) -> None:
        """Add a new scenario."""
        try:
            starting = float(self.form_starting_amount.replace(",", "").replace("$", ""))
            monthly = float(self.form_monthly_contribution.replace(",", "").replace("$", ""))
            annual_return = float(self.form_annual_return.replace("%", ""))
            years = int(self.form_years)

            scenario = {
                "id": str(len(self.scenarios) + 1),
                "name": self.form_name or f"Scenario {len(self.scenarios) + 1}",
                "starting_amount": starting,
                "monthly_contribution": monthly,
                "annual_return": annual_return,
                "years": years,
                "color": self.form_color,
            }

            self.scenarios = self.scenarios + [scenario]
            self._reset_form()
            self.show_form = False

        except ValueError:
            pass

    def edit_scenario(self, scenario_id: str) -> None:
        """Load a scenario into the form for editing."""
        for scenario in self.scenarios:
            if scenario["id"] == scenario_id:
                self.form_name = scenario["name"]
                self.form_starting_amount = str(scenario["starting_amount"])
                self.form_monthly_contribution = str(scenario["monthly_contribution"])
                self.form_annual_return = str(scenario["annual_return"])
                self.form_years = str(scenario["years"])
                self.form_color = scenario.get("color", "#8b5cf6")
                self.editing_scenario_id = scenario_id
                self.show_form = True
                break

    def update_scenario(self) -> None:
        """Update an existing scenario."""
        if not self.editing_scenario_id:
            return

        try:
            starting = float(self.form_starting_amount.replace(",", "").replace("$", ""))
            monthly = float(self.form_monthly_contribution.replace(",", "").replace("$", ""))
            annual_return = float(self.form_annual_return.replace("%", ""))
            years = int(self.form_years)

            updated_scenarios = []
            for scenario in self.scenarios:
                if scenario["id"] == self.editing_scenario_id:
                    updated_scenarios.append({
                        **scenario,
                        "name": self.form_name,
                        "starting_amount": starting,
                        "monthly_contribution": monthly,
                        "annual_return": annual_return,
                        "years": years,
                        "color": self.form_color,
                    })
                else:
                    updated_scenarios.append(scenario)

            self.scenarios = updated_scenarios
            self._reset_form()
            self.show_form = False

        except ValueError:
            pass

    def delete_scenario(self, scenario_id: str) -> None:
        """Delete a scenario."""
        self.scenarios = [s for s in self.scenarios if s["id"] != scenario_id]

    def save_or_update_scenario(self) -> None:
        """Save new scenario or update existing one."""
        if self.editing_scenario_id:
            self.update_scenario()
        else:
            self.add_scenario()

    def add_default_scenarios(self) -> None:
        """Add default comparison scenarios if none exist."""
        if self.scenarios:
            return

        defaults = [
            {
                "id": "1",
                "name": "Conservative",
                "starting_amount": 100000,
                "monthly_contribution": 1500,
                "annual_return": 5.0,
                "years": 30,
                "color": "#3b82f6",
            },
            {
                "id": "2",
                "name": "Moderate",
                "starting_amount": 100000,
                "monthly_contribution": 2000,
                "annual_return": 7.0,
                "years": 30,
                "color": "#8b5cf6",
            },
            {
                "id": "3",
                "name": "Aggressive",
                "starting_amount": 100000,
                "monthly_contribution": 2500,
                "annual_return": 9.0,
                "years": 30,
                "color": "#10b981",
            },
        ]
        self.scenarios = defaults

    def _calculate_projection(self, scenario: dict) -> list[dict]:
        """Calculate projection for a single scenario."""
        data = []
        current = scenario["starting_amount"]
        monthly_rate = scenario["annual_return"] / 100 / 12
        monthly_contrib = scenario["monthly_contribution"]

        for year in range(scenario["years"] + 1):
            data.append({
                "year": year,
                "value": round(current, 0),
            })
            for _ in range(12):
                current = current * (1 + monthly_rate) + monthly_contrib

        return data

    @rx.var
    def comparison_chart_data(self) -> list[dict[str, Any]]:
        """Return combined projection data for all scenarios."""
        if not self.scenarios:
            return []

        # Find max years across scenarios
        max_years = max(s["years"] for s in self.scenarios)

        data = []
        for year in range(max_years + 1):
            point = {"year": year}

            for scenario in self.scenarios:
                current = scenario["starting_amount"]
                monthly_rate = scenario["annual_return"] / 100 / 12
                monthly_contrib = scenario["monthly_contribution"]

                # Calculate value at this year
                for y in range(year):
                    for _ in range(12):
                        current = current * (1 + monthly_rate) + monthly_contrib

                if year <= scenario["years"]:
                    point[scenario["name"]] = round(current, 0)

            data.append(point)

        return data

    @rx.var
    def scenario_names(self) -> list[str]:
        """Return list of scenario names for chart keys."""
        return [s["name"] for s in self.scenarios]

    @rx.var
    def scenario_colors(self) -> dict[str, str]:
        """Return mapping of scenario names to colors."""
        return {s["name"]: s["color"] for s in self.scenarios}

    @rx.var
    def scenario_summaries(self) -> list[dict[str, Any]]:
        """Return summary statistics for each scenario."""
        summaries = []

        for scenario in self.scenarios:
            current = scenario["starting_amount"]
            monthly_rate = scenario["annual_return"] / 100 / 12
            monthly_contrib = scenario["monthly_contribution"]
            total_contributions = scenario["starting_amount"]

            for _ in range(scenario["years"]):
                for _ in range(12):
                    current = current * (1 + monthly_rate) + monthly_contrib
                    total_contributions += monthly_contrib

            interest_earned = current - total_contributions

            summaries.append({
                "name": scenario["name"],
                "final_value": f"${current:,.0f}",
                "total_contributions": f"${total_contributions:,.0f}",
                "interest_earned": f"${interest_earned:,.0f}",
                "color": scenario.get("color", "#8b5cf6"),
            })

        return summaries
