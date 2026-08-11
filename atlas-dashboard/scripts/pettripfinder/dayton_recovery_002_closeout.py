"""PTF-DAYTON-RECOVERY-WORKER-002 -- closeout categorization of everything
left unresolved after this worker's pass, one next action each.

Reads nothing but the committed census and this module's own hand-built
tables (built from the capture attempts actually made this run). Writes
the closeout report into the gitignored run directory; the summary is
reproduced in the worker's final report to the operator.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

CENSUS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
               / "dayton-oh.json")
OUT_PATH = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
            / "dayton-recovery-002" / "remaining_unresolved_report.json")

ADVANCED_WITH_EVIDENCE = {
    "cobblestone-hotel-suites-eaton", "cobblestone-hotel-suites-urbana",
    "the-hotel-at-dayton-south", "hearthstone-inn-cedarville",
    "extended-stay-america-suites-dayton-fairborn",
    "extended-stay-america-suites-dayton-south",
    "extended-stay-america-suites-dayton---north",
    "baymont-by-wyndham-dayton-north", "wingate-by-wyndham-dayton-north",
    "scioto-inn-urbana", "hotel-versailles",
}

ACCESS_BLOCKED = {
    "hilton-garden-inn-dayton-downtown": "hilton.com 403 Forbidden (directly attempted)",
    "homewood-suites-by-hilton-dayton-fairborn-wright-patterson": "hilton.com 403 (brand pattern)",
    "hotel-ardent-dayton-downtown-tapestry-collection-by-hilton": "hilton.com 403 (brand pattern)",
    "home2-suites-by-hilton-dayton-centerville": "hilton.com 403 (brand pattern); no official_url on record either",
    "best-western-plus-dayton-northwest": "bestwestern.com 403 Forbidden (directly attempted)",
    "best-western-plus-miamisburg-dayton": "bestwestern.com 403 (brand pattern)",
    "best-western-wapakoneta-inn": "bestwestern.com 403 (brand pattern)",
    "best-western-celina": "bestwestern.com 403 (brand pattern)",
    "red-roof-inn-dayton-moraine-u-of-dayton": "redroof.com 403 Forbidden (directly attempted)",
    "country-inn-and-suites-by-radisson-beavercreek-dayton": "radissonhotels.com 403 Forbidden (directly attempted)",
    "country-inn-suites-by-radisson-springfield": "radissonhotels.com 403 (brand pattern)",
    "comfort-inn-suites-dayton-north": "choicehotels.com read-timeout, no response (directly attempted)",
    "quality-inn-dayton-north-vandalia": "choicehotels.com timeout (brand pattern)",
    "quality-inn-dayton-airport": "choicehotels.com timeout (brand pattern)",
    "comfort-inn-suites-dayton-northwest-englewood": "choicehotels.com timeout (brand pattern)",
    "comfort-suites-dayton-wright-patterson": "choicehotels.com timeout (brand pattern)",
    "comfort-suites-miamisburg---dayton-south": "choicehotels.com timeout (brand pattern)",
    "quality-inn-st-marys": "choicehotels.com timeout (brand pattern)",
    "comfort-inn-bellefontaine": "choicehotels.com timeout (brand pattern)",
    "fairfield-inn-suites-springfield": "marriott.com 403 Forbidden (directly attempted)",
    "fairfield-inn-dayton-new-paris": "marriott.com 403 (brand pattern)",
    "springhill-suites-by-marriott-dayton-south-miamisburg": "marriott.com 403 (brand pattern)",
    "holiday-inn-express-suites-dayton-sw-university-area": "ihg.com 403 (brand pattern)",
    "holiday-inn-express-suites-dayton-north-vandalia": "ihg.com 403 (brand pattern)",
    "staybridge-suites-dayton-north": "ihg.com 403 (brand pattern)",
    "staybridge-suites-fairborn-dayton-east": "ihg.com 403 (brand pattern); DAY-C001 address collision also unresolved",
    "holiday-inn-express-suites-dayton-south-i-675": "ihg.com 403 (brand pattern)",
    "holiday-inn-express-and-suites-dayton-east---beavercreek": "ihg.com 403 (brand pattern)",
    "holiday-inn-express-and-suites-dayton-huber-heights": "ihg.com 403 (brand pattern)",
    "holiday-inn-express-and-suites-dayton-north---tipp-city": "ihg.com 403 (brand pattern)",
    "holiday-inn-express-suites-wapakoneta": "ihg.com 403 (brand pattern)",
    "holiday-inn-express-suites-washington-court-house": "ihg.com 403 (brand pattern)",
    "holiday-inn-express-suites-sidney": "ihg.com 403 (brand pattern)",
    # the two remaining HELD properties
    "holiday-inn-express-suites-troy": "ihg.com 403; the property's own IHG page could not be re-captured to back the prior VERIFIED_NO_PETS assertion",
    "springhill-suites-by-marriott-dayton-vandalia": "marriott.com 403; contradictory $50/$75 per-stay fee text from the original capture remains unresolved",
}

JS_RENDERED_NO_STATIC_CONTENT = {
    "west-bank-inn": "Wix single-page app, no server-rendered text at all",
    "hawthorn-suites-by-wyndham-miamisburg-dayton-mall-south": "wyndhamhotels.com {{pets}} template placeholder did not render server-side; no property phone/address recoverable either",
    "hawthorn-extended-stay-by-wyndham-dayton": "wyndhamhotels.com {{pets}} template placeholder did not render server-side",
    "microtel-inn-suites-by-wyndham-dayton-riverside": "wyndhamhotels.com {{pets}} template placeholder did not render server-side",
    "la-quinta-inn-suites-by-wyndham-dayton-north-tipp-city": "wyndhamhotels.com {{pets}} template placeholder did not render server-side",
    "wingate-by-wyndham-dayton---fairborn": "wyndhamhotels.com {{pets}} template placeholder did not render server-side",
    "super-8-by-wyndham-wapakoneta": "wyndhamhotels.com {{pets}} template placeholder did not render server-side",
    "super-8-by-wyndham-sidney": "wyndhamhotels.com {{pets}} template placeholder did not render server-side",
    "super-8-by-wyndham-bellefontaine": "wyndhamhotels.com {{pets}} template placeholder did not render server-side",
    "baymont-by-wyndham-greenville": "wyndhamhotels.com {{pets}} template placeholder did not render server-side",
    "baymont-by-wyndham-huber-heights-dayton": "wyndhamhotels.com {{pets}} template placeholder did not render server-side",
    "baymont-by-wyndham-springfield": "wyndhamhotels.com {{pets}} template placeholder did not render server-side",
    "the-cedar-lodge-cabins-new-paris": "static fetch OK, zero pet-policy text; also CLASSIFICATION_EXCLUDED by the prior audit (single lakefront cabin venue, not a hotel by PTF's minimum classification)",
}

UNREACHABLE_DOMAIN = {
    "grinnell-mill-bed-breakfast-yellow-springs": "grinnellmillbandb.com DNS resolution failed (getaddrinfo), not an anti-bot block",
}

NO_FIRST_PARTY_URL = [
    "red-roof-inn-dayton-north-airport", "red-roof-inn-dayton-fairborn-nutter-center",
    "red-roof-inn-dayton-south-miamisburg", "extended-stay-america-select-suites-dayton-miamisburg",
    "red-roof-inn-dayton-huber-heights", "comfort-suites-springfield-i-70", "red-roof-inn-springfield",
    "holiday-inn-express-suites-springfield", "motel-6-springfield", "relax-inn-springfield",
    "golden-inn-new-paris", "econo-lodge-alpha-beavercreek", "springs-motel-yellow-springs",
    "comfort-inn-miami-valley-centre-piqua", "quality-inn-sidney", "motel-6-sidney",
    "holiday-inn-express-suites-greenville", "quality-inn-greenville",
]

#: Identity was recovered/corrected this run but no policy evidence was found
#: on the same page -- still needs a policy capture, just no longer blocked
#: on "does this hotel exist".
IDENTITY_RECOVERED_POLICY_STILL_NEEDED = {
    "scioto-inn-urbana": "sciotoinn.com confirms identity (address + phone both "
                          "match the census exactly) but carries no pet-policy text",
}

IDENTITY_UNCERTAIN_PHANTOM = [
    "comfort-inn-washington-court-house", "studio-6-suites-springfield",
    "quality-inn-springfield", "new-budget-inn-eaton", "hotel-piqua-east-ash",
    "red-roof-inn-piqua", "monument-square-suites-urbana", "the-four-gables-urbana",
]


def build_report() -> list:
    census = {h["slug"]: h for h in json.loads(
        CENSUS_PATH.read_text(encoding="utf-8"))["hotels"]}

    def row(slug, category, detail, action):
        h = census.get(slug, {})
        return {"slug": slug, "canonical_name": h.get("canonical_name", slug),
                "category": category, "detail": detail, "next_action": action}

    report = []
    for slug, detail in ACCESS_BLOCKED.items():
        report.append(row(slug, "ACCESS_BLOCKED", detail,
            "attended/authenticated browser capture, or a direct operator phone "
            "call -- static HTTP is bot-walled at the brand-platform level "
            "(Hilton, IHG, Marriott, Best Western, Choice, Radisson, Red Roof all "
            "reproduce this same block in every Dayton/Columbus/Cleveland worker "
            "run to date; not attempted here as a bypass)"))
    for slug, detail in JS_RENDERED_NO_STATIC_CONTENT.items():
        report.append(row(slug, "JS_RENDERED_NO_STATIC_CONTENT", detail,
            "attended browser capture -- the page renders its pet-policy text "
            "client-side; a static GET returns only the unfilled template"))
    for slug, detail in UNREACHABLE_DOMAIN.items():
        report.append(row(slug, "UNREACHABLE_DOMAIN", detail,
            "retry the domain later, or locate an alternate first-party URL "
            "(the property's Facebook page or booking-platform listing)"))
    for slug in NO_FIRST_PARTY_URL:
        note = (census.get(slug, {}).get("_capture_note") or "")[:200]
        report.append(row(slug, "NO_FIRST_PARTY_URL_ON_RECORD", note,
            "no official brand or property URL has been recovered yet -- needs "
            "a brand-site search or phone verification before any evidence "
            "capture is possible"))
    for slug, detail in IDENTITY_RECOVERED_POLICY_STILL_NEEDED.items():
        report.append(row(slug, "IDENTITY_RECOVERED_POLICY_STILL_NEEDED", detail,
            "attended capture or a phone call for the pet policy specifically "
            "-- identity is no longer the blocker"))
    for slug in IDENTITY_UNCERTAIN_PHANTOM:
        note = (census.get(slug, {}).get("_capture_note") or "")[:200]
        report.append(row(slug, "IDENTITY_UNCERTAIN_PHANTOM_SUSPECT", note,
            "phone verification (numbers already on file in the census) before "
            "any further capture attempt -- OSM/directory evidence suggests "
            "possible closure, de-flagging, or residential misclassification"))
    return report


def main() -> int:
    report = build_report()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    counts = Counter(r["category"] for r in report)
    print("wrote", OUT_PATH, "with", len(report), "rows")
    for cat, n in counts.most_common():
        print(" ", cat, n)
    print("advanced-with-evidence this run:", len(ADVANCED_WITH_EVIDENCE))
    print("total accounted:", len(report) + len(ADVANCED_WITH_EVIDENCE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
