# ATLAS-THROUGHPUT-005 — final participation proof

The Cincinnati / Toledo failure: a pre-flip artifact can never authorize a post-flip release.

| measure | value |
|---|---|
| pre-flip candidate digest | sha256:a22f1c5123eeb3bf4 |
| post-flip candidate digest | sha256:25b69be224b34ff42 |
| digests differ | True |
| bundles differ | True |
| pre-flip markets | 9 |
| post-flip markets | 10 |
| pre-flip authorization accepts the final candidate | False |
| final membership inside the hashed bytes | True |
| pre-flip gates failing | release.parent_routes_preserved |

The pre-flip candidate is staged from a participation record in which `dayton-oh` is source-ready but not
founder-authorized, so it does not contain that market at all, and its live-route gate fails — correctly. It
exists to be compared, never to be released.
