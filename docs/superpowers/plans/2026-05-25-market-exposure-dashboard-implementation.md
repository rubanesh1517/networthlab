# Market Exposure Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new `/exposure` page to the networthlab Reflex app that visualizes diversification across 6 dimensions (asset class, geography, sector, position concentration, currency, account groups) by pulling Wealthsimple positions via `ws_api` and applying ETF look-through using yfinance + YAML overrides.

**Architecture:** Four layers — `WealthsimpleService` (auth/fetch/normalize), `EtfLookthroughService` (yfinance + YAML classification with disk cache), pure `ExposureService` (aggregation into contribution rows + KPIs), and `ExposureState` (Reflex orchestration). UI is a 2×3 grid of tiles with a single reusable drill-down modal. See the design spec for full architecture rationale.

**Tech Stack:** Reflex >=0.6, Pydantic >=2.0, `ws-api` >=0.34, `yfinance` >=0.2.40, PyYAML >=6.0, `keyring` >=25 (transitive via lunchsimple), pytest >=8 for tests.

**Spec reference:** `docs/superpowers/specs/2026-05-24-market-exposure-dashboard-design.md` — every task implements a section of the spec. Section refs in the form `(spec §N)` point back to it.

**Existing conventions to follow:**
- Models use **Pydantic BaseModel**, not `@dataclass` (see `networthlab/models/accounts.py`).
- JSON persistence uses the `Storage` class in `networthlab/services/storage.py`.
- Async state loaders use `try/finally` with `is_loading` boolean (see `state/app_state.py`).
- Reflex page registration uses `add_page(..., route=..., title=..., on_load=...)` pattern (see `networthlab/networthlab.py`).
- Commit messages: short imperative, no prefix (see `git log`).

**Working directory:** All paths in this plan are relative to `~/Documents/Ruban Person/Personal Finance/networthlab/` (the git-tracked clone of `rubanesh1517/networthlab`). All `pytest` and `git` commands assume that as the cwd.

**Definition of done for each task:** the task's tests pass, no pre-existing tests broken, code committed.

---

## Task 0: Dependencies and environment

**Goal:** add the new runtime deps and confirm imports work in a clean environment.

**Files:**
- Modify: `pyproject.toml`

**Steps:**

- [ ] **Step 1: Add the four new runtime deps to pyproject.toml**

In the `[project] dependencies = [...]` array, add (alphabetically among the new entries):

```toml
dependencies = [
    "reflex>=0.6.0",
    "lunchable>=1.4.2",
    "pandas>=2.0.0",
    "pydantic>=2.0.0",
    "python-dateutil>=2.8.2",
    "keyring>=25.0.0",
    "pyyaml>=6.0",
    "ws-api>=0.34.0",
    "yfinance>=0.2.40",
]
```

Add `pytest-mock>=3.12` to the `dev` extras for the mocking helpers used in later tests:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.12.0",
    "ruff>=0.1.0",
]
```

- [ ] **Step 2: Install the updated deps**

Run: `pip install -e ".[dev]"`

Expected: install completes without errors. If `ws-api` doesn't resolve, the user may need to upgrade pip first (`python -m pip install --upgrade pip`).

- [ ] **Step 3: Verify imports resolve**

Run:

```bash
python -c "import reflex, pydantic, keyring, yaml, yfinance; from ws_api import WealthsimpleAPI, WSAPISession; print('OK')"
```

Expected: prints `OK` with no exceptions.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "Add ws-api, yfinance, pyyaml, keyring deps for exposure page"
```

---

## Task 1: Data models

**Goal:** define every model the rest of the feature consumes (spec §5). Tests verify construction, equality, and edge cases.

**Files:**
- Create: `networthlab/models/exposure.py`
- Modify: `networthlab/models/__init__.py`
- Create: `tests/test_exposure_models.py`

**Steps:**

- [ ] **Step 1: Write the failing tests**

Create `tests/test_exposure_models.py`:

```python
"""Tests for exposure data models."""

from datetime import date, datetime, timezone
from decimal import Decimal

from networthlab.models.exposure import (
    ClassificationComponent,
    ContributionRow,
    DimensionBreakdown,
    ExposureSnapshot,
    Kpis,
    Position,
    SecurityClassification,
)


def test_position_construction():
    pos = Position(
        account_id="acct-1",
        account_type="TFSA",
        account_nickname="My TFSA",
        symbol="VEQT.TO",
        name="Vanguard All-Equity ETF Portfolio",
        security_type="ETF",
        listing_currency="CAD",
        listing_exchange="TSX",
        quantity=Decimal("100"),
        market_value_cad=Decimal("3500.50"),
        book_value_cad=Decimal("3200.00"),
    )
    assert pos.symbol == "VEQT.TO"
    assert pos.market_value_cad == Decimal("3500.50")


def test_dimension_breakdown_unclassified_has_empty_buckets():
    d = DimensionBreakdown(buckets={}, source="unclassified", as_of=None, notes=["no data"])
    assert d.source == "unclassified"
    assert d.buckets == {}
    assert d.notes == ["no data"]


def test_dimension_breakdown_override_carries_as_of():
    d = DimensionBreakdown(
        buckets={"US": Decimal("1.0")},
        source="override",
        as_of=date(2026, 1, 15),
        notes=[],
    )
    assert d.as_of == date(2026, 1, 15)
    assert d.source == "override"


def test_classification_component_default_self_reference():
    c = ClassificationComponent(symbol="VEQT.TO", weight=Decimal("1.0"), source="override")
    assert c.weight == Decimal("1.0")


def test_security_classification_holds_four_dimensions():
    breakdown = DimensionBreakdown(buckets={}, source="unclassified", as_of=None, notes=[])
    sc = SecurityClassification(
        symbol="VEQT.TO",
        asset_class=breakdown,
        geography=breakdown,
        sector=breakdown,
        currency=breakdown,
        complexity_flag=None,
        components=[ClassificationComponent(symbol="VEQT.TO", weight=Decimal("1.0"), source="unclassified")],
        fetched_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
    )
    assert sc.symbol == "VEQT.TO"
    assert sc.complexity_flag is None


def test_contribution_row_weight_range():
    row = ContributionRow(
        dimension="sector",
        bucket="Technology",
        source_position="VEQT.TO",
        source_account_id="acct-1",
        underlying=None,
        value_cad=Decimal("710.00"),
        weight=Decimal("0.2033"),
        source="provider",
    )
    assert Decimal("0") <= row.weight <= Decimal("1")


def test_kpis_construction():
    kpis = Kpis(
        total_value_cad=Decimal("100000"),
        position_count=12,
        hhi_positions=1420,
        top_holding_weight=Decimal("0.21"),
        as_of_snapshot=datetime(2026, 5, 24, tzinfo=timezone.utc),
        cache_stale_minutes=0,
    )
    assert kpis.hhi_positions == 1420
    assert kpis.cache_stale_minutes == 0


def test_exposure_snapshot_assembles_full_shape():
    kpis = Kpis(
        total_value_cad=Decimal("0"),
        position_count=0,
        hhi_positions=0,
        top_holding_weight=Decimal("0"),
        as_of_snapshot=datetime(2026, 5, 24, tzinfo=timezone.utc),
        cache_stale_minutes=0,
    )
    snap = ExposureSnapshot(kpis=kpis, contributions=[], warnings=["empty portfolio"])
    assert snap.warnings == ["empty portfolio"]
    assert snap.contributions == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_exposure_models.py -v`
Expected: every test fails with `ModuleNotFoundError: No module named 'networthlab.models.exposure'`.

- [ ] **Step 3: Implement the models**

Create `networthlab/models/exposure.py`:

```python
"""Data models for the market exposure dashboard."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

Dimension = Literal[
    "asset_class", "geography", "sector", "concentration", "currency", "account"
]
ClassificationSource = Literal[
    "override", "provider", "heuristic", "recursive", "unclassified"
]


class _Frozen(BaseModel):
    """Base for immutable, hashable-by-value models."""

    model_config = ConfigDict(frozen=True)


class Position(_Frozen):
    """A single security held in a Wealthsimple account, CAD-normalized."""

    account_id: str
    account_type: str           # WS unifiedAccountType (RRSP, TFSA, NON_REGISTERED, etc.)
    account_nickname: str
    symbol: str                 # e.g., "VEQT.TO"
    name: str
    security_type: str          # "ETF", "EQUITY", "CRYPTO", ...
    listing_currency: str       # "CAD" / "USD"
    listing_exchange: str       # "TSX" / "NASDAQ" / ...
    quantity: Decimal
    market_value_cad: Decimal
    book_value_cad: Decimal


class ClassificationComponent(_Frozen):
    """One underlying contribution to a classification.

    MVP: every non-recursive source produces a single self-referential component.
    Phase 2 recursive look-through emits one component per sub-fund.
    """

    symbol: str
    weight: Decimal             # fraction of parent position
    source: ClassificationSource


class DimensionBreakdown(_Frozen):
    """Per-dimension classification result for a single security."""

    buckets: dict[str, Decimal]   # bucket name -> weight; empty when source="unclassified"
    source: ClassificationSource
    as_of: date | None            # source="override" only; day-precision YAML input
    notes: list[str]              # diagnostic warnings ("weights summed to 0.97", etc.)


class SecurityClassification(_Frozen):
    """Full classification for one symbol, normalized to internal types."""

    symbol: str
    asset_class: DimensionBreakdown
    geography: DimensionBreakdown
    sector: DimensionBreakdown
    currency: DimensionBreakdown
    complexity_flag: str | None       # "covered_call_leverage", "leveraged_2x_long", etc.
    components: list[ClassificationComponent]  # phase 2 hook; in MVP always [self]
    fetched_at: datetime              # timezone-aware UTC; drives 24h cache TTL


class ContributionRow(_Frozen):
    """One row in the canonical aggregation output. Tiles group by (dimension, bucket)."""

    dimension: Dimension
    bucket: str
    source_position: str
    source_account_id: str
    underlying: str | None
    value_cad: Decimal
    weight: Decimal               # fraction of total portfolio, 0..1
    source: ClassificationSource


class Kpis(_Frozen):
    """Top-of-page summary numbers."""

    total_value_cad: Decimal
    position_count: int
    hhi_positions: int            # 0..10,000 — POSITION concentration; Phase 2 adds single-name HHI
    top_holding_weight: Decimal   # 0..1
    as_of_snapshot: datetime      # timezone-aware UTC
    cache_stale_minutes: int      # 0 when fresh; positive when rendering from positions_cache


class ExposureSnapshot(_Frozen):
    """Complete output of ExposureService.aggregate()."""

    kpis: Kpis
    contributions: list[ContributionRow]
    warnings: list[str]           # banner text
```

- [ ] **Step 4: Update the package `__init__.py`**

Modify `networthlab/models/__init__.py` — replace its contents with:

```python
"""Data models for NetWorthLab."""

from networthlab.models.accounts import Account, AccountType
from networthlab.models.exposure import (
    ClassificationComponent,
    ClassificationSource,
    ContributionRow,
    Dimension,
    DimensionBreakdown,
    ExposureSnapshot,
    Kpis,
    Position,
    SecurityClassification,
)
from networthlab.models.projections import FIREResult, FinancialSnapshot, Projection
from networthlab.models.settings import LoanSettings, UserSettings

__all__ = [
    "Account",
    "AccountType",
    "ClassificationComponent",
    "ClassificationSource",
    "ContributionRow",
    "Dimension",
    "DimensionBreakdown",
    "ExposureSnapshot",
    "FIREResult",
    "FinancialSnapshot",
    "Kpis",
    "LoanSettings",
    "Position",
    "Projection",
    "SecurityClassification",
    "UserSettings",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_exposure_models.py -v`
Expected: 8 passed.

- [ ] **Step 6: Commit**

```bash
git add networthlab/models/exposure.py networthlab/models/__init__.py tests/test_exposure_models.py
git commit -m "Add exposure data models (Position, Classification, ContributionRow, Kpis)"
```

---

## Task 2: Committed example YAML configs

**Goal:** ship the three committed YAML files (spec §4). Content is generic curated market metadata, not user portfolio.

**Files:**
- Create: `config/account_groups.example.yaml`
- Create: `config/security_overrides.example.yaml`
- Create: `config/complex_securities.yaml`

**Steps:**

- [ ] **Step 1: Create `config/account_groups.example.yaml`**

```yaml
# Account grouping rules — TEMPLATE.
# Copy to ~/.networthlab/account_groups.yaml and edit to taste.
# Rules evaluated top-to-bottom; first match wins.
# Nickname matches use glob (fnmatch). Type matches against WS unifiedAccountType.

groups:
  - name: "Custom Group"
    match: { nicknames: ["*Nickname Pattern*"] }
    icon: "home"

  - name: Retirement
    match: { types: [RRSP, LIRA, RRIF, SPOUSAL_RRSP] }
    icon: "piggy-bank"

  - name: Tax Free Saving
    match: { types: [TFSA] }
    icon: "shield-check"

  - name: Education Saving
    match: { types: [RESP] }
    icon: "graduation-cap"

  - name: Long Term Investment
    match: { types: [NON_REGISTERED, CASH, CRYPTO] }
    icon: "trending-up"
```

- [ ] **Step 2: Create `config/security_overrides.example.yaml`**

```yaml
# Security classification overrides — committed generic curation.
# User-specific overrides live at ~/.networthlab/security_overrides.yaml
# and take precedence per-symbol.

stale_after_days: 180        # gray "review override" chip threshold

securities:
  # Vanguard CA all-in-one ETFs (fund-of-funds; geography from sub-fund weights)
  VEQT.TO:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 0.448, CAN: 0.306, INTL_DEV: 0.177, EM: 0.072 }
    as_of: "2026-05-24"
  VGRO.TO:
    asset_class: { equity: 0.8, bond: 0.2 }
    sector: provider
    geography: { US: 0.358, CAN: 0.245, INTL_DEV: 0.142, EM: 0.058, BOND_GLOBAL: 0.197 }
    as_of: "2026-05-24"
  VBAL.TO:
    asset_class: { equity: 0.6, bond: 0.4 }
    sector: provider
    geography: { US: 0.269, CAN: 0.184, INTL_DEV: 0.106, EM: 0.043, BOND_GLOBAL: 0.398 }
    as_of: "2026-05-24"

  # iShares CA all-in-one ETFs
  XEQT.TO:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 0.442, CAN: 0.258, INTL_DEV: 0.246, EM: 0.054 }
    as_of: "2026-05-24"
  XGRO.TO:
    asset_class: { equity: 0.8, bond: 0.2 }
    sector: provider
    geography: { US: 0.354, CAN: 0.206, INTL_DEV: 0.197, EM: 0.043, BOND_GLOBAL: 0.200 }
    as_of: "2026-05-24"
  XBAL.TO:
    asset_class: { equity: 0.6, bond: 0.4 }
    sector: provider
    geography: { US: 0.266, CAN: 0.155, INTL_DEV: 0.148, EM: 0.032, BOND_GLOBAL: 0.399 }
    as_of: "2026-05-24"

  # Single-region equity ETFs
  VFV.TO:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-05-24"
  VUN.TO:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-05-24"
  VCN.TO:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { CAN: 1.0 }
    as_of: "2026-05-24"
  VIU.TO:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { INTL_DEV: 1.0 }
    as_of: "2026-05-24"
  VEE.TO:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { EM: 1.0 }
    as_of: "2026-05-24"
  XIC.TO:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { CAN: 1.0 }
    as_of: "2026-05-24"
  ZSP.TO:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-05-24"

  # US-listed popular ETFs
  VOO:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-05-24"
  VTI:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-05-24"
  QQQ:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-05-24"
  QQQM:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-05-24"
```

