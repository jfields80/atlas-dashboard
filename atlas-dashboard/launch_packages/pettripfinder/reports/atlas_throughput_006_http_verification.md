# ATLAS-THROUGHPUT-006 — live HTTP verification and the host adapter

005 defined nine post-activation checks and ran them against staged bytes. 006 supplies the HTTP client that
asks a real origin, and the host adapter that speaks the deployment host's actual semantics.

**A timeout is UNKNOWN.** Not a pass, not a failure, and never grounds for a rollback until the host has been
reconciled. Treating an unknown as either is how a good release gets rolled back or a bad one gets kept.

## The host, read from this repository

| property | value |
|---|---|
| site | pettripfinder-prod |
| site id source | NETLIFY_SITE_ID at deploy time, never a committed .netlify/state.json |
| deploy command | netlify deploy --prod --no-build --dir <candidate>/site --site <site> |
| why --no-build | without it the CLI runs a git build and uploads nothing from --dir |
| deploy id | 24 hex characters |
| per-deploy URL | https://<deploy-id>--<site>.netlify.app |
| rollback | restore an earlier deploy |
| side effect | the CLI scaffolds a gitignored .netlify/ that fails the assembler gate |

Upload and publish are ONE operation for `--prod`: the host offers no separate activate step to hold, which is
why the coordinator's parent guard runs immediately before the call. Rollback is "publish an earlier deploy",
not "undo" — which is why 005 keeps the previous release in durable storage rather than trusting the host to
remember it.

The adapter is constructed **disabled** and refuses every mutating command in that state, while still
returning the exact command it would run so the plan stays reviewable.
