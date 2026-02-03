# NetWorthLab - Architecture

A personal financial projection app powered by Lunch Money data.

**Tech Stack:** Python + Reflex (React-quality UI)

## Goals

1. **FIRE Calculator** - Year when you can be financially independent
2. **Loan Payoff Tracker** - Year when loans are paid off
3. **Net Worth Projections** - Projected net worth each year based on trends

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **UI Framework** | Reflex (compiles to React + Next.js) |
| **Styling** | TailwindCSS |
| **Charts** | Recharts (via Reflex) |
| **Data Processing** | Pandas, Pydantic |
| **Lunch Money API** | Lunchable (Python client) |
| **State Management** | Reflex State |
| **Storage** | SQLite (local) or JSON file |

---

## Data Flow

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Lunch Money   │ ───► │   Reflex State  │ ───► │   React UI      │
│      API        │      │   (Python)      │      │   (Auto-gen)    │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  User Inputs    │
                         │  (rates, goals) │
                         └─────────────────┘
```

---

## Data Models

### From Lunch Money API

```python
from pydantic import BaseModel
from decimal import Decimal
from datetime import date

class Account(BaseModel):
    """Unified model for assets and plaid accounts"""
    id: int
    name: str
    type: str           # investment, loan, cash, real_estate, crypto
    subtype: str | None # retirement, checking, savings
    balance: Decimal
    currency: str
    institution: str | None
    source: str         # "asset" or "plaid"

class Transaction(BaseModel):
    """For trend analysis"""
    id: int
    date: date
    amount: Decimal
    category_id: int | None
    category_name: str | None
    is_income: bool
    payee: str | None

class RecurringItem(BaseModel):
    """Predictable cash flows"""
    id: int
    amount: Decimal
    cadence: str        # monthly, yearly, etc.
    category: str | None
    type: str           # cleared, suggested
```

### User Settings (Manual Input)

```python
class UserSettings(BaseModel):
    # API
    lunch_money_token: str

    # FIRE Settings
    safe_withdrawal_rate: float = 0.04      # 4%
    expected_return: float = 0.07           # 7%
    inflation_rate: float = 0.03            # 3%

    # Loan Settings
    loans: list[LoanSettings] = []

class LoanSettings(BaseModel):
    account_id: int
    interest_rate: float
    extra_monthly_payment: Decimal = Decimal(0)
```

### Computed Data

```python
class FinancialSnapshot(BaseModel):
    """Current state"""
    date: date
    net_worth: Decimal
    total_assets: Decimal
    total_liabilities: Decimal

    # Breakdown
    investments: Decimal
    cash: Decimal
    real_estate: Decimal
    crypto: Decimal
    loans: Decimal

    # Cash Flow (monthly)
    income: Decimal
    expenses: Decimal
    savings: Decimal
    savings_rate: float

class Projection(BaseModel):
    """Single year projection"""
    year: int
    net_worth: Decimal
    investments: Decimal
    loan_balance: Decimal
    fire_progress: float  # 0.0 to 1.0

class FIREResult(BaseModel):
    """FIRE calculation output"""
    fire_number: Decimal
    current_investments: Decimal
    years_to_fire: int
    fire_year: int
    monthly_savings_needed: Decimal
```

---

## Core Calculations

### 1. FIRE Year

```python
def calculate_fire(
    current_investments: Decimal,
    annual_savings: Decimal,
    annual_expenses: Decimal,
    expected_return: float = 0.07,
    withdrawal_rate: float = 0.04,
    inflation_rate: float = 0.03,
    max_years: int = 50
) -> FIREResult:
    """
    FIRE Number = Annual Expenses / Withdrawal Rate
    Compound investments until >= FIRE Number (inflation adjusted)
    """
    fire_number = annual_expenses / Decimal(withdrawal_rate)
    investments = current_investments

    for year in range(1, max_years + 1):
        investments = investments * Decimal(1 + expected_return) + annual_savings
        adjusted_fire = fire_number * Decimal(1 + inflation_rate) ** year

        if investments >= adjusted_fire:
            return FIREResult(
                fire_number=fire_number,
                current_investments=current_investments,
                years_to_fire=year,
                fire_year=datetime.now().year + year,
                monthly_savings_needed=annual_savings / 12
            )

    # Not achievable in max_years
    return FIREResult(
        fire_number=fire_number,
        current_investments=current_investments,
        years_to_fire=-1,
        fire_year=-1,
        monthly_savings_needed=Decimal(0)
    )