- [ ] **Step 3: Create `config/complex_securities.yaml`**

```yaml
# Leveraged, inverse, and derivative-based products.
# Surfaces a red "leverage" chip on any tile containing a held position
# whose symbol appears here.

HYLD.TO: { flag: covered_call_leverage, leverage: 1.25 }
HMAX.TO: { flag: covered_call, leverage: 1.0 }
QMAX.TO: { flag: covered_call, leverage: 1.0 }
SMAX.TO: { flag: covered_call, leverage: 1.0 }
HQU.TO:  { flag: leveraged_2x_long, leverage: 2.0 }
HSU.TO:  { flag: leveraged_2x_long, leverage: 2.0 }
HXD.TO:  { flag: leveraged_inverse, leverage: -1.0 }
HSD.TO:  { flag: leveraged_2x_inverse, leverage: -2.0 }
```

- [ ] **Step 4: Commit**

```bash
git add config/account_groups.example.yaml config/security_overrides.example.yaml config/complex_securities.yaml
git commit -m "Add committed config templates for exposure feature"
```

---

## Task 3: Config loaders

**Goal:** load + merge the YAML configs (spec §4, §7).

**Files:**
- Create: `networthlab/services/exposure_config.py`
- Create: `tests/test_exposure_config.py`

**Steps:**

- [ ] **Step 1: Write the failing tests**

Create `tests/test_exposure_config.py`:

```python
"""Tests for exposure config loaders."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from networthlab.services.exposure_config import (
    AccountGroupRule,
    ComplexSecurityFlag,
    SecurityOverride,
    load_account_groups,
    load_complex_securities,
    load_security_overrides,
    match_account_group,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


# ----- account_groups loader -----

def test_load_account_groups_returns_rules_in_order(tmp_path):
    f = tmp_path / "account_groups.yaml"
    f.write_text(
        """
groups:
  - name: "Custom"
    match: { nicknames: ["*Pattern*"] }
    icon: "home"
  - name: Retirement
    match: { types: [RRSP] }
    icon: "piggy-bank"
""".strip()
    )
    rules = load_account_groups(f)
    assert len(rules) == 2
    assert rules[0].name == "Custom"
    assert rules[1].name == "Retirement"


def test_load_account_groups_missing_file_returns_empty():
    rules = load_account_groups(Path("/nonexistent/path.yaml"))
    assert rules == []


def test_match_account_group_nickname_pattern_wins_over_type():
    rules = [
        AccountGroupRule(name="Special", nicknames=["*Vault*"], types=[], icon="home"),
        AccountGroupRule(name="Retirement", nicknames=[], types=["RRSP"], icon="piggy-bank"),
    ]
    matched = match_account_group(
        nickname="My Vault RRSP",
        account_type="RRSP",
        rules=rules,
    )
    assert matched == "Special"


def test_match_account_group_type_fallback_when_no_nickname_matches():
    rules = [
        AccountGroupRule(name="Special", nicknames=["*Vault*"], types=[], icon="home"),
        AccountGroupRule(name="Retirement", nicknames=[], types=["RRSP"], icon="piggy-bank"),
    ]
    matched = match_account_group(
        nickname="Regular RRSP",
        account_type="RRSP",
        rules=rules,
    )
    assert matched == "Retirement"


def test_match_account_group_unmatched_returns_other():
    rules = [AccountGroupRule(name="Retirement", nicknames=[], types=["RRSP"], icon="piggy-bank")]
    matched = match_account_group(nickname="Some Account", account_type="TFSA", rules=rules)
    assert matched == "Other"


def test_match_account_group_empty_rules_returns_other():
    matched = match_account_group(nickname="Anything", account_type="RRSP", rules=[])
    assert matched == "Other"


# ----- security_overrides loader -----

def test_load_security_overrides_parses_buckets_and_as_of(tmp_path):
    f = tmp_path / "security_overrides.yaml"
    f.write_text(
        """
stale_after_days: 90
securities:
  VEQT.TO:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 0.5, CAN: 0.5 }
    as_of: "2026-01-15"
""".strip()
    )
    bundle = load_security_overrides(f, None)
    assert bundle.stale_after_days == 90
    veqt = bundle.securities["VEQT.TO"]
    assert veqt.asset_class == {"equity": Decimal("1.0")}
    assert veqt.sector == "provider"
    assert veqt.geography == {"US": Decimal("0.5"), "CAN": Decimal("0.5")}
    assert veqt.as_of == date(2026, 1, 15)


def test_load_security_overrides_user_file_overrides_example(tmp_path):
    example = tmp_path / "example.yaml"
    user = tmp_path / "user.yaml"
    example.write_text(
        """
stale_after_days: 180
securities:
  AAA:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-01-01"
  BBB:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-01-01"
""".strip()
    )
    user.write_text(
        """
stale_after_days: 90
securities:
  AAA:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { CAN: 1.0 }
    as_of: "2026-04-01"
""".strip()
    )
    bundle = load_security_overrides(example, user)
    assert bundle.stale_after_days == 90  # user file wins
    assert bundle.securities["AAA"].geography == {"CAN": Decimal("1.0")}
    assert bundle.securities["BBB"].geography == {"US": Decimal("1.0")}  # passthrough


def test_load_security_overrides_missing_user_file_is_fine(tmp_path):
    example = tmp_path / "example.yaml"
    example.write_text(
        """
stale_after_days: 180
securities:
  AAA:
    asset_class: { equity: 1.0 }
    sector: provider
    geography: { US: 1.0 }
    as_of: "2026-01-01"
""".strip()
    )
    bundle = load_security_overrides(example, tmp_path / "missing.yaml")
    assert bundle.stale_after_days == 180
    assert "AAA" in bundle.securities


# ----- complex_securities loader -----

def test_load_complex_securities_parses_flags(tmp_path):
    f = tmp_path / "complex.yaml"
    f.write_text(
        """
HYLD.TO: { flag: covered_call_leverage, leverage: 1.25 }
HXD.TO:  { flag: leveraged_inverse, leverage: -1.0 }
""".strip()
    )
    flags = load_complex_securities(f)
    assert flags["HYLD.TO"] == ComplexSecurityFlag(flag="covered_call_leverage", leverage=Decimal("1.25"))
    assert flags["HXD.TO"].leverage == Decimal("-1.0")


def test_load_complex_securities_missing_file_returns_empty():
    flags = load_complex_securities(Path("/nonexistent.yaml"))
    assert flags == {}


# ----- repo-bundled example files load ----

def test_committed_example_yamls_are_loadable():
    """Smoke test that the committed example files parse end-to-end."""
    bundle = load_security_overrides(REPO_ROOT / "config" / "security_overrides.example.yaml", None)
    assert bundle.stale_after_days == 180
    assert "VEQT.TO" in bundle.securities

    rules = load_account_groups(REPO_ROOT / "config" / "account_groups.example.yaml")
    assert any(r.name == "Retirement" for r in rules)

    flags = load_complex_securities(REPO_ROOT / "config" / "complex_securities.yaml")
    assert "HYLD.TO" in flags


# ----- YAML parse-error surfacing -----

def test_malformed_account_groups_raises_with_file_path(tmp_path):
    f = tmp_path / "bad_account_groups.yaml"
    f.write_text("groups:\n  - name: 'Unterminated\n")  # unterminated string
    with pytest.raises(ValueError) as exc_info:
        load_account_groups(f)
    assert str(f) in str(exc_info.value)


def test_malformed_security_overrides_raises_with_file_path(tmp_path):
    f = tmp_path / "bad_overrides.yaml"
    f.write_text("securities:\n  AAA: { unterminated\n")
    with pytest.raises(ValueError) as exc_info:
        load_security_overrides(f, None)
    assert str(f) in str(exc_info.value)


def test_malformed_complex_securities_raises_with_file_path(tmp_path):
    f = tmp_path / "bad_complex.yaml"
    f.write_text("AAA: { unterminated\n")
    with pytest.raises(ValueError) as exc_info:
        load_complex_securities(f)
    assert str(f) in str(exc_info.value)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_exposure_config.py -v`
Expected: every test fails with `ModuleNotFoundError: networthlab.services.exposure_config`.

- [ ] **Step 3: Implement the loaders**

Create `networthlab/services/exposure_config.py`:

```python
"""Loaders for the exposure feature's YAML config files."""

from __future__ import annotations

import fnmatch
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal, Union

import yaml
from pydantic import BaseModel, ConfigDict


class AccountGroupRule(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    nicknames: list[str]        # glob patterns, possibly empty
    types: list[str]            # WS unifiedAccountType values, possibly empty
    icon: str


class SecurityOverride(BaseModel):
    model_config = ConfigDict(frozen=True)
    # Each dimension is either a buckets dict OR the literal string "provider".
    asset_class: Union[dict[str, Decimal], Literal["provider"]]
    sector: Union[dict[str, Decimal], Literal["provider"]]
    geography: Union[dict[str, Decimal], Literal["provider"]]
    as_of: date


class SecurityOverrideBundle(BaseModel):
    model_config = ConfigDict(frozen=True)
    stale_after_days: int
    securities: dict[str, SecurityOverride]


class ComplexSecurityFlag(BaseModel):
    model_config = ConfigDict(frozen=True)
    flag: str
    leverage: Decimal


# ----------------------------------------------------------------------
# account_groups
# ----------------------------------------------------------------------

def _safe_load(path: Path) -> object:
    """yaml.safe_load with a clear error message that includes the file path."""
    try:
        return yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error in {path}: {exc}") from exc


def load_account_groups(path: Path) -> list[AccountGroupRule]:
    """Parse an account_groups.yaml file. Missing file -> empty list (caller surfaces a banner)."""
    if not path.is_file():
        return []
    raw = _safe_load(path)
    if not raw or "groups" not in raw:
        return []
    rules: list[AccountGroupRule] = []
    for entry in raw["groups"]:
        match = entry.get("match") or {}
        rules.append(
            AccountGroupRule(
                name=entry["name"],
                nicknames=match.get("nicknames") or [],
                types=match.get("types") or [],
                icon=entry.get("icon", "wallet"),
            )
        )
    return rules


def match_account_group(
    nickname: str, account_type: str, rules: list[AccountGroupRule]
) -> str:
    """Apply rules top-to-bottom; nickname matches considered before type matches per rule."""
    for rule in rules:
        if any(fnmatch.fnmatchcase(nickname, pat) for pat in rule.nicknames):
            return rule.name
        if account_type in rule.types:
            return rule.name
    return "Other"


# ----------------------------------------------------------------------
# security_overrides (with example + user file merge)
# ----------------------------------------------------------------------

def _parse_dimension(
    raw: object,
) -> Union[dict[str, Decimal], Literal["provider"]]:
    if raw == "provider":
        return "provider"
    if isinstance(raw, dict):
        return {k: Decimal(str(v)) for k, v in raw.items()}
    raise ValueError(f"Unexpected dimension value: {raw!r}")


def _parse_override(raw: dict) -> SecurityOverride:
    return SecurityOverride(
        asset_class=_parse_dimension(raw["asset_class"]),
        sector=_parse_dimension(raw["sector"]),
        geography=_parse_dimension(raw["geography"]),
        as_of=raw["as_of"] if isinstance(raw["as_of"], date)
              else date.fromisoformat(str(raw["as_of"])),
    )


def _load_overrides_file(path: Path) -> tuple[int | None, dict[str, SecurityOverride]]:
    if not path or not path.is_file():
        return None, {}
    raw = _safe_load(path) or {}
    stale = raw.get("stale_after_days")
    securities_raw = raw.get("securities") or {}
    securities = {symbol: _parse_override(payload) for symbol, payload in securities_raw.items()}
    return stale, securities


def load_security_overrides(
    example_path: Path, user_path: Path | None
) -> SecurityOverrideBundle:
    """Merge committed example with optional user file. User file wins per-symbol."""
    example_stale, example_secs = _load_overrides_file(example_path)
    user_stale, user_secs = _load_overrides_file(user_path) if user_path else (None, {})

    merged_secs = {**example_secs, **user_secs}  # user wins per symbol
    stale = user_stale if user_stale is not None else (example_stale or 180)
    return SecurityOverrideBundle(stale_after_days=stale, securities=merged_secs)


# ----------------------------------------------------------------------
# complex_securities
# ----------------------------------------------------------------------

def load_complex_securities(path: Path) -> dict[str, ComplexSecurityFlag]:
    if not path.is_file():
        return {}
    raw = _safe_load(path) or {}
    return {
        symbol: ComplexSecurityFlag(
            flag=payload["flag"],
            leverage=Decimal(str(payload.get("leverage", 1))),
        )
        for symbol, payload in raw.items()
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_exposure_config.py -v`
Expected: all tests pass (the 11 tests defined above).

- [ ] **Step 5: Commit**

```bash
git add networthlab/services/exposure_config.py tests/test_exposure_config.py
git commit -m "Add YAML config loaders for account_groups, security_overrides, complex_securities"
```

---

## Task 4: EtfLookthroughService — override-only path

**Goal:** the service can take a symbol and a `SecurityOverrideBundle` and produce a `SecurityClassification` when an override exists for every dimension. yfinance integration comes in Task 5.

**Files:**
- Create: `networthlab/services/etf_lookthrough.py`
- Create: `tests/test_etf_lookthrough.py`

**Steps:**

- [ ] **Step 1: Write the failing tests**

Create `tests/test_etf_lookthrough.py`:

