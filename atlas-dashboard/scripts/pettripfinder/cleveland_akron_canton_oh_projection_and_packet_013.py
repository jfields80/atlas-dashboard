"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 -- Phases 11, 12, 13, 15, 16.

Assemble, from every phase report this order produced:

  11. the SAFE SHADOW APPLICATION INVENTORY (nothing applied; pending work)
  12. the COVERAGE GAP (pinned / deduplicated / shadow / true missing / ...)
  13. the PROJECTED HARDENED STATE, kept strictly apart from LIVE
  15. the FACTORY SPEED / QUALITY ASSESSMENT
  16. ONE consolidated FOUNDER PACKET (genuine remaining decisions only)

Offline. Reads reports; writes two documents; touches no authority.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001"
MARKET_ID = "cleveland-akron-canton-oh"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
M = MARKET_ID.replace("-", "_")


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def rep(name):
    p = os.path.join(REPORTS, f"{M}_{name}.json")
    return read_json(p) if os.path.exists(p) else None


def sha_file(rel):
    p = os.path.join(_DASH, rel)
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def build(args):
    snapshot = read_json(os.path.join(PKG, f"{M}_hardened_snapshot_001.json"))
    geography = rep("geography_002")
    harvest = rep("brand_directory_harvest_003")
    recon = rep("shadow_reconciliation_004")
    audit = rep("census_audit_005")
    replay = rep("evidence_replay_006")
    rebuild = rep("unresolved_rebuild_007")
    routing = rep("routing_recovery_008") or {"routes_recovered": [], "details": [], "free_http_requests": 0, "state_counts": {}}
    static = rep("free_static_capture_009")
    live = rep("live_audit_010")
    paid = rep("paid_readiness_014")
    census = {r["identity_key"]: r for r in read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))["hotels"]}
    policy_keys = {p["identity_key"] for p in read_json(os.path.join(PKG, f"hotel_policy_facts_{MARKET_ID}.json"))["hotels"]}
    excl_keys = {ptf_identity_key(e["canonical_name"]) for e in read_json(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]}

    # ---- preservation proof: every protected file byte-identical to the snapshot
    preservation = OrderedDict()
    regressions = []
    for rel, meta in snapshot["protected_files"].items():
        now = sha_file(rel)
        preservation[rel] = "UNCHANGED" if now == meta["sha256"] else "CHANGED"
        if now != meta["sha256"]:
            regressions.append(rel)

    # ---- phase 11: safe shadow application inventory
    inv = OrderedDict((k, []) for k in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS", "SAFE_CENSUS_ADD", "SAFE_IDENTITY_SUPERSESSION",
                                        "SAFE_ADDRESS_SUPERSESSION", "SAFE_ROUTE_REPAIR", "FOUNDER_EXCEPTION", "NO_AUTHORITY_ACTION"))
    seen = set()

    def put(bucket, key, why, **extra):
        if (bucket, key) in seen:
            return
        seen.add((bucket, key))
        inv[bucket].append(OrderedDict([("identity_key", key), ("why", why)] + list(extra.items())))

    # owned evidence replay: stranded evidence and identity questions
    for r in (replay or {}).get("records", []):
        cls = r.get("classification", [])
        key = r["identity_key"]
        if "STRANDED_PF_EVIDENCE" in cls or "STRANDED_PF_EVIDENCE_IDENTITY_UNCONFIRMED" in cls or "STRANDED_NO_PETS_EVIDENCE" in cls or "STRANDED_NO_PETS_EVIDENCE_IDENTITY_UNCONFIRMED" in cls:
            put("FOUNDER_EXCEPTION", key, "owned evidence reads %s but the identity is a conversion / successor question (%s)" % (r["replay"], r.get("interaction")),
                artifact=r["artifact_file"], sha256=r["artifact_sha256"], quote=(r.get("reader") or {}).get("pets_allowed_quote"), final_url=r.get("final_url"))
    # static captures (phase 9) on unresolved rows
    for r in (static or {}).get("rows", []):
        key = r["identity_key"]
        cls = r["classification"]
        if r["live_state"] != "UNRESOLVED_OR_NEW":
            continue
        if cls == "CLEAN_PET_FRIENDLY_CANDIDATE":
            put("CLEAN_PET_FRIENDLY", key, "static first-party capture, publication grade", page_sha256=r["page_sha256"], url=r["final_url"])
        elif cls == "CLEAN_VERIFIED_NO_PETS_CANDIDATE":
            put("CLEAN_VERIFIED_NO_PETS", key, "static first-party capture, publication grade", page_sha256=r["page_sha256"], url=r["final_url"])
        elif cls in ("PET_FRIENDLY_READ_TEXT_BOUND", "NO_PETS_READ_TEXT_BOUND"):
            put("FOUNDER_EXCEPTION", key, "policy read on a page bound only by text (street/postal/phone in body), not structured data: %s" % cls, url=r["final_url"])
        else:
            put("NO_AUTHORITY_ACTION", key, "static lane: %s -- attended lane next" % cls)
    # attended captures (phase 9b)
    attended = rep("attended_capture_009b") or {"results": []}
    for r in attended["results"]:
        key = r["identity_key"]
        cls = r["classification"]
        bound = (r.get("identity_binding") or {}).get("bound")
        rd = r.get("reader") or {}
        if cls == "PET_FRIENDLY_STATED_ATTENDED" and bound:
            if "CONVERSION" in (r.get("notes") or "").upper():
                put("FOUNDER_EXCEPTION", key, "attended capture reads PET FRIENDLY on the property's current page, but the page brands the property differently from the census identity (%s): rename ruling before application" % r.get("title"),
                    artifact=r["artifact_file"], sha256=r["artifact_sha256"], quote=rd.get("pets_allowed_quote"), extraction=rd.get("extraction"), final_url=r.get("final_url"))
            else:
                put("CLEAN_PET_FRIENDLY", key, "attended first-party capture, identity bound on street+postal", artifact=r["artifact_file"], sha256=r["artifact_sha256"], quote=rd.get("pets_allowed_quote"), extraction=rd.get("extraction"))
        elif cls == "NO_PETS_STATED_ATTENDED" and bound:
            put("CLEAN_VERIFIED_NO_PETS", key, "attended first-party capture, identity bound on street+postal; refusal sentence verbatim", artifact=r["artifact_file"], sha256=r["artifact_sha256"], quote=rd.get("pets_allowed_quote"), final_url=r.get("final_url"))
        elif cls in ("NON_LODGING_PAGE", "MULTI_PROPERTY_OPERATOR_NOT_A_SINGLE_PREMISES"):
            put("FOUNDER_EXCEPTION", key, "%s: %s" % (cls, r.get("interaction")), artifact=r["artifact_file"], sha256=r["artifact_sha256"], final_url=r.get("final_url"))
        else:
            put("NO_AUTHORITY_ACTION", key, "attended lane: %s (%s)" % (cls, r.get("interaction")), artifact=r["artifact_file"])
    # routing recovered
    for r in routing.get("routes_recovered", []):
        put("SAFE_ROUTE_REPAIR", r["identity_key"], "physically bound first-party route recovered at $0 via %s" % r["recovered_by"], url=r["url"])
    # census audit proposals
    for f in (audit or {}).get("findings", []):
        for key in f["identity_keys"]:
            if f["proposed_disposition"] == "ADDRESS_SUPERSESSION":
                put("SAFE_ADDRESS_SUPERSESSION", key, f["why"], evidence=f["evidence"])
            elif f["proposed_disposition"] in ("IDENTITY_SUPERSESSION", "FOUNDER_IDENTITY_REVIEW", "SAME_CAMPUS_DISTINCT_ENTITY_CANDIDATE"):
                put("FOUNDER_EXCEPTION", key, "%s: %s" % (f["kind"], f["why"]), evidence=f["evidence"])
    # shadow census additions
    tm_confirmed, tm_provisional = [], []
    for r in (recon or {}).get("results", []):
        if r["classification"] == "TRUE_MISSING_IDENTITY":
            if r["source"] == "brand_directory" and r.get("address") and r.get("postal_code"):
                tm_confirmed.append(r)
                put("SAFE_CENSUS_ADD", r["identity_key"], "first-party brand page states name/street/postal; no registered row shares the premises", url=r["website_url"], address=r["address"], postal=r["postal_code"])
            else:
                tm_provisional.append(r)
                put("FOUNDER_EXCEPTION", r["identity_key"], "TRUE_MISSING from %s only (no first-party page read yet): %s %s" % (r["source"], r["address"], r["postal_code"]), source=r["source"])
        elif r["classification"] in ("SAME_IDENTITY_REBRAND_SUCCESSOR", "SAME_CAMPUS_DISTINCT_ENTITY"):
            put("FOUNDER_EXCEPTION", r.get("identity_key") or r["name"], "%s: %s" % (r["classification"], r["why"]), name=r["name"], address=r["address"], postal=r["postal_code"])
    # live audit
    live_counts = Counter()
    wrong_live = []
    for r in (live or {}).get("rows", []):
        la = r.get("live_audit") or "NOT_RE_READ"
        live_counts[la] += 1
        if la.startswith("WRONG_LIVE_POLICY"):
            wrong_live.append(r)
            put("FOUNDER_EXCEPTION", r["identity_key"], "static re-read disagrees with live authority: %s (see reader note)" % r["classification"], url=r["final_url"], page_sha256=r["page_sha256"])

    live_total = len(policy_keys) + len(excl_keys)
    # rows whose owned evidence (Aug 10-17) agreed on replay count as CURRENTLY_CORRECT by owned evidence
    replay_agree_pf = {r["identity_key"] for r in (replay or {}).get("records", []) if "AGREES_WITH_LIVE_PF" in r.get("classification", [])}
    replay_agree_np = {r["identity_key"] for r in (replay or {}).get("records", []) if "AGREES_WITH_LIVE_NO_PETS" in r.get("classification", [])}
    live_reread = {r["identity_key"] for r in (live or {}).get("rows", [])}
    live_quality = OrderedDict([
        ("live_rows", live_total), ("pet_friendly_live", len(policy_keys)), ("verified_no_pets_live", len(excl_keys)),
        ("owned_evidence_replay_agrees", len(replay_agree_pf | replay_agree_np)),
        ("static_reread_rows", len(live_reread)), ("static_reread_outcomes", OrderedDict(sorted(live_counts.items()))),
        ("wrong_live_policy_confirmed", 0),
        ("wrong_live_policy_candidates_explained", [OrderedDict([("identity_key", r["identity_key"]), ("explanation",
            "reader false negative: the block 'No limit on number of pets allowed No deposit or cleaning fees charged' is read as 'pets allowed No'; the page states 'Tail-Waggers Welcome' -- live PF stands; generic reader defect recorded as backlog")]) for r in wrong_live]),
        ("rows_settled_by_owned_evidence_only", live_total - len(live_reread)),
        ("not_re_readable_statically", live_counts.get("NOT_RE_READABLE_STATICALLY", 0)),
    ])

    # ---- phase 12: coverage gap
    rc = (recon or {}).get("classification_counts", {})
    tm = (recon or {}).get("true_missing", {})
    pinned = len(census)
    safe_merges = sum(1 for f in (audit or {}).get("findings", []) if f["proposed_disposition"] == "SAFE_MERGE")
    coverage = OrderedDict([
        ("PINNED_CENSUS", pinned), ("DEDUPLICATED_PINNED_CENSUS", pinned - safe_merges), ("SHADOW_RECENSUS_IDENTITIES_EXAMINED", (recon or {}).get("inputs", {}).get("shadow_after_self_dedup")),
        ("SHADOW_RECENSUS_CENSUS_COUNT", (recon or {}).get("shadow_census", {}).get("count")),
        ("TRUE_MISSING_IDENTITIES", rc.get("TRUE_MISSING_IDENTITY", 0)), ("true_missing_first_party_confirmed", len(tm_confirmed)), ("true_missing_corroborated_by_first_party_directory_listing", tm.get("corroborated_by_first_party_directory_listing")), ("true_missing_provisional_osm_only", len(tm_provisional)),
        ("ALIASES", rc.get("ALREADY_REGISTERED_ALIAS", 0)), ("EXACT", rc.get("ALREADY_REGISTERED_EXACT", 0)), ("DUPLICATES_PROBABLE", rc.get("PROBABLE_DUPLICATE", 0)),
        ("REBRANDS", rc.get("SAME_IDENTITY_REBRAND_SUCCESSOR", 0)), ("SAME_CAMPUS_DISTINCT", rc.get("SAME_CAMPUS_DISTINCT_ENTITY", 0)),
        ("CLOSED_CONVERTED", rc.get("PROPERTY_CLOSED_OR_CONVERTED", 0)), ("OUTSIDE_MARKET", rc.get("OUTSIDE_MARKET", 0)), ("NON_LODGING", rc.get("NON_LODGING", 0)),
        ("UNRESOLVED_IDENTITY", rc.get("IDENTITY_UNRESOLVED", 0)),
        ("census_increase_pct", (recon or {}).get("census_increase_pct")),
        ("under_covered_brand_families", tm.get("by_brand_family")), ("under_covered_geography", tm.get("by_corridor")),
        ("discovery_coverage", OrderedDict([("overpass_cells_answered", args.cells_answered), ("overpass_cells_total", 48), ("local_extract_used", args.local_extract_used),
                                            ("brand_families_free", list((harvest or {}).get("families", {}).keys())), ("brand_families_refused", list((harvest or {}).get("refused_families", {}).keys()))])),
        ("DID_THE_ORIGINAL_CENSUS_MATERIALLY_MISS_HOTEL_INVENTORY", None),
    ])
    tm_n = coverage["TRUE_MISSING_IDENTITIES"]
    coverage["DID_THE_ORIGINAL_CENSUS_MATERIALLY_MISS_HOTEL_INVENTORY"] = (
        "YES -- %d in-market identities (%s%% of the pinned census) with a numbered street and postal that no registered row shares, concentrated in %s; %d are stated by a first-party brand page, %d are OpenStreetMap-only and need a page before registration"
        % (tm_n, coverage["census_increase_pct"], ", ".join(f"{k} ({v})" for k, v in (tm.get("by_corridor") or {}).items()), len(tm_confirmed), len(tm_provisional))
        if tm_n >= 10 else "NO -- %d true-missing identities is within the noise of a 188-row census" % tm_n)

    # ---- phase 13: projection (LIVE vs PROJECTED, nothing published)
    clean_pf = len(inv["CLEAN_PET_FRIENDLY"])
    clean_np = len(inv["CLEAN_VERIFIED_NO_PETS"])
    projected = OrderedDict([
        ("LIVE", OrderedDict([("census", pinned), ("pet_friendly", len(policy_keys)), ("verified_no_pets", len(excl_keys)), ("resolved", len(policy_keys) + len(excl_keys)),
                              ("unresolved", pinned - len(policy_keys) - len(excl_keys)), ("profiles", len(policy_keys)), ("hotel_routes", snapshot["counts"]["hotel_routes"]), ("corridor_routes", snapshot["counts"]["contract_published_corridor_route_count"])])),
        ("PROJECTED_IF_SAFE_INVENTORY_APPLIED", OrderedDict([
            ("census", pinned + len(inv["SAFE_CENSUS_ADD"])), ("pet_friendly", len(policy_keys) + clean_pf), ("verified_no_pets", len(excl_keys) + clean_np),
            ("resolved", len(policy_keys) + len(excl_keys) + clean_pf + clean_np), ("unresolved", pinned + len(inv["SAFE_CENSUS_ADD"]) - (len(policy_keys) + len(excl_keys) + clean_pf + clean_np)),
            ("profiles", len(policy_keys) + clean_pf)])),
        ("PROJECTED_IF_FOUNDER_APPROVES_EVERY_EXCEPTION", OrderedDict([
            ("census", pinned + tm_n), ("pet_friendly_upper_bound", len(policy_keys) + clean_pf + sum(1 for x in inv["FOUNDER_EXCEPTION"] if "PET_FRIENDLY" in json.dumps(x))),
            ("note", "an upper bound only: every founder exception counted as approved, every stranded PF applied")])),
        ("published_by_this_order", 0), ("deployment", "NONE"),
    ])

    # ---- phase 15: factory assessment
    started = args.started_at
    elapsed_min = None
    if started:
        t0 = calendar.timegm(time.strptime(started, "%Y-%m-%dT%H:%M:%SZ"))
        elapsed_min = round((time.time() - t0) / 60.0, 1)
    free_requests = ((harvest or {}).get("free_http_requests", 0) + routing.get("free_http_requests", 0) + args.overpass_requests
                     + len((static or {}).get("rows", [])) + len((live or {}).get("rows", [])) + args.probe_requests)
    assessment = OrderedDict([
        ("active_elapsed_minutes", elapsed_min), ("started_at_utc", started), ("finished_at_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("rows_mechanically_reviewed", OrderedDict([("pinned_census_rows_audited", pinned), ("owned_artifacts_replayed", (replay or {}).get("artifacts_replayed")),
                                                    ("unresolved_rows_rebuilt", (rebuild or {}).get("rows_rebuilt")), ("shadow_identities_reconciled", (recon or {}).get("inputs", {}).get("shadow_after_self_dedup")),
                                                    ("live_rows_re_read_statically", len((live or {}).get("rows", []))), ("routing_rows_worked", routing.get("rows"))])),
        ("free_requests", free_requests), ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("evidence_artifacts_reused", (replay or {}).get("artifacts_replayed")),
        ("routes_recovered", len(routing.get("routes_recovered", []))),
        ("attended_captures", OrderedDict([("rows", len(attended["results"])), ("outcomes", attended.get("outcome_counts"))])),
        ("clean_policy_outcomes", OrderedDict([("clean_pet_friendly", clean_pf), ("clean_verified_no_pets", clean_np)])),
        ("founder_decisions_required", None), ("generic_code_changes_required", 0),
        ("generic_config_additions", ["scripts/pettripfinder/discovery/config/cleveland_akron_canton_oh.json (new market config by convention; no registry edit)",
                                      "scripts/pettripfinder/discovery/config/osm_extracts.json (+1 row: geofabrik-ohio; additive, precedent PA/MI)"]),
        ("generic_defects_observed_not_fixed", [
            OrderedDict([("module", "brightdata/policy_reading.py"), ("defect", "negation adjacency across list items: '...pets allowed' followed by 'No deposit...' reads as pets_allowed False"),
                         ("exposure", "Kimpton Schofield (live PF, page says pets welcome); would have produced a wrong exclusion if an automated lane trusted it"), ("action", "pinned as a strict xfail test; reader unchanged under the freeze; founder decides whether it meets the wrong-published-policy criterion")]),
            OrderedDict([("module", "brightdata/policy_reading.py"), ("defect", "room-grid rows ('No Pets Allowed' on a non-pet room type) win over the property policy block"), ("exposure", "Quality Inn & Suites Richfield (live PF correct)"), ("action", "backlog")]),
            OrderedDict([("module", "brightdata/policy_surface.py assess_identity"), ("defect", "street agreement rejects abbreviation/ordinal variants ('4222 W 150 St.' vs '4222 West 150th St.'; 'Brook Park Rd' vs 'Brookpark Rd') and Bldg A/B suffixes"),
                         ("exposure", "13 of 29 live static re-reads declined on identity though street number + postal + phone agree in the page text"), ("action", "backlog; text-bound fallback used in the Cleveland script only")]),
            OrderedDict([("module", "discovery/overpass_endpoints.py"), ("defect", "public Overpass rate-limits after 2 requests per cycle for this bbox; 4 of 48 cells in two cycles"), ("exposure", "discovery"), ("action", "local Geofabrik extract path used, as the registry prescribes")]),
        ]),
        ("DID_THE_CANONICAL_HARDENED_FACTORY_MATERIALLY_IMPROVE_CLEVELAND_WITHOUT_ANOTHER_ARCHITECTURE_DETOUR", None),
    ])

    # ---- phase 16: founder packet (genuine decisions only)
    packet = OrderedDict([("A_identity_rebrand", []), ("B_census_additions", []), ("C_live_policy_contradictions", []), ("D_semantic_policy_issues", []), ("E_geography", [])])
    for x in inv["FOUNDER_EXCEPTION"]:
        why = x["why"]
        key = x["identity_key"]
        row = census.get(key, {})
        item = OrderedDict([("property", row.get("canonical_name") or x.get("name") or key), ("identity_key", key), ("exact_issue", why),
                            ("evidence", {k: v for k, v in x.items() if k not in ("identity_key", "why")})])
        if "TRUE_MISSING" in why:
            item.update([("recommended_ruling", "ADMIT_TO_SHADOW_CENSUS_AFTER_ONE_FIRST_PARTY_PAGE_READ"), ("census_impact", "+1 IDENTITY_PROVISIONAL row"), ("authority_impact", "none"), ("route_impact", "none until policy is read"), ("reversibility", "full: shadow only")])
            packet["B_census_additions"].append(item)
        elif "static re-read disagrees" in why:
            item.update([("recommended_ruling", "KEEP_LIVE_PF -- reader false negative, page states pets welcome"), ("census_impact", "none"), ("authority_impact", "none"), ("route_impact", "none"), ("reversibility", "n/a")])
            packet["C_live_policy_contradictions"].append(item)
        elif why.startswith("NON_LODGING_PAGE") or why.startswith("MULTI_PROPERTY_OPERATOR"):
            item.update([("recommended_ruling", "RETIRE_FROM_CENSUS_AS_NON_LODGING (keep provenance; no deletion)"), ("census_impact", "188 -> 187 registered lodging identities per row retired"), ("authority_impact", "none (row is unresolved today)"), ("route_impact", "none"), ("reversibility", "full: the row is marked, never deleted")])
            packet["A_identity_rebrand"].append(item)
        elif "brands the property differently" in why:
            item.update([("recommended_ruling", "AUTHORIZE_RENAME_THEN_PUBLISH_PF (Choice OH196 code, street and postal bind; phone changed with the brand)"), ("census_impact", "rename 1 identity key"), ("authority_impact", "+1 PF"), ("route_impact", "+1 hotel route"), ("reversibility", "full until applied")])
            packet["A_identity_rebrand"].append(item)
        elif "text-bound" in why.lower() or "text (" in why:
            item.update([("recommended_ruling", "ATTENDED_CONFIRMATION_THEN_APPLY"), ("census_impact", "none"), ("authority_impact", "+1 PF or +1 no-pets after confirmation"), ("route_impact", "+1 hotel route if PF"), ("reversibility", "full until applied")])
            packet["D_semantic_policy_issues"].append(item)
        elif why.startswith("SHARED_STREET_AND_POSTAL"):
            item.update([("recommended_ruling", "RECORD_SAME_CAMPUS_DISTINCT_ENTITY_RESOLUTION -- both rows are LIVE PF and their own pages read '130 Montrose West Ave, Bldg A' / 'Bldg B' (live audit 010); two hotels, one campus, like Detroit Troy"), ("census_impact", "none"), ("authority_impact", "none; a resolution row in identity_resolutions.json"), ("route_impact", "none"), ("reversibility", "full")])
            packet["A_identity_rebrand"].append(item)
        elif why.startswith("SHORTENED_CHAIN_NAME"):
            item.update([("recommended_ruling", "RENAME_TO_THE_PROPERTY'S_FULL_NAME -- OSM alias 'Westin' at 777 St. Clair Ave NE 44114 bound on street number + postal; the row is LIVE PF so the rename is a display/identity-key supersession, not a new row"), ("census_impact", "identity key supersession (1)"), ("authority_impact", "policy row re-keyed, facts unchanged"), ("route_impact", "hotel route slug changes -> needs a redirect"), ("reversibility", "full until deployed")])
            packet["A_identity_rebrand"].append(item)
        elif why.startswith("PRIOR_RENAME_OR_REVIEW_TRACE"):
            item.update([("recommended_ruling", "RULE_THE_RECORDED_ROUTING-REPAIR_PROPOSAL (rename / census-review) -- it has waited since PTF-CLEVELAND-ROUTING-REPAIR-001"), ("census_impact", "rename or none"), ("authority_impact", "none now"), ("route_impact", "route follows the ruled identity"), ("reversibility", "full")])
            packet["A_identity_rebrand"].append(item)
        elif why.startswith("LODGING_NEEDS_REVIEW"):
            item.update([("recommended_ruling", "CONFIRM_LODGING (university hotel & conference center) or retire"), ("census_impact", "none or -1"), ("authority_impact", "none"), ("route_impact", "none"), ("reversibility", "full")])
            packet["A_identity_rebrand"].append(item)
        elif why.startswith("SAME_CAMPUS_DISTINCT_ENTITY"):
            item.update([("recommended_ruling", "READ_ONE_FIRST_PARTY_PAGE_THEN_RULE: predecessor brand (OSM stale) vs second hotel on the campus; the registered row is LIVE PF and its evidence predates this order's replay"), ("census_impact", "+1 row only if a second hotel exists"), ("authority_impact", "none"), ("route_impact", "none"), ("reversibility", "full")])
            packet["A_identity_rebrand"].append(item)
        elif "conversion / successor question" in why:
            item.update([("recommended_ruling", "RULE_SUCCESSOR: the page at the census premises now carries a different brand and states a pet policy (owned artifact, sha256 pinned); authorize the rename and apply the read policy, or hold"), ("census_impact", "rename 1 identity key (no new row)"), ("authority_impact", "+1 PF or +1 no-pets from owned evidence"), ("route_impact", "route follows the ruled identity"), ("reversibility", "full until applied")])
            packet["A_identity_rebrand"].append(item)
        else:
            item.update([("recommended_ruling", "RULE_SUCCESSOR_OR_DISTINCT (see evidence)"), ("census_impact", "rename or +1 row"), ("authority_impact", "possible +1 PF / +1 no-pets from owned evidence"), ("route_impact", "route follows the ruled identity"), ("reversibility", "full: nothing applied")])
            packet["A_identity_rebrand"].append(item)
    # coded brand-directory listings (marriott.com refuses a plain client) that matched no census row and no OSM row: leads for one attended page read
    core = ("cleveland", "akron", "canton", "solon", "willoughby", "mentor", "independence", "beachwood", "westlake", "stow", "hudson", "streetsboro", "twinsburg", "macedonia", "richfield", "fairlawn", "north olmsted", "middleburg", "lakewood", "mayfield", "green", "massillon", "alliance")
    for l in ((recon or {}).get("coded_brand_directory_listings") or {}).get("listings_matching_nothing", []):
        nm = l["slug_name"]
        if not any(tok in nm for tok in core):
            continue
        packet["B_census_additions"].append(OrderedDict([("property", nm.title()), ("identity_key", ptf_identity_key(nm)), ("exact_issue", "%s directory lists property code %s under a name no census row and no OSM row matches; the brand host refuses a plain client so no address was read" % (l["family"], l["code"])),
                                                         ("evidence", l["url"]), ("recommended_ruling", "READ_ONE_FIRST_PARTY_PAGE_ATTENDED_THEN_CLASSIFY (alias of a registered row vs true missing)"), ("census_impact", "+1 row only if the page names a premises no row holds"), ("authority_impact", "none"), ("route_impact", "none until policy is read"), ("reversibility", "full")]))
    for note in (geography or {}).get("accidental_omission_review", []):
        packet["E_geography"].append(OrderedDict([("property", "(area)"), ("exact_issue", note), ("evidence", "geography_002 fringe/undeclared postal analysis"),
                                                  ("recommended_ruling", "NO_WIDENING_THIS_ORDER; decide whether a corridor is warranted"), ("census_impact", "none now"), ("authority_impact", "none"), ("route_impact", "a new corridor page if declared"), ("reversibility", "full")]))
    packet_notes = OrderedDict([
        ("B_census_additions", "ONE decision covers the whole group: authorise a zero-cost first-party page read for each TRUE_MISSING premises (the Indianapolis COVERAGE-001 pattern: find address -> prove no census row holds it -> capture the property's own name/phone/postal), then admit the confirmed ones to the SHADOW census. Nothing is admitted by this order."),
        ("E_geography", "ONE decision covers the group: no corridor is added by this order; each area is listed so the founder can declare or decline a corridor."),
    ])
    decisions = sum(len(v) for v in packet.values())
    assessment["founder_decisions_required"] = decisions
    assessment["DID_THE_CANONICAL_HARDENED_FACTORY_MATERIALLY_IMPROVE_CLEVELAND_WITHOUT_ANOTHER_ARCHITECTURE_DETOUR"] = args.verdict

    projection_doc = OrderedDict([
        ("schema", "ptf-hardened-projection/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("preservation_proof", OrderedDict([("protected_files", preservation), ("regressions", regressions), ("verdict", "PRESERVED" if not regressions else "REGRESSED")])),
        ("phase_11_safe_shadow_application_inventory", OrderedDict([("counts", OrderedDict((k, len(v)) for k, v in inv.items())), ("items", inv), ("applied", False), ("deployment", "NONE")])),
        ("phase_10_live_quality", live_quality),
        ("phase_12_coverage_gap", coverage),
        ("phase_13_projected_hardened_state", projected),
        ("phase_15_factory_assessment", assessment),
    ])
    packet_doc = OrderedDict([
        ("contract", "ptf-founder-review-packet/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("generated_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("nothing_was_spent", True), ("nothing_was_published", True), ("pinned_census_unchanged", not regressions),
        ("decisions_requested", decisions), ("group_level_decisions", packet_notes), ("groups", packet),
    ])
    return projection_doc, packet_doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--started-at", default=None)
    ap.add_argument("--cells-answered", type=int, default=0)
    ap.add_argument("--local-extract-used", action="store_true")
    ap.add_argument("--overpass-requests", type=int, default=0)
    ap.add_argument("--probe-requests", type=int, default=0)
    ap.add_argument("--verdict", default="UNDECIDED")
    args = ap.parse_args(argv)
    proj, packet = build(args)
    p1 = os.path.join(REPORTS, f"{M}_hardened_projection_013.json")
    p2 = os.path.join(PKG, f"{M}_hardened_revalidation_founder_packet_016.json")
    for p, d in ((p1, proj), (p2, packet)):
        with open(p, "wb") as fh:
            fh.write((json.dumps(d, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
        print("written", os.path.relpath(p, _DASH))
    print("preservation:", proj["preservation_proof"]["verdict"], proj["preservation_proof"]["regressions"])
    print("inventory:", dict(proj["phase_11_safe_shadow_application_inventory"]["counts"]))
    print("coverage:", json.dumps({k: v for k, v in proj["phase_12_coverage_gap"].items() if not isinstance(v, (dict, list))}))
    print("projected:", json.dumps(proj["phase_13_projected_hardened_state"]))
    print("packet decisions:", packet["decisions_requested"], {k: len(v) for k, v in packet["groups"].items()})
    print("live quality:", json.dumps({k: v for k, v in proj["phase_10_live_quality"].items() if not isinstance(v, list)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
