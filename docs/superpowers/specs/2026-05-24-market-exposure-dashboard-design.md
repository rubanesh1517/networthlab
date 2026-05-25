# Market Exposure Dashboard — Design Spec

**Status:** Draft for review
**Date:** 2026-05-24
**Project:** networthlab (Reflex web app)
**Goal:** A new `/exposure` page that shows, at a glance, how a Wealthsimple portfolio is diversified across six dimensions — using ETF look-through so the dashboard reflects actual underlying exposure rather than misleading listing-level data.

---

## 1. Background and motivation

`networthlab` currently uses Lunch Money as its data source and only knows account-level totals. Wealthsimple's GraphQL API (via `ws_api` 0.34.0) exposes per-security positions: quantity, market value, average price, book value, security metadata. This enables a real diversification view for the first time.

The naive approach — classify each security by its listing exchange — fails for ETFs. VEQT (TSX-listed) reads as "100% Canada" by exchange but actually holds ~45% US / ~30% Canada / ~18% Intl Dev / ~7% EM equities. The dashboard must look *through* ETFs to their actual exposure.

Out of scope for this spec:
- Historical exposure tracking (no daily snapshots in MVP)
- Target allocation / rebalance suggestions
- Non-Wealthsimple holdings (Lunch Money investment assets, manual entries)
- An in-app "classify this ETF" UI (we edit YAML by hand for MVP)
- Networthlab-owned login flow (lunchsimple owns Wealthsimple auth)

---

## 2. Architecture

Reflex page in the existing `networthlab` app, slotted into the sidebar between Dashboard and FIRE at route `/exposure`. Three new layers separated by responsibility so each is testable in isolation:

```
ws_api  ─────────────────►  WealthsimpleService
                              │  (auth from keyring,
                              │   fetch positions normalized to CAD,
                              │   disk-cache positions snapshot)
                              ▼
                            raw positions
                              │
                              ▼
yfinance + YAML  ─────────►  EtfLookthroughService
                              │  (classify each unique security,
                              │   24h yfinance cache,
                              │   override > pattern > exchange > unknown)
                              ▼
                       SecurityClassification per symbol
                              │
                              ▼
                            ExposureService
                              │  (pure aggregation:
                              │   positions × classifications × account_groups
                              │   → contribution rows + 6 breakdowns + KPIs)
                              ▼
                            ExposureState (Reflex)
                              │
                              ▼
                            pages/exposure.py (UI)
```

**Boundary contracts** between layers:

| Layer | Input | Output | Pure? |
|---|---|---|---|
| `WealthsimpleService` | keyring session | `list[Position]` (normalized CAD) | No (IO) |
| `EtfLookthroughService` | `symbol`, YAML configs | `SecurityClassification` | No (yfinance + cache) |
| `ExposureService` | positions, classifications, account groups | contribution rows + breakdowns + KPIs | Yes |
| `ExposureState` | services above | reactive state for UI | No (orchestration) |
| `pages/exposure.py` | state | rendered components | Yes (declarative) |

The pure-aggregation boundary at `ExposureService` is the primary unit-test surface.

---

## 3. New files

```
networthlab/
  config/
    account_groups.example.yaml      # template, committed
    security_overrides.yaml          # generic market metadata, committed
    complex_securities.yaml          # generic market metadata, committed
  docs/
    superpowers/specs/
      2026-05-24-market-exposure-dashboard-design.md   # this file
  networthlab/
    pages/
      exposure.py                    # 2×3 grid composition
    state/
      exposure_state.py              # async load, refresh, derived @rx.vars
    services/
      wealthsimple.py                # ws_api session bootstrap + fetch_positions
      etf_lookthrough.py             # yfinance + YAML classification + cache
      exposure.py                    # pure aggregation (positions → breakdowns)
    models/
      exposure.py                    # dataclasses (Position, SecurityClassification, ContributionRow, etc.)
    components/
      exposure/
        kpi_bar.py
        exposure_tile.py             # reusable tile shell (title, chart slot, chips)
        drilldown_modal.py           # one modal serving all 6 dimensions
        chips.py                     # stale, leverage, unclassified chips
      charts/
        sector_bars.py
        concentration_bars.py
  tests/
    fixtures/
      positions_sample.json          # sanitized real get_identity_positions response
      yfinance_veqt.json             # sanitized yfinance fixture
    test_exposure_service.py
    test_etf_lookthrough.py
    test_account_grouping.py
```