```python
"""Tests for the ETF look-through / classification service."""

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from networthlab.models import DimensionBreakdown
from networthlab.services.etf_lookthrough import EtfLookthroughService
from networthlab.services.exposure_config import (
    SecurityOverride,
    SecurityOverrideBundle,
)


def make_override_bundle(symbol: str, **dimensions) -> SecurityOverrideBundle:
    """Helper to build a 1-symbol bundle for unit tests."""
    default_dims = {
        "asset_class": {"equity": Decimal("1.0")},
        "sector": "provider",
        "geography": {"US": Decimal("1.0")},
        "as_of": date(2026, 1, 1),
    }
    default_dims.update(dimensions)
    return SecurityOverrideBundle(
        stale_after_days=180,
        securities={symbol: SecurityOverride(**default_dims)},
    )


def test_override_full_classification_no_yfinance_call():
    bundle = make_override_bundle(
        "VEQT.TO",
        asset_class={"equity": Decimal("1.0")},
        sector={"tech": Decimal("0.5"), "financials": Decimal("0.5")},
        geography={"US": Decimal("0.45"), "CAN": Decimal("0.30"), "INTL_DEV": Decimal("0.25")},
        as_of=date(2026, 1, 15),
    )
    svc = EtfLookthroughService(
        overrides=bundle,
        complex_flags={},
        cache_dir=Path("/tmp/nonexistent_cache_dir_for_test"),
    )
    result = svc.classify(
        symbol="VEQT.TO",
        security_type="ETF",
        name="Vanguard All-Equity ETF Portfolio",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result.asset_class.source == "override"
    assert result.asset_class.buckets == {"equity": Decimal("1.0")}
    assert result.sector.source == "override"
    assert result.sector.buckets["tech"] == Decimal("0.5")
    assert result.geography.source == "override"
    assert result.geography.as_of == date(2026, 1, 15)
    assert result.complexity_flag is None


def test_complexity_flag_populated_when_symbol_in_complex_dict():
    from networthlab.services.exposure_config import ComplexSecurityFlag

    bundle = make_override_bundle("HYLD.TO")
    flags = {"HYLD.TO": ComplexSecurityFlag(flag="covered_call_leverage", leverage=Decimal("1.25"))}
    svc = EtfLookthroughService(
        overrides=bundle,
        complex_flags=flags,
        cache_dir=Path("/tmp/nonexistent_cache_dir_for_test"),
    )
    result = svc.classify(
        symbol="HYLD.TO",
        security_type="ETF",
        name="Hamilton Enhanced US Covered Call",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result.complexity_flag == "covered_call_leverage"


def test_unknown_symbol_returns_all_unclassified_when_no_yfinance(tmp_path):
    """Without an override or yfinance hit, every dimension is unclassified."""
    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
        yfinance_disabled=True,  # explicit disable for unit-test isolation
    )
    result = svc.classify(
        symbol="MYSTERY.TO",
        security_type="ETF",
        name="Mystery ETF",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    # Asset class + sector have no fallback after provider, so unclassified.
    assert result.asset_class.source == "unclassified"
    assert result.asset_class.buckets == {}
    # Geography has name-pattern + stock-exchange fallback; without yfinance
    # we have no top_holdings, name doesn't match patterns, so unclassified.
    assert result.geography.source == "unclassified"


def test_currency_dimension_always_derived_from_listing_currency():
    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=Path("/tmp/nonexistent"),
        yfinance_disabled=True,
    )
    result = svc.classify(
        symbol="ANY.TO",
        security_type="EQUITY",
        name="Anything",
        listing_exchange="TSX",
        listing_currency="USD",
    )
    assert result.currency.source == "heuristic"
    assert result.currency.buckets == {"USD": Decimal("1.0")}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_etf_lookthrough.py -v`
Expected: tests fail with `ModuleNotFoundError: networthlab.services.etf_lookthrough`.

- [ ] **Step 3: Implement the service (override + currency-from-listing only; provider/fallbacks in later tasks)**

Create `networthlab/services/etf_lookthrough.py`:

```python
"""Classify each security into per-dimension breakdowns.

MVP fallback chains (see spec §6):
  ETF asset_class: override -> provider -> unclassified
  ETF sector:      override -> provider -> unclassified
  ETF geography:   override -> name-pattern -> stock-exchange aggregation -> unclassified
  Non-ETF asset_class: override -> from security_type -> unclassified
  Non-ETF sector:      override -> provider (info["sector"]) -> unclassified
  Non-ETF geography:   override -> listing exchange -> unclassified
  currency:        always derived from listing_currency

This task implements override + currency + the unclassified default.
Provider/name-pattern/stock-exchange/listing-exchange branches are added
in Tasks 5-6.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Union

from networthlab.models import (
    ClassificationComponent,
    DimensionBreakdown,
    SecurityClassification,
)
from networthlab.services.exposure_config import (
    ComplexSecurityFlag,
    SecurityOverride,
    SecurityOverrideBundle,
)


def _unclassified(notes: list[str] | None = None) -> DimensionBreakdown:
    return DimensionBreakdown(
        buckets={},
        source="unclassified",
        as_of=None,
        notes=notes or [],
    )


def _override_breakdown(
    dim_value: Union[dict[str, Decimal], str], as_of
) -> DimensionBreakdown | None:
    """Return a DimensionBreakdown if the override is a concrete dict.
    Returns None if the override says `provider` (caller falls through)."""
    if dim_value == "provider":
        return None
    if isinstance(dim_value, dict):
        return DimensionBreakdown(
            buckets={k: Decimal(str(v)) for k, v in dim_value.items()},
            source="override",
            as_of=as_of,
            notes=[],
        )
    return None


class EtfLookthroughService:
    """Classify each held symbol into per-dimension breakdowns.

    `yfinance_disabled=True` short-circuits any network call — used in unit tests.
    """

    def __init__(
        self,
        overrides: SecurityOverrideBundle,
        complex_flags: dict[str, ComplexSecurityFlag],
        cache_dir: Path,
        yfinance_disabled: bool = False,
    ):
        self.overrides = overrides
        self.complex_flags = complex_flags
        self.cache_dir = cache_dir
        self.yfinance_disabled = yfinance_disabled

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def classify(
        self,
        symbol: str,
        security_type: str,
        name: str,
        listing_exchange: str,
        listing_currency: str,
    ) -> SecurityClassification:
        override = self.overrides.securities.get(symbol)
        is_etf = security_type.upper() == "ETF"

        asset_class = self._classify_asset_class(override, is_etf, security_type)
        sector = self._classify_sector(override, is_etf, symbol)
        geography = self._classify_geography(override, is_etf, name, listing_exchange, symbol)
        currency = self._derive_currency(listing_currency)

        flag = self.complex_flags.get(symbol)

        return SecurityClassification(
            symbol=symbol,
            asset_class=asset_class,
            geography=geography,
            sector=sector,
            currency=currency,
            complexity_flag=flag.flag if flag else None,
            components=[
                ClassificationComponent(
                    symbol=symbol,
                    weight=Decimal("1.0"),
                    source=asset_class.source,
                )
            ],
            fetched_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Per-dimension chains
    # ------------------------------------------------------------------

    def _classify_asset_class(
        self, override: SecurityOverride | None, is_etf: bool, security_type: str
    ) -> DimensionBreakdown:
        if override:
            ob = _override_breakdown(override.asset_class, override.as_of)
            if ob:
                return ob
        # Provider path (Task 5) goes here for ETFs.
        # Non-ETF path (Task 5/6): derive from security_type.
        return _unclassified(notes=["no override; provider not implemented in this task"])

    def _classify_sector(
        self, override: SecurityOverride | None, is_etf: bool, symbol: str
    ) -> DimensionBreakdown:
        if override:
            ob = _override_breakdown(override.sector, override.as_of)
            if ob:
                return ob
        # Provider path (Task 5) goes here.
        return _unclassified(notes=["no override; provider not implemented in this task"])

    def _classify_geography(
        self,
        override: SecurityOverride | None,
        is_etf: bool,
        name: str,
        listing_exchange: str,
        symbol: str,
    ) -> DimensionBreakdown:
        if override:
            ob = _override_breakdown(override.geography, override.as_of)
            if ob:
                return ob
        # Name-pattern / stock-exchange / listing-exchange fallbacks (Task 6) go here.
        return _unclassified(notes=["no override; geography fallbacks not implemented in this task"])

    def _derive_currency(self, listing_currency: str) -> DimensionBreakdown:
        return DimensionBreakdown(
            buckets={listing_currency: Decimal("1.0")},
            source="heuristic",
            as_of=None,
            notes=[],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_etf_lookthrough.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add networthlab/services/etf_lookthrough.py tests/test_etf_lookthrough.py
git commit -m "Add EtfLookthroughService with override-only classification path"
```

---

## Task 5: EtfLookthroughService — yfinance provider path

**Goal:** add provider-data classification (yfinance `funds_data` for ETFs, `info["sector"]` for stocks). Tests mock yfinance.

**Files:**
- Modify: `networthlab/services/etf_lookthrough.py`
- Modify: `tests/test_etf_lookthrough.py`

**Steps:**

- [ ] **Step 1: Add failing tests for the provider path**

Append to `tests/test_etf_lookthrough.py`:

```python
# --- yfinance provider path (Task 5) -----------------------------------


@pytest.fixture
def fake_funds_data():
    """Synthetic yfinance.Ticker(symbol).funds_data shape."""

    class FakeFundsData:
        sector_weightings = {
            "technology": 0.5,
            "financials": 0.3,
            "healthcare": 0.2,
        }
        asset_classes = {
            "stockPosition": 0.99,
            "cashPosition": 0.01,
            "bondPosition": 0.0,
        }

        class FakeTopHoldings:
            def to_dict(self_inner):
                return {}  # not exercised here

        top_holdings = FakeTopHoldings()

    return FakeFundsData()


def test_etf_uses_provider_when_override_says_provider(mocker, fake_funds_data, tmp_path):
    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.funds_data = fake_funds_data

    bundle = make_override_bundle(
        "FAKE.TO",
        asset_class="provider",
        sector="provider",
        geography={"US": Decimal("1.0")},  # still override geography
        as_of=date(2026, 1, 1),
    )
    svc = EtfLookthroughService(
        overrides=bundle, complex_flags={}, cache_dir=tmp_path,
    )
    result = svc.classify(
        symbol="FAKE.TO",
        security_type="ETF",
        name="Fake ETF",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    # asset_class came from provider (was "provider" in override)
    assert result.asset_class.source == "provider"
    assert result.asset_class.buckets["equity"] == Decimal("0.99")
    assert result.asset_class.buckets["cash"] == Decimal("0.01")
    # sector also from provider
    assert result.sector.source == "provider"
    assert result.sector.buckets["technology"] == Decimal("0.5")
    # geography from override (was a concrete dict)
    assert result.geography.source == "override"


def test_etf_provider_missing_fields_yields_unclassified(mocker, tmp_path):
    """If yfinance returns no useful data, mark unclassified — don't crash."""

    class EmptyFundsData:
        sector_weightings = {}
        asset_classes = {}

        class FakeTopHoldings:
            def to_dict(self_inner):
                return {}

        top_holdings = FakeTopHoldings()

    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.funds_data = EmptyFundsData()

    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
    )
    result = svc.classify(
        symbol="EMPTY.TO",
        security_type="ETF",
        name="Empty ETF",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result.asset_class.source == "unclassified"
    assert result.sector.source == "unclassified"
    assert result.asset_class.buckets == {}


def test_non_etf_asset_class_from_security_type(tmp_path):
    """For stocks/crypto, asset_class is derived from security_type — no yfinance call."""
    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
        yfinance_disabled=True,
    )
    result_eq = svc.classify(
        symbol="SHOP.TO",
        security_type="EQUITY",
        name="Shopify Inc",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result_eq.asset_class.source == "heuristic"
    assert result_eq.asset_class.buckets == {"equity": Decimal("1.0")}

    result_crypto = svc.classify(
        symbol="BTC",
        security_type="CRYPTO",
        name="Bitcoin",
        listing_exchange="WS_CRYPTO",
        listing_currency="CAD",
    )
    assert result_crypto.asset_class.buckets == {"crypto": Decimal("1.0")}


def test_non_etf_sector_from_yfinance_info(mocker, tmp_path):
    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.info = {"sector": "Technology", "quoteType": "EQUITY"}

    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
    )
    result = svc.classify(
        symbol="AAPL",
        security_type="EQUITY",
        name="Apple Inc",
        listing_exchange="NASDAQ",
        listing_currency="USD",
    )
    assert result.sector.source == "provider"
    assert result.sector.buckets == {"technology": Decimal("1.0")}
```

- [ ] **Step 2: Run new tests to verify they fail**

Run: `pytest tests/test_etf_lookthrough.py -v`
Expected: 4 new failures (`networthlab.services.etf_lookthrough.yf` doesn't exist yet, plus the asset-class-from-type and provider branches aren't implemented).

- [ ] **Step 3: Implement the provider branches**

Update two of the helper methods (`_classify_asset_class` and `_classify_sector`) in `networthlab/services/etf_lookthrough.py`. `_classify_geography` is updated in Task 6.

At the top of the file, add the import (kept lazy by alias for mock-patching):

```python
import yfinance as yf  # mocked in tests via networthlab.services.etf_lookthrough.yf
```

Define a sector normalization map and asset-class-from-security-type map at module level:

```python
# yfinance asset_classes keys -> bucket names we use throughout the dashboard.
# yfinance returns sectors as e.g. "consumer_cyclical" — we keep its keys directly
# and let the UI title-case them.
_YF_ASSET_CLASS_MAP = {
    "stockPosition": "equity",
    "bondPosition": "bond",
    "cashPosition": "cash",
    "preferredPosition": "preferred",
    "convertiblePosition": "convertible",
    "otherPosition": "other",
}

_SECURITY_TYPE_ASSET_CLASS = {
    "EQUITY": "equity",
    "STOCK": "equity",
    "ETF": "equity",       # only used when ETF asset_class fully unclassified
    "BOND": "bond",
    "CRYPTO": "crypto",
    "CASH": "cash",
    "OPTION": "option",
}
```

Replace `_classify_asset_class` (note the added `symbol` parameter; the call site in `classify()` must be updated to pass it):

```python
    def _classify_asset_class(
        self,
        override: SecurityOverride | None,
        is_etf: bool,
        security_type: str,
        symbol: str,
    ) -> DimensionBreakdown:
        if override:
            ob = _override_breakdown(override.asset_class, override.as_of)
            if ob:
                return ob
        if not is_etf:
            bucket = _SECURITY_TYPE_ASSET_CLASS.get(security_type.upper())
            if bucket:
                return DimensionBreakdown(
                    buckets={bucket: Decimal("1.0")},
                    source="heuristic",
                    as_of=None,
                    notes=[f"derived from security_type={security_type}"],
                )
            return _unclassified(notes=[f"unknown security_type={security_type}"])
        if self.yfinance_disabled:
            return _unclassified(notes=["yfinance disabled"])
        try:
            fd = self._get_funds_data(symbol)
            raw = getattr(fd, "asset_classes", None) or {}
        except Exception as exc:
            return _unclassified(notes=[f"yfinance error: {exc!s}"])
        buckets: dict[str, Decimal] = {}
        for yf_key, weight in raw.items():
            bucket = _YF_ASSET_CLASS_MAP.get(yf_key, yf_key)
            w = Decimal(str(weight))
            if w > 0:
                buckets[bucket] = buckets.get(bucket, Decimal("0")) + w
        if not buckets:
            return _unclassified(notes=["yfinance asset_classes empty"])
        return DimensionBreakdown(
            buckets=buckets, source="provider", as_of=None, notes=[]
        )
```

Replace `_classify_sector` with:

```python
    def _classify_sector(
        self,
        override: SecurityOverride | None,
        is_etf: bool,
        symbol: str,
    ) -> DimensionBreakdown:
        if override:
            ob = _override_breakdown(override.sector, override.as_of)
            if ob:
                return ob
        if self.yfinance_disabled:
            return _unclassified(notes=["yfinance disabled"])
        try:
            if is_etf:
                fd = self._get_funds_data(symbol)
                raw = getattr(fd, "sector_weightings", None) or {}
            else:
                info = self._get_info(symbol)
                sector_name = (info or {}).get("sector")
                raw = {sector_name.lower(): 1.0} if sector_name else {}
        except Exception as exc:
            return _unclassified(notes=[f"yfinance error: {exc!s}"])
        buckets: dict[str, Decimal] = {}
        for key, weight in raw.items():
            w = Decimal(str(weight))
            if w > 0:
                buckets[str(key)] = buckets.get(str(key), Decimal("0")) + w
        if not buckets:
            return _unclassified(notes=["yfinance sector data empty"])
        return DimensionBreakdown(
            buckets=buckets, source="provider", as_of=None, notes=[]
        )
```

