"""Financial calculations for projections."""

from datetime import date, timedelta
from decimal import Decimal

from networthlab.models.projections import FIREResult, FinancialSnapshot, LoanPayoffResult, Projection
from networthlab.models.settings import UserSettings


def calculate_fire(
    current_investments: Decimal,
    annual_savings: Decimal,
    annual_expenses: Decimal,
    expected_return: float = 0.07,
    withdrawal_rate: float = 0.04,
    inflation_rate: float = 0.03,
    max_years: int = 50,
) -> FIREResult:
    """
    Calculate years to Financial Independence.

    FIRE Number = Annual Expenses / Safe Withdrawal Rate
    Then compound investments until they reach the inflation-adjusted FIRE number.
    """
    if withdrawal_rate <= 0:
        withdrawal_rate = 0.04

    fire_number = annual_expenses / Decimal(withdrawal_rate)
    investments = current_investments

    # Check if already FIRE
    if investments >= fire_number:
        return FIREResult(
            fire_number=fire_number,
            current_investments=current_investments,
            annual_expenses=annual_expenses,
            years_to_fire=0,
            fire_year=date.today().year,
            fire_progress=1.0,
        )

    for year in range(1, max_years + 1):
        # Grow investments
        investments = investments * Decimal(1 + expected_return) + annual_savings

        # Adjust FIRE number for inflation
        adjusted_fire = fire_number * Decimal(1 + inflation_rate) ** year

        if investments >= adjusted_fire:
            return FIREResult(
                fire_number=fire_number,
                current_investments=current_investments,
                annual_expenses=annual_expenses,
                years_to_fire=year,
                fire_year=date.today().year + year,
                fire_progress=min(1.0, float(current_investments / fire_number)),
            )

    # Not achievable within max_years
    return FIREResult(
        fire_number=fire_number,
        current_investments=current_investments,
        annual_expenses=annual_expenses,
        years_to_fire=-1,
        fire_year=-1,
        fire_progress=float(current_investments / fire_number) if fire_number > 0 else 0.0,
    )


def calculate_loan_payoff(
    account_id: int,
    account_name: str,
    balance: Decimal,
    annual_rate: float,
    monthly_payment: Decimal,
    extra_payment: Decimal = Decimal(0),
) -> LoanPayoffResult:
    """
    Calculate loan payoff timeline using amortization.

    Returns months to payoff and total interest paid.
    """
    if balance <= 0:
        return LoanPayoffResult(
            account_id=account_id,
            account_name=account_name,
            current_balance=balance,
            interest_rate=annual_rate,
            monthly_payment=monthly_payment,
            months_to_payoff=0,
            payoff_date=date.today(),
            total_interest=Decimal(0),
        )

    monthly_rate = Decimal(annual_rate / 12)
    remaining = balance
    months = 0
    total_interest = Decimal(0)
    total_payment = monthly_payment + extra_payment

    while remaining > 0 and months < 360:  # 30 year cap
        interest = remaining * monthly_rate
        total_interest += interest
        principal = total_payment - interest

        if principal <= 0:
            # Payment doesn't cover interest - loan will never be paid off
            return LoanPayoffResult(
                account_id=account_id,
                account_name=account_name,
                current_balance=balance,
                interest_rate=annual_rate,
                monthly_payment=monthly_payment,
                months_to_payoff=-1,
                payoff_date=date.today(),
                total_interest=Decimal(-1),
            )

        remaining = max(Decimal(0), remaining - principal)
        months += 1

    payoff_date = date.today() + timedelta(days=months * 30)

    return LoanPayoffResult(
        account_id=account_id,
        account_name=account_name,
        current_balance=balance,
        interest_rate=annual_rate,
        monthly_payment=monthly_payment,
        months_to_payoff=months,
        payoff_date=payoff_date,
        total_interest=total_interest,
    )


def project_net_worth(
    snapshot: FinancialSnapshot,
    settings: UserSettings,
    years: int | None = None,
) -> list[Projection]:
    """
    Project net worth year by year.

    Assumptions:
    - Investments grow at expected_return rate
    - Savings continue at current rate
    - Loans decrease based on current payment patterns
    """
    if years is None:
        years = settings.projection_years

    projections = []
    investments = snapshot.investments
    annual_savings = snapshot.monthly_savings * 12

    # Calculate FIRE number for progress tracking
    annual_expenses = snapshot.monthly_expenses * 12
    if settings.safe_withdrawal_rate > 0:
        fire_number = annual_expenses / Decimal(settings.safe_withdrawal_rate)
    else:
        fire_number = Decimal(0)

    # Estimate loan payoff (simplified: assume 5% of balance paid per year)
    current_loans = snapshot.loans

    for year in range(1, years + 1):
        # Compound investment growth
        investments = investments * Decimal(1 + settings.expected_return) + annual_savings

        # Decrease loans (simplified linear model)
        loan_balance = max(Decimal(0), current_loans - (current_loans * Decimal("0.1") * year))

        # Calculate net worth
        net_worth = (
            investments
            + snapshot.cash
            + snapshot.real_estate
            + snapshot.crypto
            + snapshot.other_assets
            - loan_balance
            - snapshot.credit
            - snapshot.other_liabilities
        )

        # Calculate FIRE progress
        fire_progress = min(1.0, float(investments / fire_number)) if fire_number > 0 else 0.0

        projections.append(
            Projection(
                year=date.today().year + year,
                net_worth=net_worth,
                investments=investments,
                loan_balance=loan_balance,
                fire_progress=fire_progress,
            )
        )

    return projections