Updates to existing files:
- `networthlab/networthlab.py` — register `/exposure` route and `on_load` handler
- `networthlab/components/layout/sidebar.py` — add nav item ("pie-chart" icon)
- `requirements.txt` — add `ws-api>=0.34.0`, `yfinance>=0.2.40`, `PyYAML>=6.0`

---

## 4. Configuration files

### 4.1 `~/.networthlab/account_groups.yaml` (user-specific, NOT committed)

Loaded from `~/.networthlab/` (matches existing `services/storage.py` pattern). Rules evaluated top-to-bottom; first match wins. Nickname rules placed before type rules so they override.

```yaml
groups:
  - name: "52 Narbonne"
    match: { nicknames: ["SM Non Reg", "*Narbonne*"] }
    icon: "home"
  - name: Retirement
    match: { types: [RRSP, LIRA, RRIF] }
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

Unmatched accounts fall into "Other" with a yellow chip prompting the user to add a rule. Pattern syntax for nicknames is glob (`*Narbonne*`).

A committed `config/account_groups.example.yaml` documents the structure with placeholder values only.

### 4.2 `config/security_overrides.yaml` (committed, generic)

Direct per-symbol classification override. Pre-populated for the user's current holdings; extensible.

```yaml
VEQT.TO:
  asset_class:  { equity: 1.0 }
  sector:       provider              # use yfinance
  geography:    { US: 0.448, CAN: 0.306, INTL_DEV: 0.177, EM: 0.072 }
  as_of: "2026-05-24"

XEQT.TO:
  asset_class:  { equity: 1.0 }
  sector:       provider
  geography:    { US: 0.442, CAN: 0.258, INTL_DEV: 0.246, EM: 0.054 }
  as_of: "2026-05-24"

VFV.TO:
  asset_class:  { equity: 1.0 }
  sector:       provider
  geography:    { US: 1.0 }
  as_of: "2026-05-24"

QQQM:
  asset_class:  { equity: 1.0 }
  sector:       provider
  geography:    { US: 1.0 }
  as_of: "2026-05-24"

HYLD.TO:
  asset_class:  { equity: 1.0 }    # leverage flagged separately
  sector:       provider
  geography:    { US: 1.0 }
  as_of: "2026-05-24"