```

### 2. Loan Payoff

```python
def calculate_loan_payoff(
    balance: Decimal,
    annual_rate: float,
    monthly_payment: Decimal,
    extra_payment: Decimal = Decimal(0)
) -> dict:
    """Returns months to payoff and total interest paid"""
    monthly_rate = Decimal(annual_rate / 12)
    remaining = balance
    months = 0
    total_interest = Decimal(0)

    while remaining > 0 and months < 360:
        interest = remaining * monthly_rate
        total_interest += interest
        principal = monthly_payment + extra_payment - interest
        remaining = max(Decimal(0), remaining - principal)
        months += 1

    return {
        "months": months,
        "years": months // 12,
        "remaining_months": months % 12,
        "total_interest": total_interest,
        "payoff_date": date.today() + timedelta(days=months * 30)
    }
```

### 3. Net Worth Projection

```python
def project_net_worth(
    snapshot: FinancialSnapshot,
    settings: UserSettings,
    years: int = 30
) -> list[Projection]:
    """Project net worth year by year"""
    projections = []
    investments = snapshot.investments
    annual_savings = snapshot.savings * 12

    fire_number = (snapshot.expenses * 12) / Decimal(settings.safe_withdrawal_rate)

    for year in range(1, years + 1):
        # Compound growth
        investments = investments * Decimal(1 + settings.expected_return) + annual_savings

        # Simplified: assume loans decrease linearly
        loan_balance = max(Decimal(0), snapshot.loans - (snapshot.loans / 20) * year)

        net_worth = investments + snapshot.cash + snapshot.real_estate - loan_balance

        projections.append(Projection(
            year=datetime.now().year + year,
            net_worth=net_worth,
            investments=investments,
            loan_balance=loan_balance,
            fire_progress=min(1.0, float(investments / fire_number))
        ))

    return projections
```

---

## File Structure

```
networthlab/
├── ARCHITECTURE.md
├── README.md
├── pyproject.toml
├── requirements.txt
│
├── networthlab/              # Reflex app
│   ├── __init__.py
│   ├── networthlab.py        # Main app entry
│   │
│   ├── state/                # Reflex state management
│   │   ├── __init__.py
│   │   ├── app_state.py      # Global app state
│   │   └── settings_state.py # User settings state
│   │
│   ├── pages/                # UI pages
│   │   ├── __init__.py
│   │   ├── dashboard.py      # Home / overview
│   │   ├── fire.py           # FIRE calculator
│   │   ├── loans.py          # Loan tracker
│   │   ├── projections.py    # Net worth projections
│   │   └── settings.py       # Settings page
│   │
│   ├── components/           # Reusable UI components
│   │   ├── __init__.py
│   │   ├── navbar.py
│   │   ├── stat_card.py
│   │   ├── charts.py
│   │   └── forms.py
│   │
│   ├── services/             # Business logic
│   │   ├── __init__.py
│   │   ├── lunch_money.py    # API client wrapper
│   │   ├── calculations.py   # FIRE, loan, projection math
│   │   └── data_processor.py # Transform API data
│   │
│   └── models/               # Pydantic models
│       ├── __init__.py
│       ├── accounts.py
│       ├── transactions.py
│       ├── projections.py
│       └── settings.py
│
├── assets/                   # Static assets
│   └── favicon.ico
│
├── tests/
│   ├── test_calculations.py
│   └── test_lunch_money.py
│
└── data/                     # Local storage
    └── settings.json
```

---

## UI Pages

### 1. Dashboard (Home)
- Net worth headline number with trend indicator
- Sparkline chart (last 12 months)
- Asset allocation donut chart
- Quick stats: Savings rate, FIRE progress %, Loan payoff date

### 2. FIRE Calculator
- Large "FIRE in X years" display
- Progress bar to FIRE number
- Interactive sliders:
  - Expected return (5-10%)
  - Withdrawal rate (3-5%)
  - Monthly savings adjustment
- Year-by-year projection chart (area chart)
- Milestone markers (25%, 50%, 75%, 100%)

### 3. Loan Tracker
- List of loans with progress bars
- Input fields for interest rates
- Payoff timeline (Gantt-style or stacked bar)
- "What if" extra payment calculator
- Total interest saved display

### 4. Projections
- Interactive line chart (10/20/30 year toggle)
- Net worth breakdown over time (stacked area)
- Optimistic / Expected / Pessimistic scenarios
- Comparison: "With current savings" vs "With increased savings"

### 5. Settings
- Lunch Money API token input
- Default assumptions (sliders)
- Account type overrides
- Data refresh button

---

## MVP Roadmap

### Phase 1: Foundation
- [x] Project architecture
- [ ] Initialize Reflex project
- [ ] Create Pydantic models
- [ ] Build Lunch Money API service

### Phase 2: Core Features
- [ ] Dashboard with net worth display
- [ ] Fetch and display accounts
- [ ] Basic FIRE calculator
- [ ] Simple projection chart

### Phase 3: Polish
- [ ] Loan payoff calculator
- [ ] Interactive sliders
- [ ] Settings persistence
- [ ] Responsive design

### Phase 4: Enhancement
- [ ] Historical tracking (store snapshots)
- [ ] Multiple scenarios
- [ ] Export to CSV/PDF
- [ ] Dark mode
