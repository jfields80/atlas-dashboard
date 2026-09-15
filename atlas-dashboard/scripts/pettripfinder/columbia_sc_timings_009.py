"""PTF-COLUMBIA-SC-PARALLEL-SOURCE-READY-001 -- the measured wall-clock facts of this run (UTC), recorded as observed."""
from __future__ import annotations

from collections import OrderedDict

TIMINGS = OrderedDict([
    ("COLUMBIA_START_TIMESTAMP", "2026-09-15T00:18:26Z (recorded by the first command of the run)"),
    ("precheck_and_template_read", "00:18Z-00:25Z (worktree, branch, HEAD 6825851b, tree clean; the Hampton Roads VA shadow chain "
                                   "@87249b80 read and cloned by name; its browser capture JS extracted from its transcript by a "
                                   "read-only helper agent; the 2026-09-10 South Carolina Geofabrik extract copied from the "
                                   "Charleston worktree)"),
    ("geography", "00:27:25Z (13 corridors: 10 CORE / 1 CORRIDOR / 2 FRINGE, 24 admitted ZIPs; West Columbia's PO-box ZIP 29171 "
                  "added at 00:52Z for 25 after Marriott's own page printed it)"),
    ("census_lanes", "OSM lane 207.3 s (South Carolina extract, 157 elements); brand inventory about 24 min detached (Marriott SC "
                     "sitemap page, 10 Hilton city pages + 42 sub-pages, 16 family sitemap probes); Experience Columbia SC "
                     "listing service (plain client, 116 lodging listings) at 00:31Z"),
    ("routing", "Wyndham property service 10.6 s (34 routes: 19 read, 15 retired); static lane 31.0 s (40 targets); policy-page "
                "lane 5.0 s (10 sites, 49 pages)"),
    ("browser_evidence", "00:33Z-00:52Z attended same-origin reads: IHG 13, Marriott 30, Hilton 33, Choice 26 (no 403 wall), "
                         "Hyatt 2, Best Western 8, Red Roof 2, Extended Stay America 4, Motel 6 / Studio 6 4, stayAPT 1, "
                         "Historic Stays of Columbia 1 (JavaScript refused on the domain; page text read); every committed brand "
                         "payload's canonical-JSON sha256 verified against the page's"),
    ("identity", "00:45Z-00:58Z (census passes; municipality safety; Fort Jackson military rule; rental-apartment, campground and "
                 "non-hotel rulings; competitor gap challenge)"),
    ("policy_adjudication", "00:50Z-00:58Z (candidate quotes tested against the shared first-party reader; independent quotes "
                            "proved verbatim with house number and ZIP on the same document)"),
    ("reconciliation", "00:58Z-00:59Z (clean set 64 / 42, staged authority, final partition 125 identities, 0 contract issues; "
                       "inputs committed at fe2d1b6a)"),
    ("shadow_package_and_fast", "00:59Z dry-run seal (digest only, not written); 01:00:48Z-01:02:53Z at fe2d1b6a, pkg dcc24295, "
                                "FAST 15/15, determinism BYTE_IDENTICAL, first-party gate 106/106"),
    ("independent_reproduction", "01:04:10Z-01:04:37Z (clean git worktree at fe2d1b6a with a COPY of the document store: "
                                 "geography, brand pages, capture, census, clean set, staged authority, partition and staged "
                                 "shard rebuilt from committed captures -- zero content difference; the eol-unattributed "
                                 "discovery config checks out CRLF but the rebuilt file equals the committed blob byte for byte; "
                                 "separate-process digest-only seal = the same digest)"),
    ("ZERO_TO_SOURCE_READY", "44 min 27 s (00:18:26Z -> 01:02:53Z, the FAST-passed sealed shadow package; reproduction confirmed "
                             "at 01:04:37Z, 46 min 11 s)"),
    ("peak_memory", "not measured on this run"),
])
