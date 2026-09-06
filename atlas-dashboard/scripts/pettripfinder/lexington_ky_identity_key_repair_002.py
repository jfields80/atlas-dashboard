"""PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 -- identity-key defect repair.

A policy page exposed a genuine identity defect in the order-001 artifacts,
which is the one circumstance this order is allowed to reach back and correct.

THE DEFECT. `lexington_ky_routing_and_static_capture_001.py` derived
`identity_key` from the hotel NAME alone. Lexington has two hotels called
"Holiday Inn Express" (2255 Buena Vista Road / Hamburg, and 1935 Stanton Way /
Griffin Gate) and two called "Red Roof Inn" (2651 Wilhite Drive and 1980
Haggard Court). So 61 distinct hotels collapsed into 59 identity keys, and each
colliding pair also shared one capture directory, because `slug` was the same
string.

This is the factory's own standing rule turned on its own code: a NAME proposes
an identity and never decides it; verification is on address, phone or property
code.

WHAT WAS AND WAS NOT DAMAGED. Checked before repairing, not assumed:

  * Only ONE artifact directory exists per colliding pair -- `holiday-inn-express`
    (the routed Hamburg row) and no `red-roof-inn` directory at all, because
    neither Red Roof was ever routed. So no capture was overwritten and no
    evidence was cross-bound.
  * The Firecrawl row that bound to `holiday-inn-express` states page address
    2255 Buena Vista Road, which is the Hamburg row's own census address. The
    ACQUISITION bound to the right hotel on the address; only the KEY was wrong.

THE REPAIR. The key becomes `<name slug>--<discriminator>`, where the
discriminator is the row's own stated street address, or its OSM element id
when it states none. Both come from the row itself and neither is a sequence
number. The Firecrawl report is remapped by REQUESTED URL, which is
unambiguous, so no paid call is repeated: this script makes no network request
and spends nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-LEXINGTON-KY-POLICY-ACQUISITION-002"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
ROUTING = os.path.join(REPORTS, "lexington_ky_routing_and_static_capture_001.json")
FIRECRAWL = os.path.join(REPORTS, "lexington_ky_firecrawl_pass_002.json")


def norm(s):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    args = ap.parse_args()

    routing = json.load(open(ROUTING, encoding="utf-8"))
    rows = routing["identities"]

    before = Counter(r["identity_key"] for r in rows)
    collisions_before = {k: v for k, v in before.items() if v > 1}

    remap = []
    for r in rows:
        name_slug = slugify(r["name"])
        disc = slugify(r.get("address_line") or "")
        if not disc:
            disc = slugify(r.get("osm_element") or "")
        new_key = ("%s--%s" % (name_slug, disc)) if disc else name_slug
        if new_key != r["identity_key"]:
            remap.append(OrderedDict([
                ("old_identity_key", r["identity_key"]),
                ("new_identity_key", new_key),
                ("name", r["name"]),
                ("discriminator_source",
                 "stated street address" if slugify(r.get("address_line") or "")
                 else "OSM element id"),
            ]))
        r["identity_key"] = new_key
        # The artifact `slug` is deliberately LEFT ALONE. It is a filesystem
        # path that already points at real captured evidence, and rewriting it
        # would orphan artifacts this order paid Firecrawl credits for. The
        # identity and the artifact path are two different things; conflating
        # them is what produced the defect.
        r["name_slug"] = name_slug
        r["identity_discriminator"] = disc
        r["artifact_slug"] = r["slug"]

    after = Counter(r["identity_key"] for r in rows)
    collisions_after = {k: v for k, v in after.items() if v > 1}

    routing.setdefault("defect_repairs", []).append(OrderedDict([
        ("work_order", WORK_ORDER),
        ("defect", "identity_key was derived from the hotel NAME alone"),
        ("found_by",
         "a Firecrawl policy page whose stated address (2255 Buena Vista Road) did not match "
         "the census row an identity_key lookup returned (1935 Stanton Way)"),
        ("collisions_before", collisions_before),
        ("collisions_after", collisions_after),
        ("keys_before", len(before)), ("keys_after", len(after)),
        ("rows", len(rows)),
        ("evidence_damage", "NONE -- only one artifact directory existed per colliding pair, "
                            "and the paid Firecrawl call bound to the correct hotel on its "
                            "stated address"),
        ("artifact_slug_preserved", True),
    ]))

    with open(ROUTING, "w", encoding="utf-8") as fh:
        json.dump(routing, fh, indent=1, default=str)
        fh.write("\n")

    # --- remap the Firecrawl report by requested URL ----------------------
    fc_remapped = 0
    if os.path.exists(FIRECRAWL):
        fc = json.load(open(FIRECRAWL, encoding="utf-8"))
        by_url = {r["route"]: r for r in rows if r.get("route")}
        for row in fc["rows"]:
            u = row.get("requested_url")
            if u and u in by_url:
                new = by_url[u]["identity_key"]
                if new != row.get("identity_key"):
                    row["identity_key_before_repair"] = row.get("identity_key")
                    row["identity_key"] = new
                    fc_remapped += 1
        fc["identity_key_repair"] = OrderedDict([
            ("work_order", WORK_ORDER),
            ("method", "remapped by REQUESTED URL, which is unambiguous"),
            ("rows_remapped", fc_remapped),
            ("firecrawl_calls_repeated", 0),
            ("credits_spent_by_this_repair", 0),
        ])
        with open(FIRECRAWL, "w", encoding="utf-8") as fh:
            json.dump(fc, fh, indent=1, default=str)
            fh.write("\n")

    report = OrderedDict([
        ("schema", "ptf-identity-key-repair/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", "lexington-ky"),
        ("as_of", args.as_of),
        ("network_requests", 0), ("usd_spent", 0.0), ("credits_spent", 0),
        ("collisions_before", collisions_before),
        ("collisions_after", collisions_after),
        ("keys_before", len(before)), ("keys_after", len(after)), ("rows", len(rows)),
        ("remapped_keys", remap),
        ("firecrawl_rows_remapped", fc_remapped),
    ])
    out = os.path.join(REPORTS, "lexington_ky_identity_key_repair_002.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")

    print("rows", len(rows), "keys", len(before), "->", len(after))
    print("collisions before:", collisions_before, "after:", collisions_after)
    print("firecrawl rows remapped:", fc_remapped)
    print("wrote", out)
    return 0 if not collisions_after else 1


if __name__ == "__main__":
    raise SystemExit(main())
