# ATLAS-THROUGHPUT-005 — performance

| measure | seconds unless stated |
|---|---|
| parent load | 0.0 |
| membership resolution | 0.0 |
| fragments (9 inherited + 1 validated bundle) | 76.623 |
| compose | 16.139 |
| gates | 76.043 |
| FAST release safety lane | 5.517 |
| candidate staged, total | 178.044 |
| live verification (targeted) | 0.022 |
| release store on disk (bytes) | 25745403 |
| bundles reused | 9 |
| bundles rebuilt | 0 |

The comparison that matters: a whole-site compose of every market costs **547.4 s**; staging a data-only
candidate that inherits the unchanged markets costs **178.044 s**, and the deployable identity is computed the
same way in both cases (`bundle_digest(file_hashes(site))`). Integrity was never weakened to reach it: every
inherited fragment is extracted from a content-addressed object and the composed candidate is re-hashed
before it can be authorized.