Update `classify()` to pass `symbol` to the asset-class call:

```python
        asset_class = self._classify_asset_class(override, is_etf, security_type, symbol)
```

Add the lightweight yfinance helpers at the bottom of the class:

```python
    # ------------------------------------------------------------------
    # yfinance wrappers — kept thin so tests can mock yf.Ticker
    # ------------------------------------------------------------------

    def _get_funds_data(self, symbol: str):
        return yf.Ticker(symbol).funds_data

    def _get_info(self, symbol: str):
        return yf.Ticker(symbol).info
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_etf_lookthrough.py -v`
Expected: all 8 tests pass (the 4 from Task 4 plus the 4 new ones).

- [ ] **Step 5: Commit**

```bash
git add networthlab/services/etf_lookthrough.py tests/test_etf_lookthrough.py
git commit -m "EtfLookthrough: provider data for ETFs (funds_data) and stocks (info)"
```

---

## Task 6: EtfLookthroughService — geography fallbacks

**Goal:** add the geography fallback chain (name-pattern, stock-exchange aggregation, non-ETF listing-exchange).

**Files:**
- Modify: `networthlab/services/etf_lookthrough.py`
- Modify: `tests/test_etf_lookthrough.py`

**Steps:**

- [ ] **Step 1: Write failing tests**

Append to `tests/test_etf_lookthrough.py`:

```python
# --- Geography fallbacks (Task 6) -------------------------------------


def test_geography_name_pattern_us(mocker, tmp_path):
    """ETF whose name contains 'S&P 500' classifies as US."""

    class EmptyFD:
        sector_weightings = {}
        asset_classes = {}

        class TH:
            def to_dict(self_inner):
                return {}

        top_holdings = TH()

    mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker").return_value.funds_data = EmptyFD()

    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
    )
    result = svc.classify(
        symbol="SPY",
        security_type="ETF",
        name="SPDR S&P 500 ETF Trust",
        listing_exchange="NYSE",
        listing_currency="USD",
    )
    assert result.geography.source == "heuristic"
    assert result.geography.buckets == {"US": Decimal("1.0")}


def test_geography_stock_exchange_aggregation(mocker, tmp_path):
    """ETF whose top_holdings are predominantly NASDAQ-listed stocks => US."""

    class FD:
        sector_weightings = {}
        asset_classes = {}

        class TH:
            def to_dict(self_inner):
                # Each row: {symbol: {"Holding Percent": pct, "quoteType": ..., "exchange": ...}}
                return {
                    "Holding Percent": {"NVDA": 0.10, "AAPL": 0.08, "MSFT": 0.07},
                    "exchange": {"NVDA": "NASDAQ", "AAPL": "NASDAQ", "MSFT": "NASDAQ"},
                    "quoteType": {"NVDA": "EQUITY", "AAPL": "EQUITY", "MSFT": "EQUITY"},
                }

        top_holdings = TH()

    mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker").return_value.funds_data = FD()

    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
    )
    result = svc.classify(
        symbol="MYSTERY_BASKET",
        security_type="ETF",
        # Name deliberately avoids ALL patterns ('S&P 500', 'Total US', 'NASDAQ',
        # 'FTSE Canada', etc.) so the algorithm MUST reach step 4 (stock-exchange
        # aggregation across top_holdings) to produce a result.
        name="Generic Quality Equity Basket",
        listing_exchange="NEO",  # ETF listing exchange would NOT alone produce US
        listing_currency="USD",
    )
    assert result.geography.source == "heuristic"
    assert "US" in result.geography.buckets
    assert result.geography.buckets["US"] == Decimal("1.0")  # all top_holdings are NASDAQ
    assert "top_holdings" in (result.geography.notes[0] if result.geography.notes else "")


def test_geography_non_etf_uses_listing_exchange(tmp_path):
    """For individual stocks, geography is derived directly from listing_exchange."""
    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
        yfinance_disabled=True,
    )
    shop = svc.classify(
        symbol="SHOP.TO",
        security_type="EQUITY",
        name="Shopify Inc",
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert shop.geography.source == "heuristic"
    assert shop.geography.buckets == {"CAN": Decimal("1.0")}

    nvda = svc.classify(
        symbol="NVDA",
        security_type="EQUITY",
        name="NVIDIA",
        listing_exchange="NASDAQ",
        listing_currency="USD",
    )
    assert nvda.geography.buckets == {"US": Decimal("1.0")}


def test_etf_geography_listing_exchange_NOT_used_as_fallback(mocker, tmp_path):
    """Per spec §10: ETF with no override / no provider / no name match / no top_holdings
    must end up Unclassified — NOT default to its listing exchange country."""

    class FD:
        sector_weightings = {}
        asset_classes = {}

        class TH:
            def to_dict(self_inner):
                return {}

        top_holdings = TH()

    mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker").return_value.funds_data = FD()

    svc = EtfLookthroughService(
        overrides=SecurityOverrideBundle(stale_after_days=180, securities={}),
        complex_flags={},
        cache_dir=tmp_path,
    )
    result = svc.classify(
        symbol="MYSTERY.TO",
        security_type="ETF",
        name="Mystery Strategy Fund",  # name doesn't match patterns
        listing_exchange="TSX",
        listing_currency="CAD",
    )
    assert result.geography.source == "unclassified"
    assert result.geography.buckets == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_etf_lookthrough.py -v`
Expected: the 4 new tests fail; the previous 8 still pass.

- [ ] **Step 3: Implement geography fallbacks**

In `networthlab/services/etf_lookthrough.py`, add module-level constants:

```python
# Name-pattern -> country (geography, ETF only). First match wins.
_NAME_PATTERNS: list[tuple[str, str]] = [
    ("s&p 500", "US"),
    ("total us", "US"),
    ("us total", "US"),
    ("nasdaq", "US"),
    ("ftse canada", "CAN"),
    ("tsx 60", "CAN"),
    ("tsx composite", "CAN"),
    ("eafe", "INTL_DEV"),
    ("intl developed", "INTL_DEV"),
    ("emerging markets", "EM"),
]

# Listing exchange -> country (used for non-ETF positions AND for
# stock-exchange aggregation across an ETF's top_holdings).
_EXCHANGE_COUNTRY: dict[str, str] = {
    "NASDAQ": "US",
    "NYSE": "US",
    "AMEX": "US",
    "BATS": "US",
    "ARCA": "US",
    "NMS": "US",
    "TSX": "CAN",
    "TSXV": "CAN",
    "NEO": "CAN",
    "LSE": "INTL_DEV",
    "TYO": "INTL_DEV",
    "FRA": "INTL_DEV",
    "ASX": "INTL_DEV",
    "HKEX": "EM",
    "SSE": "EM",
    "BSE": "EM",
    "NSE": "EM",
}
```

Replace `_classify_geography` with:

```python
    def _classify_geography(
        self,
        override: SecurityOverride | None,
        is_etf: bool,
        name: str,
        listing_exchange: str,
        symbol: str,
    ) -> DimensionBreakdown:
        if override:
            ob = _override_breakdown(override.geography, override.as_of)
            if ob:
                return ob

        # Non-ETF: listing-exchange directly.
        if not is_etf:
            country = _EXCHANGE_COUNTRY.get(listing_exchange.upper())
            if country:
                return DimensionBreakdown(
                    buckets={country: Decimal("1.0")},
                    source="heuristic",
                    as_of=None,
                    notes=[f"from listing_exchange={listing_exchange}"],
                )
            return _unclassified(notes=[f"unknown listing_exchange={listing_exchange}"])

        # ETF geography fallback chain.
        if self.yfinance_disabled:
            return _unclassified(notes=["yfinance disabled"])

        # 1) Name-pattern.
        name_lower = (name or "").lower()
        for pattern, country in _NAME_PATTERNS:
            if pattern in name_lower:
                return DimensionBreakdown(
                    buckets={country: Decimal("1.0")},
                    source="heuristic",
                    as_of=None,
                    notes=[f"name matched '{pattern}'"],
                )

        # 2) Stock-exchange aggregation across top_holdings.
        try:
            fd = self._get_funds_data(symbol)
            th = getattr(fd, "top_holdings", None)
            raw = th.to_dict() if th is not None and hasattr(th, "to_dict") else {}
        except Exception as exc:
            return _unclassified(notes=[f"yfinance top_holdings error: {exc!s}"])

        weights = raw.get("Holding Percent") or {}
        exchanges = raw.get("exchange") or {}
        quote_types = raw.get("quoteType") or {}

        if weights:
            stock_count = sum(1 for s, qt in quote_types.items() if str(qt).upper() == "EQUITY")
            if quote_types and (stock_count / max(len(quote_types), 1)) >= 0.8:
                buckets: dict[str, Decimal] = {}
                for sub_symbol, pct in weights.items():
                    ex = (exchanges.get(sub_symbol) or "").upper()
                    country = _EXCHANGE_COUNTRY.get(ex)
                    if country:
                        buckets[country] = buckets.get(country, Decimal("0")) + Decimal(str(pct))
                # Renormalize so weights sum to 1.0 (top_holdings may be partial).
                total = sum(buckets.values())
                if total > 0:
                    buckets = {k: v / total for k, v in buckets.items()}
                    return DimensionBreakdown(
                        buckets=buckets,
                        source="heuristic",
                        as_of=None,
                        notes=[f"aggregated {len(weights)} top_holdings by exchange"],
                    )

        # 3) No fallback to listing_exchange for ETFs (spec §10).
        return _unclassified(notes=["ETF geography: no override/name/top_holdings match"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_etf_lookthrough.py -v`
Expected: all 12 tests pass.

- [ ] **Step 5: Commit**

```bash
git add networthlab/services/etf_lookthrough.py tests/test_etf_lookthrough.py
git commit -m "EtfLookthrough: geography fallbacks (name-pattern, stock-exchange agg, non-ETF exchange)"
```

---

## Task 7: yfinance disk cache + staleness chip + dependency wiring

**Goal:** persist yfinance results to `~/.networthlab/yfinance_cache.json` with 24h TTL, and add a helper that callers use to derive the "review override" chip.

**Files:**
- Modify: `networthlab/services/etf_lookthrough.py`
- Modify: `tests/test_etf_lookthrough.py`

**Steps:**

- [ ] **Step 1: Write failing tests**

Append to `tests/test_etf_lookthrough.py`:

```python
# --- Cache + staleness (Task 7) ---------------------------------------


def test_cache_avoids_second_yfinance_call(mocker, tmp_path, fake_funds_data):
    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.funds_data = fake_funds_data

    bundle = make_override_bundle("FAKE.TO", asset_class="provider", sector="provider")
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)

    svc.classify("FAKE.TO", "ETF", "Fake ETF", "TSX", "CAD")
    svc.classify("FAKE.TO", "ETF", "Fake ETF", "TSX", "CAD")

    # First call hits yfinance (funds_data property access); second uses cache.
    assert mock_ticker.call_count == 1


def test_cache_refetches_after_ttl_expires(mocker, tmp_path, fake_funds_data):
    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.funds_data = fake_funds_data

    import json
    from datetime import datetime, timedelta, timezone

    bundle = make_override_bundle("FAKE.TO", asset_class="provider", sector="provider")
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)
    svc.classify("FAKE.TO", "ETF", "Fake ETF", "TSX", "CAD")

    # Backdate the cache entry by 25h.
    cache_file = tmp_path / "yfinance_cache.json"
    data = json.loads(cache_file.read_text())
    stale = datetime.now(timezone.utc) - timedelta(hours=25)
    data["FAKE.TO"]["fetched_at"] = stale.isoformat()
    cache_file.write_text(json.dumps(data))

    svc2 = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)
    svc2.classify("FAKE.TO", "ETF", "Fake ETF", "TSX", "CAD")
    assert mock_ticker.call_count == 2  # refetched


def test_is_override_stale_helper(tmp_path):
    from datetime import date, timedelta

    bundle = SecurityOverrideBundle(stale_after_days=180, securities={})
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)

    fresh = date.today() - timedelta(days=30)
    old = date.today() - timedelta(days=200)
    assert svc.is_override_stale(fresh) is False
    assert svc.is_override_stale(old) is True
    assert svc.is_override_stale(None) is False


def test_clear_symbols_evicts_only_listed_symbols(mocker, tmp_path, fake_funds_data):
    """Refresh button (spec §11) must bust cache for currently-held symbols only."""
    mock_ticker = mocker.patch("networthlab.services.etf_lookthrough.yf.Ticker")
    mock_ticker.return_value.funds_data = fake_funds_data

    bundle = SecurityOverrideBundle(
        stale_after_days=180,
        securities={
            "AAA.TO": SecurityOverride(
                asset_class="provider", sector="provider",
                geography={"US": Decimal("1.0")}, as_of=date(2026, 1, 1),
            ),
            "BBB.TO": SecurityOverride(
                asset_class="provider", sector="provider",
                geography={"US": Decimal("1.0")}, as_of=date(2026, 1, 1),
            ),
        },
    )
    svc = EtfLookthroughService(overrides=bundle, complex_flags={}, cache_dir=tmp_path)
    svc.classify("AAA.TO", "ETF", "AAA", "TSX", "CAD")
    svc.classify("BBB.TO", "ETF", "BBB", "TSX", "CAD")
    assert mock_ticker.call_count == 2

    svc.clear_symbols(["AAA.TO"])  # only AAA cleared
    svc.classify("AAA.TO", "ETF", "AAA", "TSX", "CAD")   # refetch
    svc.classify("BBB.TO", "ETF", "BBB", "TSX", "CAD")   # still cache hit
    assert mock_ticker.call_count == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_etf_lookthrough.py -v`
Expected: the 3 new tests fail.

- [ ] **Step 3: Implement the cache + staleness helper**

Add imports at the top of `networthlab/services/etf_lookthrough.py`:

```python
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
```

Add module-level constants:

```python
_CACHE_FILE_NAME = "yfinance_cache.json"
_CACHE_TTL = timedelta(hours=24)
```

Add cache load/save + memoization to `EtfLookthroughService.__init__` and add a `_cache_lookup` / `_cache_store` pair:

```python
    def __init__(
        self,
        overrides: SecurityOverrideBundle,
        complex_flags: dict[str, ComplexSecurityFlag],
        cache_dir: Path,
        yfinance_disabled: bool = False,
    ):
        self.overrides = overrides
        self.complex_flags = complex_flags
        self.cache_dir = cache_dir
        self.yfinance_disabled = yfinance_disabled
        self._cache: dict[str, dict] = self._load_cache()

    # ------------------------------------------------------------------
    # Disk cache (yfinance results)
    # ------------------------------------------------------------------

    def _cache_path(self) -> Path:
        return self.cache_dir / _CACHE_FILE_NAME

    def _load_cache(self) -> dict[str, dict]:
        path = self._cache_path()
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_cache(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path().write_text(json.dumps(self._cache, indent=2, default=str))

    def _cache_lookup(self, symbol: str, field: str):
        entry = self._cache.get(symbol)
        if not entry:
            return None
        try:
            fetched = datetime.fromisoformat(entry["fetched_at"])
        except (KeyError, ValueError):
            return None
        if datetime.now(timezone.utc) - fetched > _CACHE_TTL:
            return None
        return entry.get(field)

    def _cache_store(self, symbol: str, field: str, value) -> None:
        entry = self._cache.setdefault(
            symbol, {"fetched_at": datetime.now(timezone.utc).isoformat()}
        )
        entry["fetched_at"] = datetime.now(timezone.utc).isoformat()
        entry[field] = value
        self._save_cache()
```

