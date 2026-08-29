"""Reconcile a market's PRIOR build against its rebuilt census -- row by row.

WHY THIS EXISTS
---------------
A rebuild (``census_recandidacy`` + ``census_projection``) answers "what is the
market?" and records, per candidate, what kept it out or let it in. It does not
answer the question the founder asks next: "what happened to every hotel the
OLD build had?" -- and it must not answer "what does the old build's authority
say?", because prior authority is carried by a human, never by a rebuild.

This reads the prior census, the new census, the candidate ledger the rebuild
wrote and the recandidacy absorption record, and classifies every prior row
exactly once:

    MATCHED_EXISTING          the prior identity is in the new census under the
                              same identity key (directly, or absorbed into a
                              fresh discovery hit whose name yields that key)
    RENAMED_REBRANDED         absorbed into a fresh hit at the same street whose
                              name yields a DIFFERENT key -- the building is in
                              the census under a new name
    DUPLICATE                 the rebuild absorbed the prior row into another
                              identity by coordinate/name containment
    OUT_OF_CURRENT_GEOGRAPHY  the prior row's postal code is claimed by no
                              corridor and no corridor names it explicitly
    UNRESOLVED_IDENTITY       held by the rebuild: identity-key collision, no
                              locality, no name, or not lodging

and adds three independent flags that say what the prior build still OFFERS:

    USEFUL_SOURCE_URL         the prior row carried a property-page URL (not a
                              brand index or a city search) -- evidence a URL
                              recovery can bind
    USEFUL_POLICY_EVIDENCE    a prior capture/review artifact holds an entry for
                              this identity -- evidence a founder can re-read
    PRIOR_AUTHORITY_MATCH     the prior policy package publishes this identity;
                              the founder decides whether that authority
                              stands, the factory only reports the match

Nothing here writes to the census, the routing, or any authority. Pure,
offline, deterministic.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder.discovery import census_projection as CP        # noqa: E402
from scripts.pettripfinder.discovery import census_recandidacy as CR       # noqa: E402

SCHEMA = "ptf-prior-build-reconciliation/1.0"

MATCHED_EXISTING = "MATCHED_EXISTING"
RENAMED_REBRANDED = "RENAMED_REBRANDED"
DUPLICATE = "DUPLICATE"
OUT_OF_CURRENT_GEOGRAPHY = "OUT_OF_CURRENT_GEOGRAPHY"
UNRESOLVED_IDENTITY = "UNRESOLVED_IDENTITY"
CLASSIFICATIONS = (MATCHED_EXISTING, RENAMED_REBRANDED, DUPLICATE,
                   OUT_OF_CURRENT_GEOGRAPHY, UNRESOLVED_IDENTITY)

USEFUL_SOURCE_URL = "USEFUL_SOURCE_URL"
USEFUL_POLICY_EVIDENCE = "USEFUL_POLICY_EVIDENCE"
PRIOR_AUTHORITY_MATCH = "PRIOR_AUTHORITY_MATCH"
FLAGS = (USEFUL_SOURCE_URL, USEFUL_POLICY_EVIDENCE, PRIOR_AUTHORITY_MATCH)

_UNRESOLVED_DISPOSITIONS = frozenset({
    CP.IDENTITY_COLLISION, CP.NO_LOCALITY, CP.UNNAMED, CP.NOT_LODGING,
})
_GEOGRAPHY_DISPOSITIONS = frozenset({
    CP.OUT_OF_MARKET_GEOGRAPHY, CP.OUT_OF_MARKET_BOUNDARY_DECISION,
})


def _load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _url_is_property_page(url: str) -> bool:
    if not url:
        return False
    try:
        from scripts.pettripfinder.acquisition import market_routing as MR
        return MR.classify_url_shape(url) == getattr(MR, "SHAPE_PROPERTY_PAGE", "PROPERTY_PAGE")
    except Exception:  # noqa: BLE001 -- the shape classifier is advisory here
        return True


def identity_keys_in_artifacts(paths: Iterable[Path]) -> Dict[str, List[str]]:
    """``identity_key -> [artifact paths naming it]`` -- what prior evidence exists."""
    out: Dict[str, Set[str]] = {}
    for path in paths:
        try:
            document = _load(path)
        except (ValueError, OSError):
            continue
        stack: List = [document]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                key = str(node.get("identity_key") or "")
                if not key and isinstance(node.get("hotel_ref"), dict):
                    key = str(node["hotel_ref"].get("identity_key") or "")
                if key:
                    out.setdefault(key, set()).add(Path(path).as_posix())
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    return {k: sorted(v) for k, v in out.items()}


def published_identity_keys(policy_package: Optional[Mapping]) -> Set[str]:
    """Identity keys the prior policy package publishes -- reported, never carried."""
    if not policy_package:
        return set()
    keys: Set[str] = set()
    rows = policy_package.get("hotels") or policy_package.get("records") or []
    for row in rows:
        key = str(row.get("identity_key") or "")
        if not key and row.get("hotel_name"):
            key = ptf_identity_key(str(row["hotel_name"]))
        if not key and row.get("canonical_name"):
            key = ptf_identity_key(str(row["canonical_name"]))
        if key:
            keys.add(key)
    return keys


def reconcile(*, prior_census: Mapping, new_census: Mapping,
              candidate_ledger: Mapping, absorptions: Mapping,
              policy_package: Optional[Mapping] = None,
              evidence_artifacts: Sequence[Path] = (),
              work_order: str = "") -> Dict:
    new_rows = {r["identity_key"]: r for r in new_census.get("hotels") or ()}
    alias_to_new: Dict[str, str] = {}
    for key, row in new_rows.items():
        for alias in row.get("prior_census_identity_keys") or ():
            alias_to_new.setdefault(alias, key)
    ledger_by_cid = {e.get("candidate_id"): e
                     for e in candidate_ledger.get("candidates") or ()}
    absorbed_into = {a.get("absorbed_candidate_id"): a
                     for a in absorptions.get("absorptions") or ()}
    evidence = identity_keys_in_artifacts(evidence_artifacts)
    published = published_identity_keys(policy_package)

    rows: List[Dict] = []
    for prior in prior_census.get("hotels") or ():
        key = str(prior.get("identity_key") or "")
        cid = CR.candidate_id_for(key)
        entry: Dict = OrderedDict((
            ("identity_key", key),
            ("canonical_name", prior.get("canonical_name", "")),
            ("postal_code", prior.get("postal_code", "")),
            ("prior_corridor", prior.get("corridor", "")),
        ))
        new_key = ""
        classification = ""
        why = ""
        absorbed = absorbed_into.get(cid)
        if absorbed is not None:
            host_name = str(absorbed.get("surviving_name")
                            or absorbed.get("into_name") or "")
            host_entry = ledger_by_cid.get(absorbed.get("into_candidate_id")) or {}
            host_key = str(host_entry.get("identity_key") or "") or ptf_identity_key(host_name)
            if host_key in new_rows:
                new_key = host_key
            elif alias_to_new.get(key) in new_rows:
                new_key = alias_to_new[key]
            if new_key:
                if new_key == key:
                    classification, why = MATCHED_EXISTING, (
                        "absorbed by street into fresh discovery '%s', whose name "
                        "yields the same identity key" % host_name)
                else:
                    classification, why = RENAMED_REBRANDED, (
                        "absorbed by street into fresh discovery '%s'; the "
                        "building is in the new census as '%s'" % (host_name, new_key))
            else:
                host_entry = ledger_by_cid.get(absorbed.get("into_candidate_id")) or {}
                disposition = str(host_entry.get("disposition") or "")
                if disposition in _GEOGRAPHY_DISPOSITIONS:
                    classification = OUT_OF_CURRENT_GEOGRAPHY
                elif disposition == CP.ABSORBED:
                    classification = DUPLICATE
                else:
                    classification = UNRESOLVED_IDENTITY
                why = ("absorbed by street into fresh discovery '%s', which the "
                       "rebuild then dispositioned %s" % (host_name, disposition or "?"))
        else:
            ledger_entry = ledger_by_cid.get(cid) or {}
            disposition = str(ledger_entry.get("disposition") or "")
            admitted_key = str(ledger_entry.get("identity_key") or key)
            if disposition == CP.ADMITTED and admitted_key in new_rows:
                new_key = admitted_key
                classification, why = MATCHED_EXISTING, (
                    "the prior row survived on its own evidence and is in the "
                    "new census under its own key")
            elif disposition == CP.ABSORBED:
                classification = DUPLICATE
                why = str(ledger_entry.get("why") or "")
                into = ptf_identity_key(str(ledger_entry.get("absorbed_into_name") or ""))
                new_key = into if into in new_rows else ""
            elif disposition in _GEOGRAPHY_DISPOSITIONS:
                classification, why = OUT_OF_CURRENT_GEOGRAPHY, str(ledger_entry.get("why") or "")
            elif disposition in _UNRESOLVED_DISPOSITIONS:
                classification = UNRESOLVED_IDENTITY
                why = "%s: %s" % (disposition, ledger_entry.get("why") or "")
            elif key in new_rows:
                new_key = key
                classification, why = MATCHED_EXISTING, (
                    "present in the new census under the same key")
            else:
                classification = UNRESOLVED_IDENTITY
                why = ("the prior row is not in the candidate ledger and not in the "
                       "new census (disposition %r)" % disposition)
        entry["classification"] = classification
        entry["why"] = why
        entry["new_identity_key"] = new_key
        prior_url = str(prior.get("official_url") or "").strip()
        entry["prior_official_url"] = prior_url
        flags: List[str] = []
        if prior_url and _url_is_property_page(prior_url):
            flags.append(USEFUL_SOURCE_URL)
        if key in evidence:
            flags.append(USEFUL_POLICY_EVIDENCE)
        if key in published:
            flags.append(PRIOR_AUTHORITY_MATCH)
        entry["flags"] = flags
        entry["evidence_artifacts"] = evidence.get(key, [])
        entry["new_census_url"] = str(new_rows.get(new_key, {}).get("official_url") or "") if new_key else ""
        rows.append(entry)

    counts = Counter(r["classification"] for r in rows)
    flag_counts = Counter(f for r in rows for f in r["flags"])
    authority_unmatched = sorted(k for k in published
                                 if not any(r["identity_key"] == k and r["new_identity_key"]
                                            for r in rows))
    prior_keys = {r["identity_key"] for r in rows}
    newly_discovered = sorted(k for k, row in new_rows.items()
                              if k not in prior_keys
                              and not any(a in prior_keys for a in
                                          row.get("prior_census_identity_keys") or ()))
    return OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is", "Every row of the prior census classified exactly once "
                         "against the rebuilt census, with what the prior build "
                         "still offers. Prior authority is REPORTED as a match, "
                         "never carried."),
        ("market_id", new_census.get("market_id", "")),
        ("work_order", work_order),
        ("prior_census_work_order", prior_census.get("work_order", "")),
        ("prior_rows", len(rows)),
        ("new_census_rows", len(new_rows)),
        ("classification_counts", OrderedDict((c, counts.get(c, 0)) for c in CLASSIFICATIONS)),
        ("flag_counts", OrderedDict((f, flag_counts.get(f, 0)) for f in FLAGS)),
        ("prior_identities_matched", counts.get(MATCHED_EXISTING, 0) + counts.get(RENAMED_REBRANDED, 0)),
        ("prior_authority_published", len(published)),
        ("prior_authority_matched", len(published) - len(authority_unmatched)),
        ("prior_authority_unmatched", authority_unmatched),
        ("newly_discovered_identities", len(newly_discovered)),
        ("newly_discovered_identity_keys", newly_discovered),
        ("rows", rows),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prior-census", required=True)
    parser.add_argument("--new-census", required=True)
    parser.add_argument("--candidate-ledger", required=True)
    parser.add_argument("--absorptions", required=True,
                        help="the ptf-census-recandidacy document")
    parser.add_argument("--policy-package", default="",
                        help="the prior market policy package; matches are reported, never carried")
    parser.add_argument("--evidence-artifact", action="append", default=[],
                        help="prior capture/review artifacts naming identity keys; globs expanded")
    parser.add_argument("--work-order", default="")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    artifacts: List[Path] = []
    for pattern in args.evidence_artifact:
        artifacts.extend(Path(p) for p in sorted(glob.glob(pattern, recursive=True)))
    document = reconcile(
        prior_census=_load(args.prior_census), new_census=_load(args.new_census),
        candidate_ledger=_load(args.candidate_ledger), absorptions=_load(args.absorptions),
        policy_package=_load(args.policy_package) if args.policy_package else None,
        evidence_artifacts=artifacts, work_order=args.work_order)
    document["inputs"] = OrderedDict((
        ("prior_census", args.prior_census), ("new_census", args.new_census),
        ("candidate_ledger", args.candidate_ledger), ("absorptions", args.absorptions),
        ("policy_package", args.policy_package),
        ("evidence_artifacts", [p.as_posix() for p in artifacts]),
    ))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("prior rows            : %d" % document["prior_rows"])
    for name, value in document["classification_counts"].items():
        print("  %-26s: %d" % (name, value))
    for name, value in document["flag_counts"].items():
        print("  %-26s: %d" % (name, value))
    print("prior authority       : %d published, %d matched"
          % (document["prior_authority_published"], document["prior_authority_matched"]))
    print("newly discovered      : %d" % document["newly_discovered_identities"])
    print("written               : %s" % out.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
