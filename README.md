# NetWorthLab

A personal financial projection app powered by your Lunch Money data.

## Features

- **FIRE Calculator** - Calculate when you can achieve financial independence
- **Loan Payoff Tracker** - See when your loans will be paid off
- **Net Worth Projections** - Visualize your financial future based on current trends

## Tech Stack

- **Reflex** - Python framework that compiles to React
- **Lunchable** - Lunch Money API client
- **Recharts** - Beautiful, interactive charts

## Getting Started

### Prerequisites

- Python 3.11+
- A [Lunch Money](https://lunchmoney.app) account with API access

### Installation

```bash
# Clone the repo
cd networthlab

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -e .

# Initialize Reflex
reflex init

# Run the app
reflex run
```

### Configuration

1. Get your Lunch Money API token from [Settings > Developers](https://my.lunchmoney.app/developers)
2. Enter the token in the Settings page of the app

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .
```

## Project Structure

```
networthlab/
├── networthlab/          # Reflex app
│   ├── pages/            # UI pages
│   ├── components/       # Reusable components
│   ├── services/         # Business logic
│   ├── models/           # Pydantic models
│   └── state/            # Reflex state
├── tests/                # Unit tests
└── data/                 # Local storage
```

## License

MIT