Update `_get_funds_data` and `_get_info` to use the cache:

```python
    def _get_funds_data(self, symbol: str):
        cached = self._cache_lookup(symbol, "funds_data")
        if cached is not None:
            return _DictAttr(cached)
        raw = yf.Ticker(symbol).funds_data
        snapshot = {
            "sector_weightings": dict(getattr(raw, "sector_weightings", {}) or {}),
            "asset_classes": dict(getattr(raw, "asset_classes", {}) or {}),
            "top_holdings": (
                raw.top_holdings.to_dict()
                if getattr(raw, "top_holdings", None) is not None
                and hasattr(raw.top_holdings, "to_dict")
                else {}
            ),
        }
        self._cache_store(symbol, "funds_data", snapshot)
        return _DictAttr(snapshot)

    def _get_info(self, symbol: str):
        cached = self._cache_lookup(symbol, "info")
        if cached is not None:
            return cached
        info = dict(yf.Ticker(symbol).info or {})
        self._cache_store(symbol, "info", info)
        return info
```

Define a tiny adapter at module level so the cached snapshot can be read like the yfinance object (the existing code does `fd.sector_weightings`, `fd.top_holdings.to_dict()`):

```python
class _DictAttr:
    """Adapt a cached dict back to the yfinance funds_data shape so the rest
    of the classifier doesn't care whether data came from cache or live."""

    class _ToDict:
        def __init__(self, payload):
            self._payload = payload

        def to_dict(self):
            return self._payload

    def __init__(self, payload: dict):
        self.sector_weightings = payload.get("sector_weightings", {})
        self.asset_classes = payload.get("asset_classes", {})
        self.top_holdings = _DictAttr._ToDict(payload.get("top_holdings", {}))
```

Add the staleness helper:

```python
    def is_override_stale(self, as_of: date | None) -> bool:
        if as_of is None:
            return False
        return (date.today() - as_of).days > self.overrides.stale_after_days

    def clear_symbols(self, symbols: list[str]) -> None:
        """Evict the given symbols from the yfinance cache (spec §11).

        Called by ExposureState.refresh so that a user-initiated refresh
        actually re-fetches data for currently-held symbols instead of
        re-reading the same 24h-cached snapshot.
        """
        changed = False
        for symbol in symbols:
            if symbol in self._cache:
                del self._cache[symbol]
                changed = True
        if changed:
            self._save_cache()
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `pytest tests/test_etf_lookthrough.py -v`
Expected: all 15 tests pass.

- [ ] **Step 5: Commit**

```bash
git add networthlab/services/etf_lookthrough.py tests/test_etf_lookthrough.py
git commit -m "EtfLookthrough: 24h yfinance disk cache + override staleness helper"
```

---

## Task 8: WealthsimpleService

**Goal:** load session from keyring, fetch positions via `ws_api`, normalize to `list[Position]`, persist a fallback snapshot, return both positions and a "cache_stale_minutes" hint.

**Files:**
- Create: `networthlab/services/wealthsimple.py`
- Create: `tests/test_wealthsimple_service.py`

**Steps:**

- [ ] **Step 1: Write failing tests**

Create `tests/test_wealthsimple_service.py`:

```python
"""Tests for WealthsimpleService — session, fetch, normalization, fallback cache."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from networthlab.services.wealthsimple import (
    PositionsResult,
    WealthsimpleAuthMissing,
    WealthsimpleService,
)


def make_account(account_id: str, type_: str, nickname: str) -> dict:
    return {
        "id": account_id,
        "unifiedAccountType": type_,
        "nickname": nickname,
    }


def make_position(symbol: str, value_cad: str, account_id: str, security_type: str = "EQUITY"):
    """Mimic the shape ws_api returns from get_identity_positions(includeAccountData=True)."""
    return {
        "id": f"pos-{symbol}-{account_id}",
        "accounts": [{"id": account_id}],
        "quantity": "10",
        "averagePrice": {"amount": "10", "currency": "CAD"},
        "marketBookValue": {"amount": "100", "currency": "CAD"},
        "totalValue": {"amount": value_cad, "currency": "CAD"},
        "security": {
            "id": f"sec-{symbol}",
            "currency": "CAD",
            "securityType": security_type,
            "stock": {
                "symbol": symbol,
                "name": f"{symbol} Inc",
                "primaryExchange": "TSX",
            },
        },
    }


def test_load_session_returns_none_when_keyring_empty(mocker):
    mocker.patch("networthlab.services.wealthsimple.keyring.get_password", return_value=None)
    assert WealthsimpleService.load_session() is None


def test_load_session_parses_keyring_json(mocker):
    mocker.patch(
        "networthlab.services.wealthsimple.keyring.get_password",
        return_value='{"access_token":"x","refresh_token":"y"}',
    )
    sess = WealthsimpleService.load_session()
    assert sess is not None
    assert sess.access_token == "x"


def test_fetch_positions_normalizes_and_writes_cache(mocker, tmp_path):
    mock_api = mocker.MagicMock()
    mock_api.get_accounts.return_value = [
        make_account("acct-1", "RRSP", "My RRSP"),
        make_account("acct-2", "TFSA", "My TFSA"),
    ]
    mock_api.get_token_info.return_value = {"identity_canonical_id": "identity-1"}
    # Production calls do_graphql_query("FetchIdentityPositions", ...) directly
    # to force includeSecurity=True; we stub that method (not get_identity_positions).
    mock_api.do_graphql_query.return_value = [
        {"node": make_position("VEQT.TO", "5000", "acct-1", "ETF")},
        {"node": make_position("AAPL", "1500", "acct-2", "EQUITY")},
    ]
    mocker.patch(
        "networthlab.services.wealthsimple.WealthsimpleAPI.from_token",
        return_value=mock_api,
    )

    svc = WealthsimpleService(cache_dir=tmp_path)
    # Inject a fake session so we don't need keyring in this test:
    svc._session_override = mocker.MagicMock(access_token="x")

    result = svc.fetch_positions()
    assert isinstance(result, PositionsResult)
    assert result.stale_minutes == 0
    assert len(result.positions) == 2
    symbols = {p.symbol for p in result.positions}
    assert symbols == {"VEQT.TO", "AAPL"}
    veqt = next(p for p in result.positions if p.symbol == "VEQT.TO")
    assert veqt.market_value_cad == Decimal("5000")
    assert veqt.account_type == "RRSP"
    assert veqt.account_nickname == "My RRSP"

    cache_file = tmp_path / "positions_cache.json"
    assert cache_file.is_file()
    cached = json.loads(cache_file.read_text())
    assert cached["positions"][0]["symbol"] in {"VEQT.TO", "AAPL"}

    # Critical: verify we called do_graphql_query with includeSecurity=True,
    # otherwise the production payload would lack the metadata our pipeline needs.
    call = mock_api.do_graphql_query.call_args
    assert call.args[0] == "FetchIdentityPositions"
    assert call.args[1]["includeSecurity"] is True
    assert call.args[1]["includeAccountData"] is True


def test_fetch_positions_must_request_includeSecurity_flag(mocker, tmp_path):
    """Regression guard: the helper get_identity_positions hides the bug because
    it doesn't pass includeSecurity. Make sure we explicitly call do_graphql_query."""
    mock_api = mocker.MagicMock()
    mock_api.get_accounts.return_value = []
    mock_api.get_token_info.return_value = {"identity_canonical_id": "id"}
    mock_api.do_graphql_query.return_value = []
    mocker.patch(
        "networthlab.services.wealthsimple.WealthsimpleAPI.from_token",
        return_value=mock_api,
    )
    svc = WealthsimpleService(cache_dir=tmp_path)
    svc._session_override = mocker.MagicMock(access_token="x")
    svc.fetch_positions()
    # Ensure the wrong path (get_identity_positions wrapper) is not used.
    assert not mock_api.get_identity_positions.called
    assert mock_api.do_graphql_query.called


def test_fetch_positions_falls_back_to_cache_on_api_failure(mocker, tmp_path):
    # Seed the cache with a previous-known-good snapshot.
    cache_file = tmp_path / "positions_cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "positions": [
                    {
                        "account_id": "acct-1",
                        "account_type": "RRSP",
                        "account_nickname": "My RRSP",
                        "symbol": "VEQT.TO",
                        "name": "Vanguard All-Equity",
                        "security_type": "ETF",
                        "listing_currency": "CAD",
                        "listing_exchange": "TSX",
                        "quantity": "10",
                        "market_value_cad": "5000",
                        "book_value_cad": "4800",
                    }
                ],
            }
        )
    )

    mocker.patch(
        "networthlab.services.wealthsimple.WealthsimpleAPI.from_token",
        side_effect=RuntimeError("network down"),
    )

    svc = WealthsimpleService(cache_dir=tmp_path)
    svc._session_override = mocker.MagicMock(access_token="x")
    result = svc.fetch_positions()
    assert result.stale_minutes >= 0
    assert len(result.positions) == 1
    assert result.warnings  # something complaining about the failure


