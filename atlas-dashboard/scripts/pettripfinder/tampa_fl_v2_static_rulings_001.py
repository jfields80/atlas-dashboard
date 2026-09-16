"""PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001 -- identity-only reads and competitor leads.

IDENTITY_ONLY_PAGES: properties whose OWN page states their address but no operative pet policy the shared reader
reads. Each row: (name, street, city, postal, phone, url, the sha256 (prefix) of the document read, note). They open
or confirm a building and carry no policy. Empty at authoring time -- populated only after the attended/static
capture lane identifies one.

COMPETITOR_LEADS: names only, loaded from the competitor challenge lane's committed report
(``tampa_fl_v2_competitor_challenge_001.json``) when it exists. A lead proposes and never decides; its pet claims are
never read.
"""
from __future__ import annotations

import json
import os

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
_CHALLENGE = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                          "tampa_fl_v2_competitor_challenge_001.json")

IDENTITY_ONLY_PAGES = [
]


def _competitor_leads():
    if not os.path.exists(_CHALLENGE):
        return []
    with open(_CHALLENGE, encoding="utf-8") as fh:
        doc = json.load(fh)
    return [(r["name"], r["bringfido_url"]) for r in doc.get("leads", []) if r.get("name")]


COMPETITOR_LEADS = _competitor_leads()

#: No regional visitor-center roster is used in this market.
REGIONAL_VISITOR_CENTER_SOURCE = ""
REGIONAL_VISITOR_CENTER_LEADS = []
