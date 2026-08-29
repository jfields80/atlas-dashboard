# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FIRECRAWL-PASS-008 -- the defect that cost the pass.

Records, with evidence, why 49 of 65 paid attempts were refused before any page
could be judged, and states the repair WITHOUT APPLYING IT.

``policy_surface.page_health`` gates a fetched page on identity: when the row
carries a brand property code, the code parsed from the FINAL url must equal
the expected one, or the page is UNEXPECTED_PAGE. That gate is right. What is
wrong is the parser behind it: ``PROPERTY_CODE_PATTERNS`` holds patterns for
IHG and Choice that do not match those brands' own canonical URL shapes, so
``property_code`` returns an empty string and the gate compares "" against a
real code and refuses every page. The refusal is indistinguishable, in the
ledger, from a brand serving the wrong page.

THE REPAIR IS NOT APPLIED HERE, for two reasons that both point the same way:

  * ``PROPERTY_CODE_PATTERNS`` is SHARED. Every market and every lane reads it
    -- Cleveland, Milwaukee, Columbus, Indianapolis, the Marriott and Hilton
    surfaces. A Detroit Firecrawl pass is not the place to change how every
    market resolves identity.
  * A reading rule must not be widened during the review it feeds. Repairing
    the parser and re-running inside this order would decide, with a rule
    written after seeing the failures, the very rows the founder is being asked
    to rule on.

