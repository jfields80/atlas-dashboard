# PetTripFinder Columbus — Netlify Credential Contract

**PETTRIPFINDER-PROD-005A.** Names only. This document deliberately contains **no
credential values** and never will.

## Credentials used (names only)

| Name | Purpose | Where it lives | Where it must NEVER live |
|---|---|---|---|
| `NETLIFY_AUTH_TOKEN` | Authenticates the Netlify CLI for a remote deploy stage. | The operator's shell **environment variable**, or a browser login session. | Git, `netlify.toml`, `_headers`/`_redirects`, any script literal, chat, logs, tests, reports, `.netlify/state.json`. |
| `NETLIFY_SITE_ID` | Selects the target Netlify site for `netlify deploy --site`. | The operator's shell **environment variable**. | Same as above. |

Both are supplied **only as environment variables** at the separately authorized
remote stage (PROD-005B and later). They are **not** read, required, or referenced
by any Stage-A code: `scripts/pettripfinder/assemble_netlify_bundle.py` performs
no network activity and reads no credential.

## Rules

1. **Never paste values into chat.** The operator provides them as environment
   variables; Claude never asks for, prints, or echoes the values.
2. **Never print values.** Any tooling that must confirm a credential reports
   **presence/absence only** (e.g. `NETLIFY_SITE_ID is set` — never the value).
3. **Never commit values.** No credential appears in Git history, tracked files,
   `netlify.toml`, or example commands. Command examples use the literal
   `"$NETLIFY_SITE_ID"` / `"$NETLIFY_AUTH_TOKEN"` env-var references, never a
   literal token or ID.
4. **Never persist local link state.** Do **not** create or commit
   `.netlify/state.json`. Project selection is done at deploy time via the
   `NETLIFY_SITE_ID` env var. `.netlify/` is gitignored.
5. **Redact values from errors and subprocess output.** If the CLI ever emits a
   token or ID in an error, redact it before it reaches logs, reports, or chat.
6. **Read credentials only during separately authorized remote stages.** No
   credential is read during local assembly (Stage A).

## Presence check (no values)

At a future authorized remote stage, credential availability is confirmed by
presence only. Illustrative (do **not** run in Stage A):

```sh
# Reports presence/absence ONLY — never the value.
test -n "$NETLIFY_SITE_ID"    && echo "NETLIFY_SITE_ID: set"    || echo "NETLIFY_SITE_ID: MISSING"
test -n "$NETLIFY_AUTH_TOKEN" && echo "NETLIFY_AUTH_TOKEN: set" || echo "NETLIFY_AUTH_TOKEN: MISSING"
```

## Browser login alternative

Instead of exposing a personal-access token via `NETLIFY_AUTH_TOKEN`, the operator
may authenticate the CLI through an interactive browser login (`netlify login`),
which stores a session outside the repository. This avoids handling a raw token
value at all.

**Stage A installs nothing and authenticates nothing.** Both the token path and
the browser-login path are future, separately gated actions (PROD-005B onward).
