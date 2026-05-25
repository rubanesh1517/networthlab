"""Pre-push compile guard.

Run with `.venv/bin/python scripts/precompile_check.py`.

Why: `import` alone never catches recharts children-class validation or
any other lazy assertion that fires only when the page function is
actually called. This script calls each page once so the validators run.

Exits non-zero if any page fails to assemble.
"""

from __future__ import annotations

import os
import sys
import traceback


def main() -> int:
    os.environ.setdefault("TELEMETRY_ENABLED", "false")

    # Importing pages triggers Reflex's app.add_page registration.
    from networthlab.pages.dashboard import dashboard
    from networthlab.pages.exposure import exposure_page
    from networthlab.pages.fire import fire_calculator
    from networthlab.pages.loans import loan_tracker
    from networthlab.pages.projections import projections
    from networthlab.pages.settings import settings

    pages = [
        ("dashboard", dashboard),
        ("exposure", exposure_page),
        ("fire", fire_calculator),
        ("loans", loan_tracker),
        ("projections", projections),
        ("settings", settings),
    ]

    failed: list[str] = []
    for name, fn in pages:
        try:
            fn()  # CALL it — this is what reflex's _compile_page does.
            print(f"  ok   {name}")
        except Exception:
            failed.append(name)
            print(f"  FAIL {name}")
            traceback.print_exc()

    if failed:
        print(f"\nFAIL: {len(failed)} page(s) did not compile: {failed}")
        return 1
    print(f"\nOK: all {len(pages)} pages compile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