So the proposed patterns are PROVEN here against the 53 canonical URLs that
carry a code, and left for a founder to authorise. The 49 refused rows are not
re-run: this order forbids duplicate page buys, and re-running them as they
stand would buy the same refusal twice.
"""
from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_surface as PS  # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FIRECRAWL-PASS-008"
AS_OF = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
QUALIFICATION = LP / "detroit_ann_arbor_firecrawl_lane_qualification_008.json"
OUT_PATH = LP / "detroit_ann_arbor_property_code_defect_008.json"

#: Proposed, NOT APPLIED. Each is the committed pattern with the single
#: structural correction named in ``diagnosis`` and nothing else -- a wider
#: pattern would start matching URLs the gate is supposed to refuse.
PROPOSED = OrderedDict([
    ("IHG", OrderedDict([
        ("committed", r"/hotels/[a-z]{2}/[a-z]+/([a-z0-9]{5})/"),
        ("proposed", r"/hotels/[a-z]{2}/[a-z]{2}/[a-z0-9-]+/([a-z0-9]{5})/"),
        ("diagnosis",
         "the committed pattern expects /hotels/<country>/<city>/<code>/, but "
         "the brand's URL is /hotels/us/en/<city>/<code>/ -- there is a "
         "LANGUAGE segment between country and city that the pattern does not "
         "allow. With it absent, [a-z]+ consumes 'en' and the capture group is "
         "offered the city, which is hyphenated and the wrong length."),
        ("example",
         "https://www.ihg.com/crowneplaza/hotels/us/en/auburn-hills/dttah/"
         "hoteldetail -> expected dttah"),
    ])),
    ("CHOICE", OrderedDict([
        ("committed", r"/[a-z]{2}/[a-z-]+/[a-z-]+-hotel/([a-z0-9]{4,8})"),
        ("proposed", r"/[a-z-]+/[a-z-]+/[a-z-]+-hotels?/([a-z0-9]{4,8})"),
        ("diagnosis",
         "two mismatches. The committed pattern expects a two-letter state "
         "('/mi/') where the brand spells the state out ('/michigan/'), and it "
         "expects a singular '-hotel' segment where the brand uses the plural "
         "'-hotels'."),
        ("example",
         "https://www.choicehotels.com/michigan/romulus/clarion-hotels/mi190 "
         "-> expected mi190"),
    ])),
])


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def run() -> None:
    qualification = load(QUALIFICATION)
    rows = qualification["qualified_rows"]
    host_family = {"ihg.com": "IHG", "choicehotels.com": "CHOICE",
                   "wyndhamhotels.com": "WYNDHAM"}

    evidence: List[Dict] = []
    for family, spec in PROPOSED.items():
        pattern = re.compile(spec["proposed"])
        subject = [row for row in rows
                   if host_family.get(row["normalized_host"]) == family
                   and (row.get("property_code") or "")]
        committed_ok = proposed_ok = 0
        samples = []
        for row in subject:
            expected = (row.get("property_code") or "").lower()
            now = PS.property_code(row["canonical_url"], family).lower()
            match = pattern.search(row["canonical_url"])
            then = (match.group(1) if match else "").lower()
            committed_ok += int(now == expected)
            proposed_ok += int(then == expected)
            if len(samples) < 3:
                samples.append(OrderedDict([
                    ("url", row["canonical_url"]),
                    ("expected_code", expected),
                    ("committed_parser_returns", now or "(empty)"),
                    ("proposed_parser_returns", then or "(empty)"),
                ]))
        evidence.append(OrderedDict([
            ("family", family),
            ("rows_carrying_a_code", len(subject)),
            ("committed_pattern", spec["committed"]),
            ("committed_parses_correctly", committed_ok),
            ("proposed_pattern", spec["proposed"]),
            ("proposed_parses_correctly", proposed_ok),
            ("diagnosis", spec["diagnosis"]),
            ("example", spec["example"]),
            ("samples", samples),
        ]))

    total_rows = sum(item["rows_carrying_a_code"] for item in evidence)
    total_now = sum(item["committed_parses_correctly"] for item in evidence)
    total_then = sum(item["proposed_parses_correctly"] for item in evidence)

    write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-property-code-defect/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("status", "AWAITING_FOUNDER_AUTHORISATION"),
        ("applied", False),
        ("severity",
         "HIGH, and NOT specific to Detroit. Every market that routes an IHG "
         "or Choice property through a lane using page_health has been paying "
         "for pages it then refused on an identity check that could not "
         "succeed. Detroit is simply the first market to run a cohort large "
         "enough in those two families to make it visible."),
        ("what_happened",
         "49 of this pass's 65 paid attempts were refused as UNEXPECTED_PAGE "
         "before any page could be judged. The page-health gate compares the "
         "property code parsed from the final URL against the expected code; "
         "for IHG and Choice the parser returns an empty string, so the "
         "comparison could never succeed."),
        ("cost_of_the_defect_usd", 3.53),
        ("what_it_is_not",
         "not a bot wall, not a brand serving the wrong page, and not evidence "
         "about any hotel. The refused attempts measured nothing, which is why "
         "the yield artifact reports them on their own denominator instead of "
         "blending them into a rate."),
        ("proof", OrderedDict([
            ("rows_tested", total_rows),
            ("committed_parser_correct", total_now),
            ("proposed_parser_correct", total_then),
            ("note", "tested against the canonical URLs this market already "
                     "holds, at zero cost. This proves the PARSER reads the "
                     "code; it does not prove the pages are reachable, which "
                     "only a re-run would show."),
        ])),
        ("evidence", evidence),
        ("repair_is_not_applied_because", [
            "PROPERTY_CODE_PATTERNS is shared by every market and both paid "
            "lanes; a Detroit Firecrawl pass is not the place to change how "
            "every market resolves identity",
            "a reading rule must not be widened during the review it feeds -- "
            "repairing and re-running inside this order would decide the very "
            "rows the founder is being asked to rule on",
            "this order forbids duplicate page buys, and the 49 refused rows "
            "would have to be bought again",
        ]),
        ("recommended_next_order", OrderedDict([
            ("1", "apply the two proposed patterns behind negative tests that "
                  "pin what must STILL be refused -- a brand landing page, a "
                  "different property's code, a locale redirect"),
            ("2", "run the full test suite: these patterns are shared, so the "
                  "blast radius is every market, not Detroit"),
            ("3", "re-run the 49 refused Detroit rows as a fresh authorised "
                  "cohort, priced at the Wilson LOWER bound in the yield "
                  "artifact"),
        ])),
    ]))

    print("=== the property-code defect ===")
    for item in evidence:
        print("  %-7s %2d rows | committed parses %d, proposed parses %d"
              % (item["family"], item["rows_carrying_a_code"],
                 item["committed_parses_correctly"],
                 item["proposed_parses_correctly"]))
    print("  total: %d/%d -> %d/%d" % (total_now, total_rows, total_then,
                                       total_rows))
    print("  NOT APPLIED -- awaiting founder authorisation")
    print("wrote", OUT_PATH.name)


if __name__ == "__main__":
    run()
