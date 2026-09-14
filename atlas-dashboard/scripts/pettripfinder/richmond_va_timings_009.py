"""PTF-RICHMOND-VA-PARALLEL-SOURCE-READY-001 -- the measured wall-clock facts of this run (UTC), recorded as observed."""
from __future__ import annotations

from collections import OrderedDict

TIMINGS = OrderedDict([
    ("RICHMOND_START_TIMESTAMP", "2026-09-14T15:53:55Z (2026-09-14T11:53:55-04:00)"),
    ("precheck_and_template_read", "15:53Z-16:02Z (worktree, branch, HEAD 6825851b = the Atlanta-live release, tree clean; "
                                   "the Charleston SC shadow chain @a33266bd and its browser transcript read; Virginia "
                                   "Geofabrik extract downloaded)"),
    ("geography", "16:02:34Z (12 corridors: 9 CORE / 3 CORRIDOR / 0 FRINGE, 43 admitted ZIPs; Petersburg / Colonial Heights "
                  "/ Hopewell preserved for petersburg-tri-cities-va)"),
    ("census_lanes", "OSM lane 380.9 s (Virginia extract, 246 elements); brand inventory about 12 min detached (Marriott VA "
                     "sitemap page, 21 Hilton city pages + 29 sub-pages, 16 family sitemap probes); Visit Richmond VA "
                     "listing service one call (200 lodging listings, plain client)"),
    ("routing", "Wyndham property service 10.9 s (40 routes: 20 read, 19 retired, 1 error); static lane 63.4 s (84 "
                "targets); policy-page lane 22.6 s (38 sites, 140 pages)"),
    ("browser_evidence", "16:12Z-16:40Z attended same-origin reads: IHG 22, Hyatt 6, Hilton 33, Marriott 40, Choice 57 (22 "
                         "served, then a 403 wall), Best Western 20, Red Roof 9, Extended Stay America 7, Omni 1, InTown "
                         "Suites 2 (every committed payload's canonical-JSON sha256 verified against the page's)"),
    ("identity", "16:20Z-16:40Z (census passes; roster-listing bindings, brand-route refusal, non-hotel rulings, third-party "
                 "JSON-LD refusal, map-row fold beside a read)"),
    ("policy_adjudication", "16:25Z-16:40Z (candidate quotes tested against the shared first-party reader; independent "
                            "quotes proved verbatim with house number and ZIP on the same document)"),
    ("reconciliation", "16:38Z-16:42Z (clean set 89 / 45, staged authority, final partition 196 identities, 0 contract "
                       "issues; inputs committed at e5f1ea44)"),
    ("shadow_package_and_fast", "16:47:39Z-16:49:19Z at 6f587cc6 (sealed twice in-process, FAST 15/15, determinism "
                                "BYTE_IDENTICAL, 89.6 s); an earlier seal at e5f1ea44 (16:43:10Z-16:45:02Z, pkg 9dd5d52e) also "
                                "passed 15/15 and was superseded when the census stopped dropping the WoodSpring Suites Richmond "
                                "West own-site identity (a same-host brand-page read had suppressed it)"),
    ("independent_reproduction", "16:48:10Z-16:49:46Z (clean git worktree at 6f587cc6 with a COPY of the document store: "
                                 "geography, brand pages, capture, census, clean set, staged authority, partition and staged "
                                 "shard rebuilt from committed captures -- zero content difference; only the eol-unattributed "
                                 "discovery config checks out CRLF; separate-process digest-only seal = the same digest)"),
    ("ZERO_TO_SOURCE_READY", "55 min 24 s (15:53:55Z -> 16:49:19Z, the final FAST-passed sealed shadow package; the first "
                             "FAST-passed seal was at 16:45:02Z, 51 min 7 s)"),
    ("peak_memory", "not measured on this run"),
])