```

The literal `provider` value means "use yfinance for this dimension." Allows mixing override + provider data per dimension within a single symbol.

**Staleness:** When `as_of` is older than `stale_after_days` (default **180**, configurable via top-level YAML key `stale_after_days:`), the UI shows a gray "review override" chip on tiles containing that security.

### 4.3 `config/complex_securities.yaml` (committed, generic)

Explicit metadata for leveraged, inverse, and derivative-based products. The `stockPosition > 1.0` heuristic remains as a secondary trigger that surfaces a yellow "review this" chip on unknown complex securities not listed here.

```yaml
HYLD.TO: { flag: covered_call_leverage, leverage: 1.25 }
HQU.TO:  { flag: leveraged_2x_long,      leverage: 2.0 }
HSD.TO:  { flag: leveraged_inverse,      leverage: -2.0 }
```

UI shows a red chip on any tile containing a position whose symbol matches this file.

---

## 5. Data models

All in `networthlab/models/exposure.py`.

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Literal

Dimension = Literal["asset_class","geography","sector","concentration","currency","account"]
ClassificationSource = Literal["override","provider","heuristic","recursive","unclassified"]

@dataclass(frozen=True)
class Position:
    account_id: str
    account_type: str           # WS unifiedAccountType
    account_nickname: str
    symbol: str                 # "VEQT.TO"
    name: str                   # "Vanguard All-Equity ETF Portfolio"
    security_type: str          # "ETF", "EQUITY", "CRYPTO", etc.
    listing_currency: str       # "CAD" / "USD"
    listing_exchange: str       # "TSX" / "NASDAQ"
    quantity: Decimal
    market_value_cad: Decimal
    book_value_cad: Decimal

@dataclass(frozen=True)
class ClassificationComponent:
    """One underlying contribution to a classification. For MVP, source-types
    other than 'recursive' produce a single self-referential component.
    Phase 2 recursive look-through emits one component per sub-fund."""
    symbol: str
    weight: Decimal             # fraction of parent position
    source: ClassificationSource

@dataclass(frozen=True)
class DimensionBreakdown:
    buckets: dict[str, Decimal]   # bucket name → weight (sums to 1.0)
    source: ClassificationSource  # how this dimension was classified
    as_of: date | None            # for source=override; None otherwise

@dataclass(frozen=True)
class SecurityClassification:
    symbol: str
    asset_class: DimensionBreakdown
    geography:   DimensionBreakdown
    sector:      DimensionBreakdown
    currency:    DimensionBreakdown
    complexity_flag: str | None       # "covered_call_leverage", etc.
    components: list[ClassificationComponent]   # phase 2 will populate beyond [self]
    fetched_at: date

@dataclass(frozen=True)
class ContributionRow:
    dimension: Dimension
    bucket: str                 # "Technology", "US", "Retirement", "VEQT.TO" (for concentration)
    source_position: str        # "VEQT.TO"
    source_account_id: str
    underlying: str | None      # phase 2: "AAPL" for recursive rows; None in MVP
    value_cad: Decimal
    weight: Decimal             # fraction of total portfolio (0.0–1.0)
    source: ClassificationSource

@dataclass(frozen=True)
class Kpis:
    total_value_cad: Decimal
    position_count: int
    hhi: int                    # 0–10,000, single-name concentration
    top_holding_weight: Decimal # 0.0–1.0
    as_of_snapshot: date
    cache_stale_minutes: int    # for "stale by Xm" badge

@dataclass(frozen=True)
class ExposureSnapshot:
    kpis: Kpis
    contributions: list[ContributionRow]
    warnings: list[str]         # surfaced as a banner
```

**Why this shape:**
- `ContributionRow` is the canonical flat output. Tiles group by `(dimension, bucket)` and sum `value_cad`. Drill-down modal filters by `(dimension, bucket)` and lists rows.
- `source` provenance is on every row, enabling the UI to show high-confidence (override/provider) vs lower-confidence (heuristic) data distinctly.
- `components` field on `SecurityClassification` is unused in MVP (always `[ClassificationComponent(symbol=self, weight=1.0, source=...)]`) but reserved so phase 2 recursive look-through can attach `[VUN.TO@0.445, VCN.TO@0.306, ...]` without changing downstream contracts.

---

## 6. ETF look-through algorithm

Each dimension is classified independently. The fallback chain differs per dimension because not every step is meaningful for every dimension.

| Dimension | Fallback chain |
|---|---|
| `asset_class` | override → provider (`funds_data.asset_classes`) → unclassified |
| `sector` | override → provider (`funds_data.sector_weightings`) → unclassified |
| `geography` | override → name-pattern → stock-exchange aggregation → unclassified |
| `currency` | derived directly from `Position.listing_currency` — does not use this algorithm |

**Step definitions:**

```
1. Direct override (config/security_overrides.yaml)
   • Per-dimension. A literal `provider` value in the YAML falls through
     to step 2 for that dimension only; other dimensions still use override.
   • Carries `as_of` date → staleness chip (180-day default).

2. Provider data (yfinance.Ticker(symbol).funds_data)
   • Applies to: asset_class, sector.
   • Normalized via EtfLookthroughService; missing fields marked
     unavailable rather than crashing.

3. Name-pattern fallback (geography only; case-insensitive substring
   match against the security's full name field, e.g., "Vanguard
   S&P 500 Index ETF" — NOT the ticker symbol)
   • "S&P 500", "Total US", "NASDAQ"     → US
   • "FTSE Canada", "TSX 60"             → CAN
   • "EAFE", "Intl Developed"            → INTL_DEV
   • "Emerging Markets"                  → EM
   • "World", "Global"                   → no match, falls through

4. Stock-exchange aggregation (geography only)
   • Applies only when top_holdings are predominantly individual stocks
     (heuristic: ≥80% of top_holdings have yfinance `quoteType` of
     EQUITY, not ETF/MUTUALFUND).
   • Weight each holding by listing exchange → country (NASDAQ→US,
     NYSE→US, TSX→CAN, LSE→INTL_DEV, etc.).
   • Example: QQQM top_holdings are all NASDAQ → 100% US.

5. Unclassified
   • Position contributes to the "Unclassified" bucket on the affected
     dimension's tile.
   • Yellow warning chip on that tile.
```