def test_fetch_positions_raises_when_no_session(mocker, tmp_path):
    mocker.patch("networthlab.services.wealthsimple.keyring.get_password", return_value=None)
    svc = WealthsimpleService(cache_dir=tmp_path)
    with pytest.raises(WealthsimpleAuthMissing):
        svc.fetch_positions()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_wealthsimple_service.py -v`
Expected: tests fail with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the service**

Create `networthlab/services/wealthsimple.py`:

```python
"""Wealthsimple session handling and position fetch, normalized to `Position`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import keyring
from ws_api import WealthsimpleAPI, WSAPISession

from networthlab.models import Position

KEYRING_SERVICE = "lunchsimple"
KEYRING_KEY = "session"
CACHE_FILE_NAME = "positions_cache.json"


class WealthsimpleAuthMissing(RuntimeError):
    """Raised when no session is available — UI should show a 'run lunchsimple login' banner."""


@dataclass
class PositionsResult:
    positions: list[Position]
    stale_minutes: int  # 0 when fresh; positive when rendered from cache fallback
    warnings: list[str]


class WealthsimpleService:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        # Test-only injection point.
        self._session_override: WSAPISession | None = None

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    @staticmethod
    def load_session() -> WSAPISession | None:
        raw = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
        if not raw:
            return None
        try:
            return WSAPISession.from_json(raw)
        except Exception:
            return None

    @staticmethod
    def persist_session(session_json: str) -> None:
        """Called by ws_api when it refreshes the access token."""
        keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, session_json)

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def fetch_positions(self) -> PositionsResult:
        session = self._session_override or self.load_session()
        if not session:
            raise WealthsimpleAuthMissing(
                "No Wealthsimple session found in keyring — run `lunchsimple login`."
            )

        try:
            api = WealthsimpleAPI.from_token(session, self.persist_session)
            accounts = api.get_accounts()
            # IMPORTANT: ws_api 0.34.0's get_identity_positions() helper does NOT
            # pass includeSecurity=True, and the GraphQL query gates the
            # SecuritySummary fragment behind `@include(if: $includeSecurity)`.
            # Without the flag, security.stock.{symbol,name,primaryExchange},
            # security.securityType, and security.currency are absent from the
            # response — the entire look-through pipeline depends on them.
            # Call the underlying GraphQL query directly so we get the metadata.
            edges = api.do_graphql_query(
                "FetchIdentityPositions",
                {
                    "identityId": api.get_token_info().get("identity_canonical_id"),
                    "currency": "CAD",
                    "filter": {"securityIds": None},
                    "includeAccountData": True,
                    "includeSecurity": True,
                },
                "identity.financials.current.positions.edges",
                "array",
            )
        except Exception as exc:
            return self._render_from_cache(reason=f"WS API failed: {exc!s}")

        positions = self._normalize_positions(edges, accounts)
        self._write_cache(positions)
        return PositionsResult(positions=positions, stale_minutes=0, warnings=[])

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_positions(
        edges: list[dict], accounts: list[dict]
    ) -> list[Position]:
        accounts_by_id = {acct["id"]: acct for acct in accounts}
        positions: list[Position] = []
        for edge in edges:
            node = edge.get("node", edge)  # accept either edge-wrapped or flat
            security = node.get("security") or {}
            stock = security.get("stock") or {}
            symbol = stock.get("symbol") or security.get("id", "UNKNOWN")
            name = stock.get("name") or symbol
            security_type = security.get("securityType") or "EQUITY"
            listing_currency = security.get("currency") or "CAD"
            listing_exchange = stock.get("primaryExchange") or ""

            value = (node.get("totalValue") or {}).get("amount", "0")
            book = (node.get("marketBookValue") or {}).get("amount", "0")
            qty = node.get("quantity") or "0"

            account_ids = [a["id"] for a in (node.get("accounts") or [])]
            if not account_ids:
                continue  # cannot map to an account

            for account_id in account_ids:
                acct = accounts_by_id.get(account_id, {})
                positions.append(
                    Position(
                        account_id=account_id,
                        account_type=acct.get("unifiedAccountType", "UNKNOWN"),
                        account_nickname=acct.get("nickname", "") or "",
                        symbol=symbol,
                        name=name,
                        security_type=security_type,
                        listing_currency=listing_currency,
                        listing_exchange=listing_exchange,
                        quantity=Decimal(str(qty)),
                        market_value_cad=Decimal(str(value)),
                        book_value_cad=Decimal(str(book)),
                    )
                )
        return positions

    # ------------------------------------------------------------------
    # Disk cache (fallback only)
    # ------------------------------------------------------------------

    def _cache_path(self) -> Path:
        return self.cache_dir / CACHE_FILE_NAME

    def _write_cache(self, positions: list[Position]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "positions": [p.model_dump(mode="json") for p in positions],
        }
        self._cache_path().write_text(json.dumps(payload, indent=2, default=str))

    def _render_from_cache(self, reason: str) -> PositionsResult:
        path = self._cache_path()
        if not path.is_file():
            return PositionsResult(positions=[], stale_minutes=0, warnings=[reason])
        data = json.loads(path.read_text())
        positions = [Position.model_validate(p) for p in data["positions"]]
        fetched = datetime.fromisoformat(data["fetched_at"])
        stale_minutes = int(
            (datetime.now(timezone.utc) - fetched).total_seconds() // 60
        )
        return PositionsResult(
            positions=positions,
            stale_minutes=max(stale_minutes, 1),
            warnings=[reason, f"showing cached snapshot ({stale_minutes}m old)"],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_wealthsimple_service.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add networthlab/services/wealthsimple.py tests/test_wealthsimple_service.py
git commit -m "Add WealthsimpleService with session, fetch_positions, fallback cache"
```

---

## Task 9: ExposureService — account grouping integration

**Goal:** small façade method that loads the YAML + applies `match_account_group` to a list of WS accounts. Lets the aggregator (Task 10) consume a `dict[account_id, group_name]`.

**Files:**
- Create: `networthlab/services/exposure.py`
- Create: `tests/test_exposure_service_grouping.py`

**Steps:**

- [ ] **Step 1: Write failing tests**

Create `tests/test_exposure_service_grouping.py`:

```python
from pathlib import Path

from networthlab.models import Position
from networthlab.services.exposure import build_account_groups
from networthlab.services.exposure_config import AccountGroupRule


def _pos(account_id: str, account_type: str, nickname: str) -> Position:
    from decimal import Decimal
    return Position(
        account_id=account_id,
        account_type=account_type,
        account_nickname=nickname,
        symbol="X",
        name="x",
        security_type="EQUITY",
        listing_currency="CAD",
        listing_exchange="TSX",
        quantity=Decimal("1"),
        market_value_cad=Decimal("1"),
        book_value_cad=Decimal("1"),
    )


def test_groups_distinct_account_ids_once():
    positions = [
        _pos("a1", "RRSP", "My RRSP"),
        _pos("a1", "RRSP", "My RRSP"),  # duplicate from same account
        _pos("a2", "TFSA", "TFSA Vault"),
    ]
    rules = [
        AccountGroupRule(name="Special", nicknames=["*Vault*"], types=[], icon=""),
        AccountGroupRule(name="Retirement", nicknames=[], types=["RRSP"], icon=""),
        AccountGroupRule(name="Tax Free Saving", nicknames=[], types=["TFSA"], icon=""),
    ]
    result = build_account_groups(positions, rules)
    assert result == {"a1": "Retirement", "a2": "Special"}


def test_unmatched_falls_to_other():
    positions = [_pos("a1", "NON_REGISTERED", "")]
    result = build_account_groups(positions, [])
    assert result == {"a1": "Other"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_exposure_service_grouping.py -v`
Expected: tests fail with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `networthlab/services/exposure.py`:

```python
"""Pure aggregation logic — takes positions + classifications + grouping rules
and produces an ExposureSnapshot for the UI to render."""

from __future__ import annotations

from networthlab.models import Position
from networthlab.services.exposure_config import (
    AccountGroupRule,
    match_account_group,
)


def build_account_groups(
    positions: list[Position], rules: list[AccountGroupRule]
) -> dict[str, str]:
    """For each distinct account_id in positions, resolve its group name."""
    out: dict[str, str] = {}
    seen_account_ids: set[str] = set()
    for p in positions:
        if p.account_id in seen_account_ids:
            continue
        seen_account_ids.add(p.account_id)
        out[p.account_id] = match_account_group(
            nickname=p.account_nickname,
            account_type=p.account_type,
            rules=rules,
        )
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_exposure_service_grouping.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add networthlab/services/exposure.py tests/test_exposure_service_grouping.py
git commit -m "Add exposure aggregation module: build_account_groups"
```

---

## Task 10: ExposureService — full aggregation

**Goal:** generate the `ExposureSnapshot` from positions + classifications + account groups. Spec §5 contribution-row contract drives the shape.

**Files:**
- Modify: `networthlab/services/exposure.py`
- Create: `tests/test_exposure_service_aggregate.py`

**Steps:**

- [ ] **Step 1: Write failing tests**

Create `tests/test_exposure_service_aggregate.py`:

```python
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from networthlab.models import (
    ClassificationComponent,
    DimensionBreakdown,
    Position,
    SecurityClassification,
)
from networthlab.services.exposure import aggregate


def make_position(
    symbol: str, account_id: str, account_type: str, value: str
) -> Position:
    return Position(
        account_id=account_id,
        account_type=account_type,
        account_nickname=f"nick-{account_id}",
        symbol=symbol,
        name=f"name-{symbol}",
        security_type="ETF" if symbol.endswith(".TO") else "EQUITY",
        listing_currency="CAD" if symbol.endswith(".TO") else "USD",
        listing_exchange="TSX" if symbol.endswith(".TO") else "NASDAQ",
        quantity=Decimal("1"),
        market_value_cad=Decimal(value),
        book_value_cad=Decimal(value),
    )


def full_breakdown(buckets: dict[str, str], source="provider") -> DimensionBreakdown:
    return DimensionBreakdown(
        buckets={k: Decimal(v) for k, v in buckets.items()},
        source=source,
        as_of=None,
        notes=[],
    )


def make_classification(symbol: str, asset, sector, geo, currency) -> SecurityClassification:
    return SecurityClassification(
        symbol=symbol,
        asset_class=full_breakdown(asset),
        sector=full_breakdown(sector),
        geography=full_breakdown(geo),
        currency=full_breakdown(currency, source="heuristic"),
        complexity_flag=None,
        components=[ClassificationComponent(symbol=symbol, weight=Decimal("1"), source="provider")],
        fetched_at=datetime.now(timezone.utc),
    )


def test_aggregate_produces_six_dimensions():
    positions = [make_position("VEQT.TO", "a1", "RRSP", "1000")]
    classifications = {
        "VEQT.TO": make_classification(
            "VEQT.TO",
            asset={"equity": "1.0"},
            sector={"tech": "0.5", "financials": "0.5"},
            geo={"US": "0.6", "CAN": "0.4"},
            currency={"CAD": "1.0"},
        )
    }
    snap = aggregate(positions, classifications, account_groups={"a1": "Retirement"})
    dims = {row.dimension for row in snap.contributions}
    assert dims == {"asset_class", "geography", "sector", "concentration", "currency", "account"}


def test_aggregate_weights_sum_to_one_per_dimension():
    positions = [
        make_position("VEQT.TO", "a1", "RRSP", "1000"),
        make_position("AAPL", "a2", "TFSA", "500"),
    ]
    classifications = {
        "VEQT.TO": make_classification(
            "VEQT.TO",
            asset={"equity": "1.0"},
            sector={"tech": "1.0"},
            geo={"US": "1.0"},
            currency={"CAD": "1.0"},
        ),
        "AAPL": make_classification(
            "AAPL",
            asset={"equity": "1.0"},
            sector={"tech": "1.0"},
            geo={"US": "1.0"},
            currency={"USD": "1.0"},
        ),
    }
    snap = aggregate(
        positions,
        classifications,
        account_groups={"a1": "Retirement", "a2": "Tax Free Saving"},
    )
    for dim in ["asset_class", "geography", "sector", "currency", "account", "concentration"]:
        total = sum(r.weight for r in snap.contributions if r.dimension == dim)
        assert abs(total - Decimal("1")) < Decimal("0.0001"), f"{dim} total = {total}"


def test_aggregate_hhi_position_concentration():
    """HHI = Σ (weight × 100)² over each position. Equal weights => low HHI."""
    positions = [
        make_position("A", "x", "RRSP", "1000"),
        make_position("B", "x", "RRSP", "1000"),
        make_position("C", "x", "RRSP", "1000"),
        make_position("D", "x", "RRSP", "1000"),
    ]
    classifications = {
        sym: make_classification(
            sym,
            asset={"equity": "1.0"},
            sector={"tech": "1.0"},
            geo={"US": "1.0"},
            currency={"CAD": "1.0"},
        )
        for sym in ["A", "B", "C", "D"]
    }
    snap = aggregate(positions, classifications, account_groups={"x": "Retirement"})
    # Four equal positions: each 25%, HHI = 4 × 25² = 2500
    assert snap.kpis.hhi_positions == 2500
    assert snap.kpis.position_count == 4
    assert snap.kpis.total_value_cad == Decimal("4000")
    assert snap.kpis.top_holding_weight == Decimal("0.25")


def test_aggregate_unclassified_positions_attributed_to_unknown_bucket():
    positions = [make_position("MYSTERY", "a1", "RRSP", "100")]
    classifications = {
        "MYSTERY": SecurityClassification(
            symbol="MYSTERY",
            asset_class=DimensionBreakdown(buckets={}, source="unclassified", as_of=None, notes=[]),
            sector=DimensionBreakdown(buckets={}, source="unclassified", as_of=None, notes=[]),
            geography=DimensionBreakdown(buckets={}, source="unclassified", as_of=None, notes=[]),
            currency=DimensionBreakdown(buckets={"CAD": Decimal("1.0")}, source="heuristic", as_of=None, notes=[]),
            complexity_flag=None,
            components=[ClassificationComponent(symbol="MYSTERY", weight=Decimal("1"), source="unclassified")],
            fetched_at=datetime.now(timezone.utc),
        )
    }
    snap = aggregate(positions, classifications, account_groups={"a1": "Retirement"})
    asset_rows = [r for r in snap.contributions if r.dimension == "asset_class"]
    assert any(r.bucket == "Unclassified" for r in asset_rows)
    assert any(w in snap.warnings[0].lower() for w in ["unclassified"])


def test_aggregate_empty_portfolio_returns_zero_kpis():
    snap = aggregate(positions=[], classifications={}, account_groups={})
    assert snap.kpis.total_value_cad == Decimal("0")
    assert snap.kpis.position_count == 0
    assert snap.kpis.hhi_positions == 0
    assert snap.contributions == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_exposure_service_aggregate.py -v`
Expected: tests fail (`aggregate` not defined).

- [ ] **Step 3: Implement `aggregate`**

Append to `networthlab/services/exposure.py`:

```python
from datetime import datetime, timezone
from decimal import Decimal

from networthlab.models import (
    ContributionRow,
    DimensionBreakdown,
    ExposureSnapshot,
    Kpis,
    Position,
    SecurityClassification,
)


def _dimension_rows(
    dimension: str,
    breakdown: DimensionBreakdown,
    pos: Position,
    total_portfolio: Decimal,
) -> list[ContributionRow]:
    if not breakdown.buckets:
        # Unclassified — attribute the whole position to an Unclassified bucket.
        return [
            ContributionRow(
                dimension=dimension,
                bucket="Unclassified",
                source_position=pos.symbol,
                source_account_id=pos.account_id,
                underlying=None,
                value_cad=pos.market_value_cad,
                weight=(pos.market_value_cad / total_portfolio) if total_portfolio else Decimal("0"),
                source="unclassified",
            )
        ]
    rows: list[ContributionRow] = []
    for bucket, weight in breakdown.buckets.items():
        slice_value = pos.market_value_cad * weight
        rows.append(
            ContributionRow(
                dimension=dimension,
                bucket=bucket,
                source_position=pos.symbol,
                source_account_id=pos.account_id,
                underlying=None,
                value_cad=slice_value,
                weight=(slice_value / total_portfolio) if total_portfolio else Decimal("0"),
                source=breakdown.source,
            )
        )
    return rows


def _concentration_row(
    pos: Position, total: Decimal
) -> ContributionRow:
    return ContributionRow(
        dimension="concentration",
        bucket=pos.symbol,
        source_position=pos.symbol,
        source_account_id=pos.account_id,
        underlying=None,
        value_cad=pos.market_value_cad,
        weight=(pos.market_value_cad / total) if total else Decimal("0"),
        source="provider",  # concentration always has a known weight; provenance is the position itself
    )


def _account_row(pos: Position, group_name: str, total: Decimal) -> ContributionRow:
    return ContributionRow(
        dimension="account",
        bucket=group_name,
        source_position=pos.symbol,
        source_account_id=pos.account_id,
        underlying=None,
        value_cad=pos.market_value_cad,
        weight=(pos.market_value_cad / total) if total else Decimal("0"),
        source="provider",
    )


def aggregate(
    positions: list[Position],
    classifications: dict[str, SecurityClassification],
    account_groups: dict[str, str],
) -> ExposureSnapshot:
    """Build the full snapshot. Pure function — no IO."""
    total = sum((p.market_value_cad for p in positions), start=Decimal("0"))
    contributions: list[ContributionRow] = []
    unclassified_dims: set[str] = set()

    for pos in positions:
        cls = classifications.get(pos.symbol)
        if cls is None:
            # Treat as fully unclassified across all dimensions; currency from listing.
            unclassified_dims.update(["asset_class", "sector", "geography"])
            for dim in ("asset_class", "sector", "geography"):
                contributions.append(
                    ContributionRow(
                        dimension=dim,
                        bucket="Unclassified",
                        source_position=pos.symbol,
                        source_account_id=pos.account_id,
                        underlying=None,
                        value_cad=pos.market_value_cad,
                        weight=(pos.market_value_cad / total) if total else Decimal("0"),
                        source="unclassified",
                    )
                )
            contributions.append(
                ContributionRow(
                    dimension="currency",
                    bucket=pos.listing_currency,
                    source_position=pos.symbol,
                    source_account_id=pos.account_id,
                    underlying=None,
                    value_cad=pos.market_value_cad,
                    weight=(pos.market_value_cad / total) if total else Decimal("0"),
                    source="heuristic",
                )
            )
        else:
            for dim_name, breakdown in (
                ("asset_class", cls.asset_class),
                ("sector", cls.sector),
                ("geography", cls.geography),
                ("currency", cls.currency),
            ):
                if breakdown.source == "unclassified":
                    unclassified_dims.add(dim_name)
                contributions.extend(_dimension_rows(dim_name, breakdown, pos, total))
        contributions.append(_concentration_row(pos, total))
        contributions.append(
            _account_row(pos, account_groups.get(pos.account_id, "Other"), total)
        )

    # KPIs
    if positions:
        weights = [(p.market_value_cad / total) if total else Decimal("0") for p in positions]
        hhi = int(sum(((w * 100) ** 2) for w in weights))
        top_weight = max(weights)
    else:
        hhi = 0
        top_weight = Decimal("0")

    warnings: list[str] = []
    if unclassified_dims:
        warnings.append(
            f"Unclassified positions in dimensions: {', '.join(sorted(unclassified_dims))}"
        )

    return ExposureSnapshot(
        kpis=Kpis(
            total_value_cad=total,
            position_count=len(positions),
            hhi_positions=hhi,
            top_holding_weight=top_weight,
            as_of_snapshot=datetime.now(timezone.utc),
            cache_stale_minutes=0,
        ),
        contributions=contributions,
        warnings=warnings,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_exposure_service_aggregate.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add networthlab/services/exposure.py tests/test_exposure_service_aggregate.py
git commit -m "Add ExposureService.aggregate building contribution rows + KPIs"
```

---

## Task 11: ExposureState — Reflex state

**Goal:** wire services into a Reflex `State` subclass with async loader + refresh + derived `@rx.var`s for chart data.

**Files:**
- Create: `networthlab/state/exposure_state.py`
- Modify: `networthlab/state/__init__.py`

**Steps:**

This task is largely orchestration; manual smoke-tested in Task 15. No automated tests.

- [ ] **Step 1: Create the state class**

Create `networthlab/state/exposure_state.py`:

```python
"""Reflex state for the /exposure page."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import reflex as rx

