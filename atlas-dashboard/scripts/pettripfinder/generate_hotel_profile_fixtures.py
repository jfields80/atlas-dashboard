"""PTF-PROD-001 -- local controlled-fixture runner for the production hotel
profile. Renders the five verification states to an isolated output root and
copies the production stylesheet. Does NOT regenerate the Columbus bundle and
never overwrites the approved static prototype.

    python scripts/pettripfinder/generate_hotel_profile_fixtures.py
        [--output data/site_builds/ptf_prod_hotel_fixtures]

No network. Reads production/candidate data; writes only under the output root.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.hotel_profile import build_fixture_vms, render_hotel_profile

CSS_SRC = Path(__file__).resolve().parent / "hotel_profile.css"
DEFAULT_OUT = "data/site_builds/ptf_prod_hotel_fixtures"


def run(output: str, diag: bool = False) -> int:
    out = REPO_ROOT / output
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CSS_SRC, out / "hotel_profile.css")
    vms = build_fixture_vms()
    for state, vm in vms.items():
        html = render_hotel_profile(vm, css_href="hotel_profile.css", diag=diag)
        (out / ("%s.html" % state)).write_text(html, encoding="utf-8", newline="\n")
        print("  %-11s -> %s.html  (%s)" % (state, state, vm.state))
    print("output:", out)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", default=DEFAULT_OUT)
    p.add_argument("--diag", action="store_true", help="inject overflow-diagnostic badge")
    args = p.parse_args(argv)
    return run(args.output, diag=args.diag)


if __name__ == "__main__":
    raise SystemExit(main())