**Performance guardrails:**
- One yfinance call per *unique ETF symbol*, cached to `~/.networthlab/yfinance_cache.json` with 24h TTL keyed by `(symbol, fetched_date)`.
- For individual stocks within ETFs: exchange-based heuristic, **no yfinance call**.
- No recursive look-through in MVP (deferred — see §15).
- Cold-start budget: <5s for a 30-position portfolio. Subsequent loads <500ms.

**yfinance normalization:** `EtfLookthroughService` never returns raw yfinance objects. It returns `SecurityClassification` with `partial=True`/`unavailable=True` markers per dimension when yfinance data is missing or malformed.

---

## 7. Account grouping algorithm

`ExposureService.group_account(account, rules)`:

1. Load `~/.networthlab/account_groups.yaml`. If missing, fall back to "Other" for all accounts and surface a banner pointing to `config/account_groups.example.yaml`.
2. For each WS account:
   - Evaluate `groups` top-to-bottom.
   - A rule matches if **any** nickname pattern matches `accountNickname` (glob) OR **any** type matches `unifiedAccountType`.
   - First matching rule wins.
3. Unmatched → "Other" with yellow chip.

Nickname matching uses Python's `fnmatch.fnmatchcase` for glob support, case-sensitive (WS nicknames are user-supplied and case-meaningful).

---

## 8. Data flow

```
User navigates to /exposure
  ↓
ExposureState.on_load (async)
  ↓
WealthsimpleService.load_session()           ← keyring (service=lunchsimple, key=session)
  ├─ session missing/expired → set state.auth_required = True, return early
  ↓
WealthsimpleService.fetch_positions(currency="CAD")
  ├─ calls ws_api: get_accounts() + get_identity_positions(security_ids=None, currency="CAD")
  ├─ writes ~/.networthlab/positions_cache.json on success
  ├─ on ws_api failure: load cache, set state.stale_minutes from file mtime
  ↓
EtfLookthroughService.classify_all(unique_symbols)
  ├─ for each symbol:
  │    – check override YAML
  │    – check yfinance cache (24h TTL)
  │    – fall back to yfinance fetch + cache write
  │    – apply algorithm steps 3–5 as needed
  ↓
ExposureService.aggregate(positions, classifications, account_groups)
  ├─ produces ExposureSnapshot (KPIs, contribution rows, warnings)
  ↓
ExposureState stores snapshot + sets is_loading=False
  ↓
UI re-renders 2×3 grid from derived @rx.vars
```

**Refresh button** re-runs the entire flow. Force-busts the yfinance cache only for symbols currently held (not the entire cache).

---

## 9. UI

### 9.1 Page layout (2×3 grid — option C)

```
┌────────────────────────────────────────────────────────────────┐
│  [Total $285,400 CAD]  [24 Holdings]  [HHI 1,420]  [Top 21%]   │  ← KPI bar
│                                            [⟳ Refresh] [last 2m]│
├────────────────────────────────────────────────────────────────┤
│  Asset Class         │  Geography         │  Sector            │
│  ◐ Equity 97%        │  ◐ US 58%          │  Tech    ▓▓▓▓ 32%  │
│  ◐ Bond 0%           │  ◐ CAN 24%         │  Fin     ▓▓ 18%    │
│  ◐ Cash 3%           │  ◐ Intl 13%        │  …                 │
├────────────────────────────────────────────────────────────────┤
│  Concentration       │  Currency          │  Account Groups    │
│  VEQT  ▓▓▓▓▓ 21%     │  ◐ CAD 60%         │  Retirement   39%  │
│  VFV   ▓▓▓ 16%       │  ◐ USD 40%         │  Tax Free     27%  │
│  HHI: 1,420          │                    │  …                 │
└────────────────────────────────────────────────────────────────┘
```