from networthlab.services.etf_lookthrough import EtfLookthroughService
from networthlab.services.exposure import aggregate, build_account_groups
from networthlab.services.exposure_config import (
    load_account_groups,
    load_complex_securities,
    load_security_overrides,
)
from networthlab.services.wealthsimple import (
    PositionsResult,
    WealthsimpleAuthMissing,
    WealthsimpleService,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = REPO_ROOT / "config"
USER_CONFIG_DIR = Path.home() / ".networthlab"


class ExposureState(rx.State):
    is_loading: bool = False
    auth_required: bool = False
    error_message: str = ""
    warnings: list[str] = []

    # KPI fields surfaced individually so the UI binds simple scalars.
    total_value_cad: float = 0.0
    position_count: int = 0
    hhi_positions: int = 0
    top_holding_weight: float = 0.0
    cache_stale_minutes: int = 0
    last_updated: str = ""

    # Per-dimension chart data, list of {"name": str, "value": float}.
    asset_class_data: list[dict[str, Any]] = []
    geography_data: list[dict[str, Any]] = []
    sector_data: list[dict[str, Any]] = []
    currency_data: list[dict[str, Any]] = []
    account_data: list[dict[str, Any]] = []
    concentration_data: list[dict[str, Any]] = []  # top 10

    # Drilldown — the modal reads these to render the table.
    drilldown_open: bool = False
    drilldown_dimension: str = ""
    drilldown_bucket: str = ""
    drilldown_rows: list[dict[str, Any]] = []

    # Chip state
    has_leverage: bool = False
    has_unclassified: bool = False
    has_stale_overrides: bool = False
    has_review_complex: bool = False

    # Empty / config gating
    is_empty: bool = False
    needs_account_config: bool = False

    # Raw contributions (kept for drilldown filtering)
    _contributions: list[dict[str, Any]] = []

    async def on_load(self) -> None:
        """First page load — do not bust the yfinance cache."""
        await self._do_refresh(force_refresh=False)

    async def refresh(self) -> None:
        """Refresh button handler — bust cache for currently-held symbols (spec §11)."""
        await self._do_refresh(force_refresh=True)

    async def _do_refresh(self, force_refresh: bool) -> None:
        self.is_loading = True
        self.error_message = ""
        self.auth_required = False
        try:
            await self._refresh_impl(force_refresh=force_refresh)
        except WealthsimpleAuthMissing as exc:
            self.auth_required = True
            self.error_message = str(exc)
            self.is_empty = False
        except ValueError as exc:
            # Raised by config loaders on YAML parse errors with file path included.
            self.error_message = f"Config error: {exc}"
        except Exception as exc:  # noqa: BLE001
            self.error_message = f"Unexpected error: {exc!s}"
        finally:
            self.is_loading = False

    async def _refresh_impl(self, force_refresh: bool) -> None:
        ws_svc = WealthsimpleService(cache_dir=USER_CONFIG_DIR)
        result: PositionsResult = ws_svc.fetch_positions()

        bundle = load_security_overrides(
            CONFIG_DIR / "security_overrides.example.yaml",
            USER_CONFIG_DIR / "security_overrides.yaml",
        )
        complex_flags = load_complex_securities(CONFIG_DIR / "complex_securities.yaml")

        # Spec §10: missing ~/.networthlab/account_groups.yaml -> "all Other"
        # with a banner pointing to the example. Do NOT silently fall back to
        # the committed example — that would mask the user's lack of config.
        user_groups_path = USER_CONFIG_DIR / "account_groups.yaml"
        account_rules = load_account_groups(user_groups_path)
        self.needs_account_config = not account_rules
        if self.needs_account_config:
            result.warnings.append(
                f"No {user_groups_path} — all accounts shown as 'Other'. "
                f"Copy config/account_groups.example.yaml to {user_groups_path} and edit."
            )

        lookup = EtfLookthroughService(
            overrides=bundle,
            complex_flags=complex_flags,
            cache_dir=USER_CONFIG_DIR,
        )
        if force_refresh:
            # Evict cache entries for currently-held symbols only (spec §11).
            held_symbols = list({p.symbol for p in result.positions})
            lookup.clear_symbols(held_symbols)

        classifications = {
            p.symbol: lookup.classify(
                symbol=p.symbol,
                security_type=p.security_type,
                name=p.name,
                listing_exchange=p.listing_exchange,
                listing_currency=p.listing_currency,
            )
            for p in result.positions
        }

        account_groups = build_account_groups(result.positions, account_rules)
        snap = aggregate(result.positions, classifications, account_groups)

        # Populate scalars / chart data
        self.total_value_cad = float(snap.kpis.total_value_cad)
        self.position_count = snap.kpis.position_count
        self.hhi_positions = snap.kpis.hhi_positions
        self.top_holding_weight = float(snap.kpis.top_holding_weight)
        self.cache_stale_minutes = result.stale_minutes
        self.last_updated = snap.kpis.as_of_snapshot.strftime("%H:%M UTC")
        self.warnings = list(snap.warnings) + list(result.warnings)

        self.asset_class_data = _aggregate_for_chart(snap.contributions, "asset_class")
        self.geography_data = _aggregate_for_chart(snap.contributions, "geography")
        self.sector_data = _aggregate_for_chart(snap.contributions, "sector")
        self.currency_data = _aggregate_for_chart(snap.contributions, "currency")
        self.account_data = _aggregate_for_chart(snap.contributions, "account")
        self.concentration_data = _aggregate_for_chart(
            snap.contributions, "concentration", top_n=10
        )

        # Chips
        self.has_leverage = any(cls.complexity_flag for cls in classifications.values())
        self.has_unclassified = bool(
            [r for r in snap.contributions if r.source == "unclassified"]
        )
        self.has_stale_overrides = any(
            lookup.is_override_stale(cls.geography.as_of)
            or lookup.is_override_stale(cls.asset_class.as_of)
            or lookup.is_override_stale(cls.sector.as_of)
            for cls in classifications.values()
        )
        # Spec §9.5 yellow "Review complex" chip: stockPosition > 1.0 (which our
        # normalizer collapses into buckets["equity"] > 1.0) AND symbol not in
        # complex_securities.yaml. Flags unknown leveraged/derivative structures.
        self.has_review_complex = any(
            cls.asset_class.buckets.get("equity", Decimal("0")) > Decimal("1.0")
            and cls.symbol not in complex_flags
            for cls in classifications.values()
        )

        # Empty-state gate
        self.is_empty = len(result.positions) == 0

        # Cache contributions for drilldown — pre-format display strings so the
        # UI does not need raw rx.Var JS expressions.
        self._contributions = [
            {
                **r.model_dump(mode="json"),
                "value_cad_fmt": f"${float(r.value_cad):,.2f}",
                "weight_pct": f"{float(r.weight) * 100:.2f}%",
            }
            for r in snap.contributions
        ]

    # ----- Formatted display vars (consumed by KPI bar) -----

    @rx.var
    def formatted_total_value_cad(self) -> str:
        return f"${self.total_value_cad:,.0f} CAD"

    @rx.var
    def formatted_top_holding_pct(self) -> str:
        return f"{self.top_holding_weight * 100:.1f}%"

    @rx.var
    def concentration_label(self) -> str:
        return "concentrated" if self.hhi_positions > 2500 else "diversified"

    @rx.var
    def concentration_color(self) -> str:
        return "#f59e0b" if self.hhi_positions > 2500 else "#10b981"

    # ----- Drilldown -----

    def open_drilldown(self, dimension: str, bucket: str = "") -> None:
        self.drilldown_dimension = dimension
        self.drilldown_bucket = bucket
        self.drilldown_open = True
        if bucket:
            self.drilldown_rows = [
                r for r in self._contributions
                if r["dimension"] == dimension and r["bucket"] == bucket
            ]
        else:
            self.drilldown_rows = [
                r for r in self._contributions if r["dimension"] == dimension
            ]

    def close_drilldown(self) -> None:
        self.drilldown_open = False
        self.drilldown_rows = []


def _aggregate_for_chart(
    contributions: list, dimension: str, top_n: int | None = None
) -> list[dict[str, Any]]:
    """Sum value_cad by bucket and sort by value descending."""
    sums: dict[str, Decimal] = {}
    for row in contributions:
        if row.dimension != dimension:
            continue
        sums[row.bucket] = sums.get(row.bucket, Decimal("0")) + row.value_cad
    items = sorted(
        ({"name": k, "value": float(v)} for k, v in sums.items()),
        key=lambda item: item["value"],
        reverse=True,
    )
    if top_n is not None:
        items = items[:top_n]
    return items
```

- [ ] **Step 2: Update `state/__init__.py`**

Modify `networthlab/state/__init__.py` to re-export `ExposureState`. Read its current contents first; then add the import line and update `__all__`.

Add:

```python
from networthlab.state.exposure_state import ExposureState
```

…and add `"ExposureState"` to `__all__`.

- [ ] **Step 3: Smoke-import in a Python repl**

Run:

```bash
python -c "from networthlab.state import ExposureState; print(ExposureState.__name__)"
```

Expected: prints `ExposureState`.

- [ ] **Step 4: Commit**

```bash
git add networthlab/state/exposure_state.py networthlab/state/__init__.py
git commit -m "Add ExposureState wiring services into Reflex state"
```

---

## Task 12: Sidebar nav + route registration + chips

**Goal:** add the /exposure route, add a sidebar nav item, and ship the small "chip" presentational components used by tiles.

**Files:**
- Modify: `networthlab/components/layout/sidebar.py`
- Modify: `networthlab/networthlab.py`
- Create: `networthlab/components/exposure/__init__.py`
- Create: `networthlab/components/exposure/chips.py`
- Create: `networthlab/pages/exposure.py` (placeholder so the import in networthlab.py resolves)

**Steps:**

- [ ] **Step 1: Create the placeholder page**

Create `networthlab/pages/exposure.py`:

```python
"""Market exposure page — full composition arrives in Task 14."""

import reflex as rx


def exposure_page() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("Exposure", size="6"),
            rx.text("This page is under construction."),
            spacing="3",
        ),
        height="100vh",
    )
```

- [ ] **Step 2: Add nav item**

Modify `networthlab/components/layout/sidebar.py` — in the `nav_item(...)` block (the `vstack` listing nav items), insert a new entry after the Dashboard item:

```python
                nav_item(
                    "pie-chart",
                    "Exposure",
                    "/exposure",
                    is_active=AppState.current_page == "exposure",
                    collapsed=AppState.sidebar_collapsed,
                ),
```

- [ ] **Step 3: Wire the route**

Modify `networthlab/networthlab.py`:

Add import:

```python
from .pages.exposure import exposure_page
from .state.exposure_state import ExposureState
```

Add an `on_exposure_load` handler in `PageState`:

```python
    def on_exposure_load(self) -> None:
        self.current_page = "exposure"
```

Add the page registration block at the end:

```python
app.add_page(
    exposure_page,
    route="/exposure",
    title="Exposure | NetWorthLab",
    on_load=[PageState.on_exposure_load, ExposureState.on_load],
)
```

- [ ] **Step 4: Create the chips package**

Create `networthlab/components/exposure/__init__.py`:

```python
"""Exposure dashboard UI components."""
```

Create `networthlab/components/exposure/chips.py`:

```python
"""Status chips for exposure tiles: unclassified, leverage, stale, cache-stale."""

import reflex as rx

_BASE = {
    "padding": "2px 8px",
    "border_radius": "9999px",
    "font_size": "11px",
    "font_weight": "500",
    "letter_spacing": "0.02em",
}


def _chip(label: str, color: str, bg: str) -> rx.Component:
    return rx.box(
        rx.text(label, color=color),
        background=bg,
        **_BASE,
    )


def unclassified_chip() -> rx.Component:
    return _chip("Unclassified", color="#fbbf24", bg="rgba(245, 158, 11, 0.12)")


def leverage_chip() -> rx.Component:
    return _chip("Leverage", color="#f87171", bg="rgba(239, 68, 68, 0.12)")


def stale_override_chip() -> rx.Component:
    return _chip("Review override", color="#9ca3af", bg="rgba(255,255,255,0.06)")


def stale_cache_chip(minutes: int) -> rx.Component:
    return _chip(f"Stale by {minutes}m", color="#9ca3af", bg="rgba(255,255,255,0.06)")


def review_complex_chip() -> rx.Component:
    """Yellow chip: stockPosition > 1.0 but symbol not in complex_securities.yaml.

    Surfaces unknown leveraged/derivative ETFs the user should classify
    explicitly in `config/complex_securities.yaml`.
    """
    return _chip("Review complex", color="#fbbf24", bg="rgba(245, 158, 11, 0.12)")
```

- [ ] **Step 5: Run the dev server and verify the nav item appears**

Run:

```bash
reflex run
```

In the browser at the printed URL, confirm:
- "Exposure" nav item appears in the sidebar with a pie-chart icon
- Clicking it routes to `/exposure`
- The placeholder page renders "This page is under construction"
- No "Run lunchsimple login" error (the placeholder page doesn't call `ExposureState.on_load` yet — actually it does via the `on_load` handler — that's fine; if it errors, the page still mounts because `on_load` runs the state's async function)
- The other 5 pages still load

Stop with `Ctrl+C`.

- [ ] **Step 6: Commit**

```bash
git add networthlab/components/layout/sidebar.py networthlab/networthlab.py networthlab/pages/exposure.py networthlab/components/exposure/__init__.py networthlab/components/exposure/chips.py
git commit -m "Add /exposure route, sidebar nav item, and status chip components"
```

---

## Task 13: KPI bar + tile shell + chart components

**Goal:** the visual building blocks the page composes in Task 14.

**Files:**
- Create: `networthlab/components/exposure/kpi_bar.py`
- Create: `networthlab/components/exposure/exposure_tile.py`
- Create: `networthlab/components/exposure/charts/__init__.py`
- Create: `networthlab/components/exposure/charts/sector_bars.py`
- Create: `networthlab/components/exposure/charts/concentration_bars.py`

**Steps:**

- [ ] **Step 1: KPI bar**

Create `networthlab/components/exposure/kpi_bar.py`:

```python
"""Top-of-page KPI bar — 4 cards + refresh button."""

import reflex as rx

from ...state.exposure_state import ExposureState
from ...styles.theme import COLORS


def _kpi_card(label: str, value, subtitle: rx.Component | None = None) -> rx.Component:
    """`value` may be a Reflex Var or a plain string/int; Reflex renders either."""
    return rx.box(
        rx.text(label, font_size="11px", color=COLORS["text_secondary"], text_transform="uppercase"),
        rx.text(value, font_size="22px", font_weight="700", color=COLORS["text_primary"]),
        subtitle if subtitle is not None else rx.fragment(),
        padding="14px 18px",
        background=COLORS["bg_secondary"],
        border_left=f"3px solid {COLORS['accent_primary']}",
        border_radius="8px",
        flex="1",
        min_width="160px",
    )


def kpi_bar() -> rx.Component:
    return rx.flex(
        _kpi_card("Total Value", ExposureState.formatted_total_value_cad),
        _kpi_card("Holdings", ExposureState.position_count),
        _kpi_card(
            "Concentration (HHI)",
            ExposureState.hhi_positions,
            subtitle=rx.text(
                ExposureState.concentration_label,
                font_size="11px",
                color=ExposureState.concentration_color,
            ),
        ),
        _kpi_card("Top Holding", ExposureState.formatted_top_holding_pct),
        rx.box(
            rx.button(
                rx.icon("refresh-cw", size=16),
                "Refresh",
                on_click=ExposureState.refresh,
                loading=ExposureState.is_loading,
            ),
            margin_left="auto",
            align_self="center",
        ),
        gap="12px",
        wrap="wrap",
        width="100%",
        margin_bottom="20px",
    )
