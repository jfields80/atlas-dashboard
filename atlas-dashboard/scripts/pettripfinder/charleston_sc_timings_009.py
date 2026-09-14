"""PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001 -- the measured wall-clock facts of this run (UTC), recorded as observed."""
from __future__ import annotations

from collections import OrderedDict

TIMINGS = OrderedDict([
    ("CHARLESTON_START_TIMESTAMP", "2026-09-14T14:08:03Z (2026-09-14T10:08:03-04:00)"),
    ("precheck_and_template_read", "14:08Z-14:18Z (worktree, branch, HEAD 6825851b = the Atlanta-live release, tree clean; "
                                   "Savannah / Atlanta / Outer Banks / Greenville shadow chains and the Savannah browser "
                                   "transcript read)"),
    ("geography", "14:18:45Z (14 corridors: 7 CORE / 4 CORRIDOR / 3 FRINGE, 36 admitted ZIPs; Kiawah / Seabrook refused by "
                  "municipality inside 29455 and preserved for kiawah-seabrook-sc)"),
    ("census_lanes", "OSM lane 164.4 s (South Carolina extract, hard link of the Charlotte run's 2026-09-10 snapshot; 393 "
                     "elements); brand inventory about 15 min detached (Marriott SC sitemap page, 18 Hilton city pages + 27 "
                     "sub-pages, 16 family sitemap probes); Charleston Area CVB roster 21.2 s plain client (109 listings)"),
    ("identity", "14:41Z-15:00Z (census reconciliation passes, rulings: vacation-rental / timeshare / resort-component / "
                 "component-of; same-campus guard)"),
    ("routing", "Wyndham property service 6.4 s (25 routes: 13 read, 12 retired); static lane 8.7 s (94 targets)"),
    ("browser_evidence", "14:31Z-14:41Z attended same-origin reads: IHG 17, Hyatt 8, Choice 32, Marriott 34, Hilton 41, "
                         "Best Western 8, Red Roof 2; Extended Stay America 5 at 14:55Z (every committed payload's "
                         "canonical-JSON sha256 verified against the page's)"),
    ("static_evidence", "policy-page lane 32.3 s / 35.8 s / 40.0 s over three passes (63 / 81 / 88 sites)"),
    ("policy_adjudication", "14:45Z-15:00Z (candidate quotes tested against the shared first-party reader; independent "
                            "quotes proved verbatim with house number and ZIP on the same document)"),
    ("reconciliation", "15:00Z (clean set 82 / 44, staged authority, final partition 185 identities, 0 contract issues)"),
    ("shadow_package_and_fast", "15:01:29Z-15:03:21Z at 3b3d1271 (sealed twice in-process, FAST 15/15, determinism "
                                "BYTE_IDENTICAL)"),
    ("independent_reproduction", "15:04:09Z-15:04:31Z (clean git worktree at 3b3d1271 with a COPY of the document store: "
                                 "geography, brand pages, capture, census, clean set, staged authority, partition and staged "
                                 "shard rebuilt from committed captures -- zero content difference; only the eol-unattributed "
                                 "discovery config checks out CRLF; separate-process digest-only seal = the same digest)"),
    ("ZERO_TO_SOURCE_READY", "55 min 18 s (14:08:03Z -> 15:03:21Z, the FAST-passed sealed shadow package)"),
    ("peak_memory", "not measured on this run"),
])