### 9.2 Responsive breakpoints

- **Desktop (≥1024px):** 3 cols × 2 rows; KPI bar 4 cols
- **Tablet (640–1024px):** 2 cols × 3 rows; KPI bar 2 cols × 2 rows
- **Mobile (<640px):** 1 col stacked; KPI bar 1 col stacked

### 9.3 Tile component

Each tile is `components/exposure/exposure_tile.py`. Common shell:
- Title + dimension icon
- Chips row (warning/leverage/stale, conditional)
- Chart slot (donut for asset_class/geography/currency; horizontal bars for sector/concentration/account)
- Click handler → opens drill-down modal for that dimension

### 9.4 Drill-down modal

Single reusable in-page modal (Reflex `rx.dialog`, `components/exposure/drilldown_modal.py`) serves all 6 dimensions; no route change. Opens on tile click with the dimension preset. Sortable table of `ContributionRow` filtered by `(dimension, bucket)` — columns: Bucket, Position, Account, Value (CAD), Weight (%), Source. Concentration tile drills into the top **10** holdings by default with a "show all" expander.

### 9.5 Chips

| Chip | Color | Trigger |
|---|---|---|
| Unclassified | yellow | Any position contributes to "Unclassified" bucket on this dimension |
| Leverage | red | Any position has `complexity_flag` set |
| Review complex | yellow | `stockPosition > 1.0` from yfinance but not in `complex_securities.yaml` |
| Review override | gray | Any contributing override's `as_of` > 180 days old |
| Stale data | gray | `cache_stale_minutes` > 60 |

---

## 10. Error handling

| Condition | Behavior |
|---|---|
| Keyring session missing/expired | Banner: "Run `lunchsimple login` to connect." Page body hidden. |
| `ws_api` network failure | Toast error + render `positions_cache.json` snapshot if any; "stale by Xm" badge on KPI bar. |
| `yfinance` failure for one symbol | That symbol marked unclassified on affected dimensions; other tiles render normally; yellow chip on affected tiles. |
| All `yfinance` calls fail | Fall back to exchange-based heuristics only; warning banner. |
| Empty portfolio | Empty state: "No positions found in your Wealthsimple accounts." |
| YAML parse error | Banner with file path + parser exception message; page falls back to no-config defaults. |
| Missing `account_groups.yaml` | Banner linking to `config/account_groups.example.yaml`; all accounts grouped as "Other". |

No automatic retries in MVP — the manual refresh button is the recovery mechanism.

---

## 11. Caching strategy

| Cache | Location | TTL | Invalidation |
|---|---|---|---|
| Wealthsimple positions | `~/.networthlab/positions_cache.json` | none (always written on success) | Used only when live fetch fails |
| yfinance per-symbol | `~/.networthlab/yfinance_cache.json` | 24h per symbol | Refresh button clears entries for currently-held symbols. Newly-held symbols (never cached) are fetched fresh on next load. |
| Reflex state | in-memory (session) | session | Refresh button re-runs the full flow |

`positions_cache.json` schema: `{"fetched_at": ISO8601, "positions": [...Position...]}`. File mtime drives the "stale by Xm" badge when used as fallback.

`yfinance_cache.json` schema: `{"<symbol>": {"fetched_at": ISO8601, "data": <normalized SecurityClassification fields>}}`.

---

## 12. Auth and session

Wealthsimple authentication is owned by `lunchsimple`. The CLI's `login` command writes the session to keyring under `service=lunchsimple, key=session`. The new `WealthsimpleService` reads from the same entry.

