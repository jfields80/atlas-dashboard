"""PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001 -- the measured wall-clock facts of this run (UTC), recorded as observed."""
from __future__ import annotations

from collections import OrderedDict

TIMINGS = OrderedDict([
    ("HAMPTON_ROADS_START_TIMESTAMP", "2026-09-14T21:24:42Z (the order's first transmission; the complete order arrived a few "
                                      "minutes later and the clock was not restarted)"),
    ("precheck_and_template_read", "21:24Z-22:10Z (worktree, branch, HEAD 6825851b, tree clean; the Richmond VA shadow chain "
                                   "@82c8ea46 and its browser transcript read; chain cloned by name; Virginia Geofabrik extract "
                                   "re-used from the same-day Richmond download)"),
    ("geography", "22:13:34Z (17 corridors: 14 CORE / 1 CORRIDOR / 2 FRINGE, 63 admitted ZIPs; 23463 added at 22:48Z for 64; "
                  "Williamsburg / historic Yorktown preserved for williamsburg-va)"),
    ("census_lanes", "OSM lane 367.8 s (Virginia extract, 480 elements); brand inventory about 30 min detached (Marriott VA "
                     "sitemap page, 14 Hilton city pages + 103 sub-pages, 16 family sitemap probes); Visit Chesapeake and Visit "
                     "Newport News listing services (plain client) and the Visit Virginia Beach CRM listing API (attended "
                     "browser, 1,268 listings, 165 accommodations)"),
    ("routing", "Wyndham property service 17.8 s (68 routes: 34 read, 34 retired); static lane 49.6 s (113 targets); policy-page "
                "lane 35.6 s (57 sites, 167 pages)"),
    ("browser_evidence", "22:15Z-23:00Z attended same-origin reads: IHG 25, Hyatt 7, Choice 31 (30 served, then a 403 wall; one "
                         "more on a second pass), Best Western 10, Marriott 50, Hilton 42, Red Roof 12, Extended Stay America 8, "
                         "independents 3 sites (others refused navigation or TLS); every committed brand payload's "
                         "canonical-JSON sha256 verified against the page's"),
    ("identity", "22:45Z-23:06Z (census passes; municipality safety; military, timeshare, condo and non-hotel rulings; Choice "
                 "wall routes; roster-listing binding; competitor gap challenge)"),
    ("policy_adjudication", "22:50Z-23:00Z (candidate quotes tested against the shared first-party reader; independent quotes "
                            "proved verbatim with house number and ZIP on the same document)"),
    ("reconciliation", "23:00Z-23:02Z (clean set 94 / 72, staged authority, final partition 264 identities, 0 contract issues; "
                       "inputs committed at ceaf8efb)"),
    ("shadow_package_and_fast", "23:02:38Z-23:04:46Z at ceaf8efb (first FAST 15/15, pkg 71981771, superseded); 23:07:10Z-"
                                "23:08:39Z at 4503d568 (pkg 6592a381, superseded: its committed staged census copy was stale); "
                                "final 23:09:5xZ-23:11:20Z at d38797e6, pkg 27d17072, FAST 15/15, determinism BYTE_IDENTICAL"),
    ("independent_reproduction", "23:11:34Z-23:11:59Z (clean git worktree at d38797e6 with a COPY of the document store: "
                                 "geography, brand pages, capture, census, clean set, staged authority, partition and staged "
                                 "shard rebuilt from committed captures -- zero content difference; only the eol-unattributed "
                                 "discovery config checks out CRLF; separate-process digest-only seal = the same digest)"),
    ("ZERO_TO_SOURCE_READY", "1 h 46 min 38 s (21:24:42Z -> 23:11:20Z, the final FAST-passed sealed shadow package; the first "
                             "FAST-passed seal was at 23:04:46Z, 1 h 40 min 4 s)"),
    ("peak_memory", "not measured on this run"),
])
