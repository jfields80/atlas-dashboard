"""Build Indianapolis Pass 1 capture-results and founder-review packets.

Reads the committed census plus the gitignored worker-tree hashes. Writes
only hashes, verdicts and proposed facts. Does not write policy authority.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
LP = _REPO_ROOT / "launch_packages" / "pettripfinder"

CROWNE_QUOTE = "No, pets are not allowed at Crowne Plaza Indianapolis-Airport."
CROWNE_HTML = "sha256:6989b22e8245344daea388c95be981df31472dc70da869ec73301677e3f2807a"
CROWNE_TEXT = "sha256:75b44eb1d0ba8141f9f98ed40db178039992ffdd94e206440a496f71a172a0de"
CROWNE_FILE = "sha256:765f35e255ee55d068bfc8dc5969c54b66cf369b7c72f1051d771f2285f8eecc"
CROWNE_PNG = "sha256:3865bb6a82d8b0ce3eaffe048e440332a914d4bbb56cc927c3de615bfc9dc08a"
CROWNE_AT = "2026-08-16T17:13:43.182Z"
CROWNE_ART = (
    "www-ihg-com-crowneplaza-hotels-us-en-indianapolis-indap-hoteldetail"
    "-2026-08-16T17-13-43-182Z.json"
)

ROWS = (
    dict(n=1, name="Baymont by Wyndham Plainfield Indianapolis Airport Area",
         outcome="IDENTITY_UNCERTAIN", runner="IDENTITY_FAILED",
         rec="HOLD_RETRY_IDENTITY",
         note="Official page matched name and city; identity gate had only one independent key (phone). Diagnostic is not extraction evidence."),
    dict(n=2, name="Best Western Plus Indianapolis Northwest",
         outcome="IDENTITY_UNCERTAIN", runner="IDENTITY_INCOMPLETE",
         rec="HOLD_RETRY_IDENTITY",
         note="Official page matched name, street and city; identity gate had only the address key. JSON-LD petsAllowed was not used. Diagnostic is not extraction evidence."),
    dict(n=3, name="Comfort Inn Indianapolis Airport Plainfield",
         outcome="IDENTITY_UNCERTAIN", runner="IDENTITY_FAILED",
         rec="HOLD_RETRY_IDENTITY",
         note="Official page matched name, phone and city; identity gate had only one independent key (phone)."),
    dict(n=4, name="Comfort Suites Indianapolis Airport",
         outcome="IDENTITY_UNCERTAIN", runner="IDENTITY_MISMATCH",
         rec="REVIEW_CENSUS_PHONE",
         note="Name and city matched the official Choice property page; census phone 317-481-0700 differed from the page phone. Not treated as a different hotel without founder review."),
    dict(n=5, name="Courtyard by Marriott Indianapolis Airport",
         outcome="IDENTITY_UNCERTAIN", runner="IDENTITY_FAILED",
         rec="HOLD_RETRY_IDENTITY",
         note="Official Marriott travel URL matched name, phone and city; identity gate had only one independent key (phone). Sibling Marriott policy was not inherited."),
    dict(n=6, name="Courtyard by Marriott Indianapolis Castleton",
         outcome="IDENTITY_UNCERTAIN", runner="IDENTITY_INCOMPLETE",
         rec="HOLD_RETRY_IDENTITY",
         note="Official overview URL matched name, street and city; identity gate had only the address key. Sibling Marriott policy was not inherited."),
    dict(n=7, name="Crowne Plaza Indianapolis Airport",
         outcome="NEGATIVE", runner="POLICY_ABSENT_CONFIRMED",
         rec="APPROVE_VERIFIED_NO_PETS",
         note="Identity confirmed on address+phone. Visible IHG FAQ states a property-specific refusal. No service-animal sentence on the captured page. JSON-LD Hotel node has no petsAllowed field and was not used as evidence."),
    dict(n=8, name="Crowne Plaza Indianapolis Downtown Union Station",
         outcome="IDENTITY_UNCERTAIN", runner="IDENTITY_INCOMPLETE",
         rec="HOLD_RETRY_IDENTITY",
         note="Official page matched name, street and city; identity gate had only the address key. Sibling Crowne Airport refusal was not inherited."),
    dict(n=9, name="Delta Hotels by Marriott Indianapolis Airport",
         outcome="IDENTITY_UNCERTAIN", runner="IDENTITY_FAILED",
         rec="HOLD_RETRY_IDENTITY",
         note="Official page matched name, phone and city; identity gate had only one independent key (phone). Sibling Marriott policy was not inherited."),
    dict(n=10, name="Embassy Suites by Hilton Indianapolis Downtown",
         outcome="ACCESS_BLOCKED", runner="IDENTITY_UNVERIFIABLE",
         rec="OPERATOR_MANUAL_SCREENSHOT",
         note="Hilton official URL stayed put but produced no page title and no identity-bearing text in 20.5s (hydration timeout). Treated as a block/shell. A block page is not a pet-policy refusal. Pets widget was not revealed. No retry against Akamai."),
)


def main() -> int:
    census = json.loads((LP / "identity_census" / "indianapolis-in.json")
                        .read_text(encoding="utf-8-sig"))
    by_name = {h["canonical_name"]: h for h in census["hotels"]}
    results = []
    for row in ROWS:
        h = by_name[row["name"]]
        did = "INDY-P1-%03d" % row["n"]
        rec = OrderedDict((
            ("decision_id", did),
            ("queue_id", did),
            ("hotel", row["name"]),
            ("identity_key", h["identity_key"]),
            ("corridor", h["corridor"]),
            ("brand", h["brand"]),
            ("requested_url", h["official_url"]),
            ("final_url", h["official_url"]),
            ("runner_reason", row["runner"]),
            ("outcome", row["outcome"]),
            ("identity_binding", {"bound": row["n"] == 7, "notes": row["note"]}),
            ("artifact_file", CROWNE_ART if row["n"] == 7 else None),
            ("artifact_sha256", CROWNE_HTML if row["n"] == 7 else None),
            ("artifact_kind", "rendered_html" if row["n"] == 7 else None),
            ("text_sha256", CROWNE_TEXT if row["n"] == 7 else None),
            ("screenshot_sha256", CROWNE_PNG if row["n"] == 7 else None),
            ("captured_at", CROWNE_AT if row["n"] == 7 else None),
            ("capture_method",
             "attended_browser" if row["n"] == 7 else "attended_browser_attempt"),
            ("source_grade", "PT1_FIRST_PARTY" if row["n"] == 7 else None),
            ("notes", [row["note"]]),
            ("exact_quotes", [CROWNE_QUOTE] if row["n"] == 7 else []),
            ("proposed_schema_1_2_facts", []),
            ("withheld_fields", []),
            ("contradiction_notes", []),
            ("recommended_founder_decision", row["rec"]),
        ))
        if row["n"] == 7:
            rec["identity_binding"] = {
                "phone": True, "street_number": True, "zip": True, "bound": True,
                "notes": "JSON-LD street 2501 South High School Road, phone "
                         "1-317-2446861, ZIP 46241 agree with the census.",
            }
            rec["proposed_schema_1_2_facts"] = [{
                "field": "pets_allowed", "value": False,
                "quote": CROWNE_QUOTE, "quote_contiguous_in_artifact": True,
            }]
            rec["contradiction_notes"] = [
                "No service-animal sentence was present on the captured page; none is proposed."
            ]
        results.append(rec)

    counts = OrderedDict((
        ("AFFIRMATIVE_STRUCTURED", 0),
        ("AFFIRMATIVE_PARTIAL", 0),
        ("NEGATIVE", 1),
        ("POLICY_NOT_FOUND", 0),
        ("IDENTITY_UNCERTAIN", 8),
        ("ROUTING_PROBLEM", 0),
        ("ACCESS_BLOCKED", 1),
        ("CAPTURE_FAILED", 0),
    ))
    results_doc = OrderedDict((
        ("schema", "ptf-indianapolis-pass1-capture-results/1.0"),
        ("work_order", "PTF-INDIANAPOLIS-ATTENDED-CAPTURE-001"),
        ("as_of", "2026-08-16"),
        ("market_id", "indianapolis-in"),
        ("captured_by", "grok-4.6 (PTF-INDIANAPOLIS-ATTENDED-CAPTURE-001, agent)"),
        ("capture_method",
         "attended browser (dedicated visible Chrome via official "
         "CaptureRunner / LiveBrowserSession); raw HTML and screenshot "
         "retained only in gitignored worker tree "
         "data/worker_runs/pettripfinder/indianapolis-attended-capture-001/; "
         "committed output is hashes and verdicts only"),
        ("branch_checkpoint", "7e6c3c73fbd0ce3ab40a10c1e4dac9894b3431c1"),
        ("rows_total", 10),
        ("rows_captured", 1),
        ("rows_with_publication_grade_artifact", 1),
        ("outcome_counts", counts),
        ("rule",
         "A failed or incomplete identity gate is never negative evidence. "
         "A refusal is proposed only where the property own page states it "
         "in a hash-bound artifact. No Indianapolis policy authority, "
         "exclusion, seed, or routing row was written. "
         "POINTER_TO_EVIDENCE was not used."),
        ("speed_benchmark", OrderedDict((
            ("batch_total", 10),
            ("started_at", "2026-08-16T17:10:20.619Z"),
            ("finished_at", "2026-08-16T17:18:19.525Z"),
            ("elapsed_seconds", 481.54),
            ("captures_completed", 10),
            ("successful_artifacts", 1),
            ("median_inter_capture_gap_seconds", 50.7),
            ("captures_per_hour", 74.8),
            ("positive_rate", 0.0),
            ("negative_rate", 0.1),
            ("policy_not_found_rate", 0.0),
            ("blocked_or_identity_failure_rate", 0.9),
        ))),
        ("results", results),
    ))
    negative = [r for r in results if r["outcome"] == "NEGATIVE"]
    packet = OrderedDict((
        ("schema", "ptf-indianapolis-pass1-founder-review-packet/1.0"),
        ("work_order", "PTF-INDIANAPOLIS-ATTENDED-CAPTURE-001"),
        ("as_of", "2026-08-16"),
        ("prepared_by", "grok-4.6 (PTF-INDIANAPOLIS-ATTENDED-CAPTURE-001, agent)"),
        ("status", "FOUNDER_REVIEW_REQUIRED"),
        ("rule",
         "Nothing here is published. Approving the negative candidate "
         "authorizes a later exclusion write bound to the named artifact "
         "hashes. Identity-uncertain rows stay unresolved. No founder "
         "approval is recorded in this packet."),
        ("positive_candidates", []),
        ("negative_candidates", [{
            "decision_id": "INDY-P1-007",
            "hotel": "Crowne Plaza Indianapolis Airport",
            "identity_key": "crowne plaza indianapolis airport",
            "corridor": "indianapolis-in__airport",
            "requested_url": by_name["Crowne Plaza Indianapolis Airport"]["official_url"],
            "final_url": by_name["Crowne Plaza Indianapolis Airport"]["official_url"],
            "identity_binding": negative[0]["identity_binding"],
            "artifact_sha256": CROWNE_HTML,
            "artifact_kind": "rendered_html",
            "artifact_file_sha256": CROWNE_FILE,
            "text_sha256": CROWNE_TEXT,
            "screenshot_sha256": CROWNE_PNG,
            "captured_at": CROWNE_AT,
            "capture_method": "attended_browser",
            "source_grade": "PT1_FIRST_PARTY",
            "exact_quotes": [CROWNE_QUOTE],
            "proposed_schema_1_2_facts": [{
                "field": "pets_allowed", "value": False,
                "quote": CROWNE_QUOTE, "quote_contiguous_in_artifact": True,
            }],
            "withheld_fields": [],
            "contradiction_notes": [
                "No service-animal sentence was present on the captured page; none is proposed."
            ],
            "recommended_founder_decision": "APPROVE_VERIFIED_NO_PETS",
        }]),
        ("identity_uncertain",
         [r for r in results if r["outcome"] == "IDENTITY_UNCERTAIN"]),
        ("access_blocked",
         [r for r in results if r["outcome"] == "ACCESS_BLOCKED"]),
        ("founder_decisions_required", 10),
        ("authority_changed", False),
    ))
    (LP / "indianapolis_pass1_capture_results.json").write_text(
        json.dumps(results_doc, indent=2) + "\n", encoding="utf-8")
    (LP / "indianapolis_pass1_founder_review_packet.json").write_text(
        json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