```python
# networthlab/services/wealthsimple.py
import keyring
from ws_api import WSAPISession, WealthsimpleAPI

def load_session() -> WSAPISession | None:
    raw = keyring.get_password("lunchsimple", "session")
    return WSAPISession.from_json(raw) if raw else None

def persist_session(session_json: str) -> None:
    # ws_api may refresh the access token; persist back to the same entry
    keyring.set_password("lunchsimple", "session", session_json)
```

networthlab does **not** implement a login flow in MVP. Auth-required banner directs the user to `lunchsimple login`.

---

## 13. Testing strategy

Unit tests for the pure-aggregation surface and for the look-through algorithm.

### 13.1 Test files

- `tests/test_exposure_service.py`
- `tests/test_etf_lookthrough.py`
- `tests/test_account_grouping.py`

### 13.2 Coverage

- **`ExposureService`** (pure, highest coverage):
  - Fixture positions → expected contribution rows
  - Donut totals sum to exactly 1.0 (rounding test using Decimal)
  - Unclassified positions don't break aggregation
  - Empty portfolio → empty snapshot, no exceptions
  - HHI calculation correctness
- **`EtfLookthroughService`** (mock yfinance + YAML):
  - Direct override precedence over provider data
  - Missing yfinance fields → partial classification with proper source marker
  - Name-pattern fallback hits ("S&P 500" → US)
  - Stock-exchange aggregation when top_holdings are stocks
  - 24h cache TTL behavior (within → hit, beyond → refetch)
  - Stale-override detection (`as_of` > 180 days)
- **Account grouping**:
  - Rule order (nickname before type)
  - Glob nickname matches (`*Narbonne*` matches "Narbonne SM", "My Narbonne")
  - Type fallback when no nickname matches
  - Unmatched → "Other" + warning surfaced
  - Missing config file → "Other" for all accounts + banner warning
- **Failure modes**:
  - YAML parse error surfaces exact file path + parser message
  - Stale `positions_cache.json` rendering with timestamp badge
  - Empty `yfinance_cache.json` doesn't crash on first run

### 13.3 Fixtures

- `tests/fixtures/positions_sample.json` — one sanitized real `get_identity_positions` response covering the user's 5 ETFs + 2-3 individual stocks + at least one CRYPTO position
- `tests/fixtures/yfinance_veqt.json`, `yfinance_qqqm.json` — captured `funds_data` responses for the unit tests

No UI tests (Reflex + recharts is declarative; manual visual check during dev).

---

## 14. Dependencies

Added to `networthlab/requirements.txt`:

```
ws-api>=0.34.0
yfinance>=0.2.40
PyYAML>=6.0
```

`keyring` is transitively present (already used by `lunchsimple`); add explicitly if `networthlab` has not pulled it in.

---

## 15. Phase 2 extension points

Designed for, not built in MVP:

- **Recursive look-through**: `SecurityClassification.components` already supports it. Implementation: when `source=provider` and `top_holdings` are predominantly ETFs (≥80%), recurse classification on each at depth ≤ 2, weight-sum into parent. Cycle detection via visited-symbol set per call.
- **Time series / drift over time**: snapshot `ExposureSnapshot` daily to `~/.networthlab/exposure_history/YYYY-MM-DD.json`. New chart: dimension-over-time stacked area.
- **Target allocation**: per-user `~/.networthlab/targets.yaml`. New tile: drift table + rebalance suggestions.
- **Non-WS holdings**: merge Lunch Money investment assets as opaque positions with user-specified classifications.
- **In-app override UI**: edit `security_overrides.yaml` from a modal rather than a text editor.

---

## 16. Open questions for review

None. All decisions captured above. Three implementation-time confirmations:

1. **WS Crypto accounts** come through `get_accounts()` with `unifiedAccountType: CRYPTO`. To be verified against a real fetch — if WS exposes them via a separate endpoint, `WealthsimpleService.fetch_positions` may need a second call merged in.
2. **HYLD.TO leverage value (1.25)** is a placeholder based on yfinance `stockPosition: 1.244`. To be confirmed from Hamilton's fact sheet at implementation time.
3. **`stale_after_days` default of 180** is a judgment call. Configurable from day one so it can be tightened without code change.
