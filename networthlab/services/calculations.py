"""Financial calculation utilities."""

import math


def calculate_compound_interest(
    principal: float,
    annual_rate: float,
    years: int,
    monthly_contribution: float = 0,
    compounds_per_year: int = 12,
) -> float:
    """
    Calculate compound interest with optional monthly contributions.

    Args:
        principal: Initial investment amount
        annual_rate: Annual interest rate as percentage (e.g., 7.0 for 7%)
        years: Number of years
        monthly_contribution: Monthly contribution amount
        compounds_per_year: Number of times interest compounds per year

    Returns:
        Final balance after compounding
    """
    rate = annual_rate / 100
    n = compounds_per_year
    t = years

    # Future value of principal
    fv_principal = principal * (1 + rate / n) ** (n * t)

    # Future value of monthly contributions (annuity)
    if monthly_contribution > 0 and rate > 0:
        monthly_rate = rate / 12
        months = years * 12
        fv_contributions = monthly_contribution * (((1 + monthly_rate) ** months - 1) / monthly_rate)
    else:
        fv_contributions = monthly_contribution * years * 12

    return fv_principal + fv_contributions


def calculate_fire_number(
    annual_expenses: float,
    withdrawal_rate: float = 4.0,
) -> float:
    """
    Calculate the FIRE number (amount needed to retire).

    Args:
        annual_expenses: Annual expenses in retirement
        withdrawal_rate: Safe withdrawal rate as percentage (default 4%)

    Returns:
        FIRE number (target net worth for retirement)
    """
    if withdrawal_rate <= 0:
        return 0.0
    return annual_expenses / (withdrawal_rate / 100)


def calculate_years_to_fire(
    current_portfolio: float,
    fire_number: float,
    monthly_contribution: float,
    annual_return: float = 7.0,
) -> int:
    """
    Calculate years until FIRE is achieved.

    Args:
        current_portfolio: Current investment portfolio value
        fire_number: Target FIRE number
        monthly_contribution: Monthly investment contribution
        annual_return: Expected annual return as percentage

    Returns:
        Number of years until FIRE
    """
    if fire_number <= current_portfolio:
        return 0

    monthly_rate = annual_return / 100 / 12
    current = current_portfolio
    years = 0

    while current < fire_number and years < 100:
        for _ in range(12):
            current = current * (1 + monthly_rate) + monthly_contribution
        years += 1

    return years


def calculate_loan_payoff(
    principal: float,
    annual_rate: float,
    monthly_payment: float,
) -> dict:
    """
    Calculate loan payoff details.

    Args:
        principal: Original loan amount
        annual_rate: Annual interest rate as percentage
        monthly_payment: Monthly payment amount

    Returns:
        Dictionary with payoff details including months, total_interest, total_paid
    """
    if monthly_payment <= 0 or principal <= 0:
        return {
            "months": 0,
            "total_interest": 0,
            "total_paid": 0,
            "schedule": [],
        }

    monthly_rate = annual_rate / 100 / 12

    if monthly_rate <= 0:
        months = math.ceil(principal / monthly_payment)
        return {
            "months": months,
            "total_interest": 0,
            "total_paid": principal,
            "schedule": [],
        }

    # Check if payment is too low
    if monthly_payment <= principal * monthly_rate:
        return {
            "months": -1,  # Indicates payment too low
            "total_interest": float("inf"),
            "total_paid": float("inf"),
            "schedule": [],
        }

    # Calculate months to payoff
    months = math.ceil(
        math.log(monthly_payment / (monthly_payment - principal * monthly_rate))
        / math.log(1 + monthly_rate)
    )

    # Generate amortization schedule
    schedule = []
    balance = principal
    total_interest = 0
    total_paid = 0

    for month in range(1, months + 1):
        interest = balance * monthly_rate
        principal_payment = min(monthly_payment - interest, balance)
        balance = max(0, balance - principal_payment)

        total_interest += interest
        total_paid += interest + principal_payment

        schedule.append({
            "month": month,
            "payment": monthly_payment if balance > 0 else principal_payment + interest,
            "principal": principal_payment,
            "interest": interest,
            "balance": balance,
        })

        if balance <= 0:
            break

    return {
        "months": len(schedule),
        "total_interest": round(total_interest, 2),
        "total_paid": round(total_paid, 2),
        "schedule": schedule,
    }


def calculate_monthly_payment(
    principal: float,
    annual_rate: float,
    term_months: int,
) -> float:
    """
    Calculate monthly payment for a loan.

    Args:
        principal: Loan principal amount
        annual_rate: Annual interest rate as percentage
        term_months: Loan term in months

    Returns:
        Monthly payment amount
    """
    if term_months <= 0 or principal <= 0:
        return 0.0

    if annual_rate <= 0:
        return principal / term_months

    monthly_rate = annual_rate / 100 / 12

    payment = principal * (
        (monthly_rate * (1 + monthly_rate) ** term_months)
        / ((1 + monthly_rate) ** term_months - 1)
    )

    return round(payment, 2)