```

- [ ] **Step 2: Tile shell**

Create `networthlab/components/exposure/exposure_tile.py`:

```python
"""Reusable tile shell for each dimension."""

import reflex as rx

from ...styles.theme import COLORS


def exposure_tile(
    title: str,
    chart: rx.Component,
    chips: rx.Component | None = None,
    on_click=None,
) -> rx.Component:
    header = rx.flex(
        rx.text(
            title,
            font_size="13px",
            font_weight="600",
            color=COLORS["text_primary"],
            text_transform="uppercase",
            letter_spacing="0.04em",
        ),
        chips if chips is not None else rx.fragment(),
        justify="between",
        align="center",
        margin_bottom="10px",
        width="100%",
    )
    body = rx.box(
        chart,
        width="100%",
        flex_grow="1",
        display="flex",
        align_items="center",
        justify_content="center",
    )
    return rx.box(
        header,
        body,
        padding="16px",
        background=COLORS["bg_secondary"],
        border_radius="12px",
        border=f"1px solid {COLORS['glass_border']}",
        cursor="pointer" if on_click is not None else "default",
        on_click=on_click,
        height="100%",
        display="flex",
        flex_direction="column",
        _hover={"border_color": COLORS["accent_primary"]} if on_click else {},
    )
```

- [ ] **Step 3: Chart components**

Create `networthlab/components/exposure/charts/__init__.py` (empty):

```python
"""Chart helpers for the exposure dashboard."""
```

Create `networthlab/components/exposure/charts/sector_bars.py`:

```python
"""Horizontal bar chart for sector / account / currency breakdowns."""

import reflex as rx

from ....styles.theme import COLORS, CHART_COLORS


def sector_bars(data: rx.Var, height: int = 240) -> rx.Component:
    return rx.recharts.bar_chart(
        rx.recharts.bar(
            data_key="value",
            fill=CHART_COLORS[0],
            radius=[0, 4, 4, 0],
        ),
        rx.recharts.x_axis(type_="number", hide=True),
        rx.recharts.y_axis(
            data_key="name", type_="category", width=110,
            tick={"fill": COLORS["text_secondary"], "fontSize": 11},
        ),
        rx.recharts.graphing_tooltip(
            content_style={
                "backgroundColor": COLORS["bg_secondary"],
                "border": f"1px solid {COLORS['glass_border']}",
                "borderRadius": "8px",
                "color": COLORS["text_primary"],
            },
            formatter=rx.Var("(value) => ['$' + value.toLocaleString(), 'Value']"),
        ),
        data=data,
        layout="vertical",
        height=height,
        width="100%",
        margin={"top": 4, "right": 8, "left": 0, "bottom": 4},
    )
```

Create `networthlab/components/exposure/charts/concentration_bars.py`:

```python
"""Concentration bar chart — top N positions by weight."""

import reflex as rx

from ....styles.theme import COLORS, CHART_COLORS


def concentration_bars(data: rx.Var, height: int = 260) -> rx.Component:
    return rx.recharts.bar_chart(
        rx.recharts.bar(
            data_key="value",
            fill=CHART_COLORS[1],
            radius=[0, 4, 4, 0],
        ),
        rx.recharts.x_axis(type_="number", hide=True),
        rx.recharts.y_axis(
            data_key="name", type_="category", width=80,
            tick={"fill": COLORS["text_secondary"], "fontSize": 11},
        ),
        rx.recharts.graphing_tooltip(
            content_style={
                "backgroundColor": COLORS["bg_secondary"],
                "border": f"1px solid {COLORS['glass_border']}",
                "borderRadius": "8px",
                "color": COLORS["text_primary"],
            },
            formatter=rx.Var("(value) => ['$' + value.toLocaleString(), 'Value']"),
        ),
        data=data,
        layout="vertical",
        height=height,
        width="100%",
        margin={"top": 4, "right": 8, "left": 0, "bottom": 4},
    )
```

- [ ] **Step 4: Smoke-import**

Run:

```bash
python -c "from networthlab.components.exposure.kpi_bar import kpi_bar; from networthlab.components.exposure.exposure_tile import exposure_tile; from networthlab.components.exposure.charts.sector_bars import sector_bars; from networthlab.components.exposure.charts.concentration_bars import concentration_bars; print('OK')"
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add networthlab/components/exposure/
git commit -m "Add KPI bar, tile shell, and bar-chart components for exposure"
```

---

## Task 14: Drilldown modal + full page composition

**Goal:** ship the drill-down modal and assemble the 2×3 grid in `pages/exposure.py`.

**Files:**
- Create: `networthlab/components/exposure/drilldown_modal.py`
- Modify: `networthlab/pages/exposure.py`

**Steps:**

- [ ] **Step 1: Drilldown modal**

Create `networthlab/components/exposure/drilldown_modal.py`:

```python
"""In-page modal listing per-position contribution rows for a (dimension, bucket)."""

import reflex as rx

from ...state.exposure_state import ExposureState
from ...styles.theme import COLORS


def _header() -> rx.Component:
    return rx.flex(
        rx.text(
            rx.cond(
                ExposureState.drilldown_bucket != "",
                ExposureState.drilldown_dimension + " — " + ExposureState.drilldown_bucket,
                ExposureState.drilldown_dimension,
            ),
            font_size="18px",
            font_weight="600",
        ),
        rx.button("Close", on_click=ExposureState.close_drilldown, variant="ghost"),
        justify="between",
        align="center",
        width="100%",
        margin_bottom="12px",
    )


def _row(row: rx.Var) -> rx.Component:
    """Each row dict carries `value_cad_fmt` and `weight_pct` pre-formatted in state."""
    return rx.table.row(
        rx.table.cell(row["bucket"]),
        rx.table.cell(row["source_position"]),
        rx.table.cell(row["source_account_id"]),
        rx.table.cell(row["value_cad_fmt"], text_align="right"),
        rx.table.cell(row["weight_pct"], text_align="right"),
        rx.table.cell(row["source"]),
    )


def drilldown_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            _header(),
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Bucket"),
                            rx.table.column_header_cell("Position"),
                            rx.table.column_header_cell("Account"),
                            rx.table.column_header_cell("Value (CAD)"),
                            rx.table.column_header_cell("Weight"),
                            rx.table.column_header_cell("Source"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(ExposureState.drilldown_rows, _row),
                    ),
                ),
                max_height="60vh",
                overflow_y="auto",
            ),
            max_width="900px",
            background=COLORS["bg_primary"],
        ),
        open=ExposureState.drilldown_open,
        on_open_change=ExposureState.close_drilldown,
    )
```

- [ ] **Step 2: Full page composition**

Replace `networthlab/pages/exposure.py` entirely:

```python
"""Market exposure dashboard page — 2×3 grid + drill-down modal."""

import reflex as rx

from ..components.exposure.chips import (
    leverage_chip,
    review_complex_chip,
    stale_cache_chip,
    stale_override_chip,
    unclassified_chip,
)
from ..components.exposure.charts.concentration_bars import concentration_bars
from ..components.exposure.charts.sector_bars import sector_bars
from ..components.exposure.drilldown_modal import drilldown_modal
from ..components.exposure.exposure_tile import exposure_tile
from ..components.exposure.kpi_bar import kpi_bar
from ..components.layout.page_wrapper import page_wrapper
from ..components.charts.allocation_chart import allocation_donut_simple
from ..state.exposure_state import ExposureState
from ..styles.theme import COLORS


def _auth_banner() -> rx.Component:
    return rx.box(
        rx.text(
            "No Wealthsimple session found in keyring. Run ",
            rx.code("lunchsimple login"),
            " to connect.",
            color=COLORS["text_primary"],
        ),
        padding="14px 18px",
        background="rgba(239, 68, 68, 0.08)",
        border_left="3px solid #ef4444",
        border_radius="8px",
        margin_bottom="20px",
    )


def _empty_state() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.icon("inbox", size=32, color=COLORS["text_secondary"]),
            rx.text(
                "No positions found in your Wealthsimple accounts.",
                color=COLORS["text_secondary"],
                font_size="14px",
            ),
            spacing="2",
        ),
        padding="48px",
        background=COLORS["bg_secondary"],
        border_radius="12px",
    )


def _global_chips() -> rx.Component:
    return rx.hstack(
        rx.cond(ExposureState.has_unclassified, unclassified_chip(), rx.fragment()),
        rx.cond(ExposureState.has_leverage, leverage_chip(), rx.fragment()),
        rx.cond(ExposureState.has_review_complex, review_complex_chip(), rx.fragment()),
        rx.cond(ExposureState.has_stale_overrides, stale_override_chip(), rx.fragment()),
        rx.cond(
            ExposureState.cache_stale_minutes > 0,
            stale_cache_chip(ExposureState.cache_stale_minutes),
            rx.fragment(),
        ),
        spacing="2",
        margin_bottom="12px",
    )


def _grid() -> rx.Component:
    tile_args = [
        ("Asset Class", "asset_class",
         allocation_donut_simple(ExposureState.asset_class_data, height=220)),
        ("Geography", "geography",
         allocation_donut_simple(ExposureState.geography_data, height=220)),
        ("Sector", "sector",
         sector_bars(ExposureState.sector_data, height=240)),
        ("Position Concentration", "concentration",
         concentration_bars(ExposureState.concentration_data, height=260)),
        ("Currency", "currency",
         allocation_donut_simple(ExposureState.currency_data, height=220)),
        ("Account Groups", "account",
         sector_bars(ExposureState.account_data, height=240)),
    ]
    return rx.grid(
        *[
            exposure_tile(
                title=title,
                chart=chart,
                on_click=lambda dim=dim: ExposureState.open_drilldown(dim, ""),
            )
            for title, dim, chart in tile_args
        ],
        columns=rx.breakpoints(initial="1", sm="2", lg="3"),
        gap="14px",
        width="100%",
    )


def _warnings_banner() -> rx.Component:
    """Renders the list of non-fatal warnings (missing config, stale cache reasons, etc.)."""
    return rx.cond(
        ExposureState.warnings.length() > 0,
        rx.box(
            rx.vstack(
                rx.foreach(
                    ExposureState.warnings,
                    lambda w: rx.text(w, font_size="12px", color=COLORS["text_secondary"]),
                ),
                spacing="1",
                align="start",
            ),
            padding="10px 14px",
            background="rgba(245, 158, 11, 0.08)",
            border_left="3px solid #f59e0b",
            border_radius="6px",
            margin_bottom="12px",
        ),
        rx.fragment(),
    )


def _body() -> rx.Component:
    """Main body — only rendered when authenticated."""
    return rx.fragment(
        rx.cond(
            ExposureState.error_message != "",
            rx.box(
                rx.text(ExposureState.error_message, color="#f87171"),
                padding="10px",
                margin_bottom="12px",
            ),
            rx.fragment(),
        ),
        _warnings_banner(),
        rx.cond(
            ExposureState.is_empty,
            _empty_state(),
            rx.fragment(
                kpi_bar(),
                _global_chips(),
                _grid(),
                drilldown_modal(),
            ),
        ),
    )


def exposure_page() -> rx.Component:
    # page_wrapper signature: (title, subtitle, *children).
    return page_wrapper(
        "Exposure",
        "Portfolio diversification by market exposure",
        rx.cond(
            ExposureState.auth_required,
            _auth_banner(),   # Spec §10: auth required -> body hidden.
            _body(),
        ),
    )
```

- [ ] **Step 3: Smoke-import**

Run:

```bash
python -c "from networthlab.pages.exposure import exposure_page; print('OK')"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add networthlab/components/exposure/drilldown_modal.py networthlab/pages/exposure.py
git commit -m "Compose 2×3 exposure grid with drill-down modal"
```

---

## Task 15: End-to-end manual verification

**Goal:** run the dev server against real Wealthsimple data and verify every spec scenario manually.

This task has no committable artifact — it's a verification gate. Document any defects as new tasks.

**Pre-requisites:**

- `lunchsimple login` has been run on this machine so the keyring contains a valid Wealthsimple session.
- The user has at least one position in at least one Wealthsimple account.

**Steps:**

- [ ] **Step 1: Optional — seed `~/.networthlab/account_groups.yaml`**

If absent, the dashboard groups everything as "Other". Recommended to copy the template:

```bash
mkdir -p ~/.networthlab
cp config/account_groups.example.yaml ~/.networthlab/account_groups.yaml
```

Then edit `~/.networthlab/account_groups.yaml` to suit the user's actual accounts.

- [ ] **Step 2: Run the app**

```bash
reflex run
```

Open the printed URL, click "Exposure" in the sidebar.

- [ ] **Step 3: Verify the happy path**

Confirm:
- KPI bar shows non-zero Total Value, Holdings count, HHI, Top %
- All 6 tiles render with non-empty charts
- Sidebar nav highlights "Exposure" while on the page
- Clicking any tile opens the drilldown modal with a populated table
- Close button closes the modal

- [ ] **Step 4: Verify chips appear when expected**

If the portfolio contains:
- An ETF not in `security_overrides.example.yaml` and not classifiable by yfinance — the **Unclassified** chip appears.
- A symbol present in `complex_securities.yaml` (e.g., HYLD.TO) — the **Leverage** chip appears.
- Any override entry older than 180 days — the **Review override** chip appears.
- The WS API failed and the page is rendering from `~/.networthlab/positions_cache.json` — the **Stale by Xm** chip appears.

- [ ] **Step 5: Verify failure modes**

- Temporarily rename `~/.networthlab/` (e.g., `mv ~/.networthlab ~/.networthlab.bak`), restart, navigate to /exposure. Page should show the "Run `lunchsimple login` to connect" banner. Restore: `mv ~/.networthlab.bak ~/.networthlab`.
- Delete `~/.networthlab/positions_cache.json` and disable network briefly, then refresh — expect empty state + warnings explaining the failure.

- [ ] **Step 6: Verify cross-page navigation still works**

Click each sidebar nav item (Dashboard, FIRE, Loans, Projections, Settings) and confirm none are broken by the new dependencies.

- [ ] **Step 7: If everything works, no commit needed. If issues found, file them as follow-up commits.**

Once green, the feature is shipped.

---

## Appendix: useful commands

```bash
# Run all tests
pytest -v

# Run only this feature's tests
pytest tests/test_exposure_models.py tests/test_exposure_config.py tests/test_etf_lookthrough.py tests/test_wealthsimple_service.py tests/test_exposure_service_grouping.py tests/test_exposure_service_aggregate.py -v

# Lint (existing project rule)
ruff check networthlab/ tests/

# Run the app
reflex run

# Re-test ws_api session is still valid
python -c "from networthlab.services.wealthsimple import WealthsimpleService; s = WealthsimpleService.load_session(); print('session ok' if s else 'NO SESSION — run lunchsimple login')"

# Inspect yfinance cache
cat ~/.networthlab/yfinance_cache.json | python -m json.tool | head -40

# Clear yfinance cache (forces refetch on next refresh)
rm ~/.networthlab/yfinance_cache.json
```
