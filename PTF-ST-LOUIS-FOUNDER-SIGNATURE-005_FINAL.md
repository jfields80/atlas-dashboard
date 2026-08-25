# PTF-ST-LOUIS-FOUNDER-SIGNATURE-005 — Founder Signature, FINAL

**Market:** `st-louis-mo` **Branch:** `feature/ptf-st-louis-market-001`
**Start HEAD:** `8911ea7`
**Offline only — zero provider calls, zero spend, zero re-fetches.**
**NOT REGISTERED. NOT PUBLISHED. NOT DEPLOYED.**

---

## A. Pre-signature verification

| Check | Result |
|---|---|
| HEAD = `8911ea7` | ✔ |
| Working tree clean | ✔ |
| Exactly 122 candidates | ✔ |
| Exactly 114 in clean signable dispositions | ✔ 76 + 38 |
| Exactly 8 outside this pass | ✔ 1 change + 7 hold |
| No attestation already on any row | ✔ 0 of 122 |

## B. What was signed

| | |
|---|---|
| **Total signed** | **114** |
| Signed pet-friendly | **76** |
| Signed verified-no-pets | **38** |
| Unsigned / excluded | **8** |
| Authority created | **114** (76 + 38) |

**Founder identifier: `jfields80`.** Derived from the repository, not guessed —
362 `reviewer_id` and 249 `decided_by` records across six markets carry it, and
it is the identity of this repository's owner.

**Decision value: `APPROVED_AFTER_CURRENT_REVIEW`**, resolved through
`contracts.founder_approval` (`founder-approval-vocabulary/1.0`) and checked with
`assert_writable`. No new vocabulary was introduced. This is the canonical value
by measurement: 333 of 336 committed approval records carry it, `APPROVED` is
already a registered legacy synonym mapping *to* it, and five markets' publication
validators compare against it literally.

## C. Two things I did differently from a literal reading of the order

**The attestation is not in the packet.** The work order says to write the
founder fields "for each of those 114 rows". Writing them into
`st_louis_mo_founder_review_packet_004.json` would put a human signature
somewhere an idempotent builder erases on its next run — PTF-DAYTON-
RECERTIFICATION-001 hit exactly this and wrote the rule: *"A human attestation
must not live somewhere a regeneration can erase."*

So the signature lives in `st_louis_mo_founder_decisions_005.json`, a separate
non-regenerable ledger, and the packet stays regenerable and unsigned. A test
asserts both. Every signed row carries `founder_decision`,
`founder_reviewer_id` and `founder_reviewed_at` exactly as required — in the
file that can hold them safely.

**The decider and the transcriber are separate fields.** `decided_by:
jfields80` is the founder's ruling. `recorded_by` names me as the agent that
transcribed it, in words, and the ledger carries the authorization verbatim.
This is Dayton's committed pattern, and it exists because PTF-POLICY-SCHEMA-
MIGRATION-001 Phase F once wrote 26 approvals under a founder's name for records
the founder had never seen — every fact source-backed, every hash verified, and
the defect purely the signature. No technical gate catches that, because no gate
checks who a name belongs to.

I signed here because the standing rule's own condition was met: the founder
authorised it **explicitly, in this conversation, scoped by name and count**.
The ledger records that authorisation so anyone reading it later can check the
same thing.

## D. Authority — 114, and not registered

`st_louis_mo_proposed_authority_005.json` — 76 pet-friendly, 38
verified-no-pets, 0 unresolved.

**It is deliberately not a shard.** `market_authority.registered_shard_ids()`
lists `markets/authority/` to decide which markets exist and *raises* on a shard
whose market has no contract. Creating `markets/authority/st-louis-mo/` would
therefore break the global build that the live deployment manifest pins — the
PTF-047 coupling. The artifact carries the same shape the shards use, so
promotion later is a move plus a market contract, not a rewrite.

`build_global_authority --check` still reports **8 source markets, 277 routes,
102 exclusions, 369 seed rows, build marker `241ce93c…`** — byte-identical.
A test asserts the shard directory does not exist.

**Every citation survived.** Each authority row carries its evidence quotes,
source URL, snapshot hash, authority tier, capture method, reader provenance,
publication grade, membrane verdict, **withheld fields and non-inferences**.
Withheld fields are carried forward, not dropped: "not stated" is a fact about
the source, and an authority row that silently loses it is how a blank becomes
an implied zero. A test checks the carried set against the observation store.

Each signed row is **bound** to the semantic hash and snapshot hash the founder
was shown. The authority builder refuses any row whose record changed after
signing — a test drives that path.

## E. The 8 unsigned rows

| Row | Disposition | Waiting on |
|---|---|---|
| comfort inn collinsville near st louis | HOLD | founder policy question — does a stated per-pet price constitute a stated allowance? |
| super 8 by wyndham troy il st louis area | HOLD | same question |
| sonesta es suites st louis chesterfield | HOLD | same question |
| comfort inn pacific st louis | HOLD | identity judgement — the page says *"Comfort Inn Near Six Flags"*; a rename, street and telephone agree |
| days inn and suites pontoon beach | HOLD | identity judgement — the page names less than the record (`& Suites` absent) |
| travelodge st louis airport | HOLD | identity judgement — the page names less than the record (`Airport` absent) |
| wingate at wyndham | HOLD | identity judgement — the census name is a bare chain word |
| hampton | APPROVE_WITH_CHANGE | name authorisation: `Hampton` → `Hampton Inn Collinsville` |

Three need one policy answer; four need identity judgements; one needs a name
authorisation. **None needs another provider call.**

## F. Reconciliation — 357 exactly

| | |
|---|---|
| Census identities | 357 |
| Closure rows | 357 |
| Missing | **0** |
| Foreign | **0** |
| Duplicate | **0** |

| Closure state | Count |
|---|---|
| HELD_REVIEW | 122 → **114 signed + 8 unsigned** |
| ACCESS_UNRESOLVED | 153 |
| INSUFFICIENT_EVIDENCE | 66 |
| POLICY_NOT_FOUND | 16 |
| **Total** | **357** |

114 + 8 + 235 = **357**. The signed set and the authority set are the same set —
asserted, not assumed.

## G. Tests

**28 new**, in `tests/pettripfinder/test_founder_signature_005.py`. The ones
that matter are the refusals: a HOLD row is never signed, an already-signed row
is never re-signed, a missing `decided_by`/`decided_at`/`authorization` stops the
run, an unreviewed candidate stops the whole run, an unsigned row can never
become authority, a non-publishing decision can never become authority, and a
record that changed after signing is refused.

| Chunk | Result |
|---|---|
| founder / authority / St. Louis / closure / policy / contracts | 902 passed, 1 skipped |
| `tests/pettripfinder/acquisition` | **134 failed — byte-identical to the measured baseline**, zero new, zero fixed |
| rest of `tests/pettripfinder` | 3 failed (pre-existing Indianapolis), 5600 passed |
| `tests/website_generation` | 3412 passed, 5 skipped |
| all other packages + top level | 3325 passed, 14 skipped |

The acquisition baseline was **measured** at `7f421bb` in work order 004 by
stashing under a unique tag and restoring by SHA — not assumed. This pass's
failure list was diffed against it and is identical.

## H. Status

```
ST. LOUIS CENSUS COMPLETE            = YES
ST. LOUIS ACTIVE CLOSURE COMPLETE    = YES
ST. LOUIS FOUNDER SIGNATURE COMPLETE = YES  (for the 114 authorised; 8 by design)
ST. LOUIS AUTHORITY CREATED          = YES  (114, proposed, unregistered)
ST. LOUIS SIGNED PET_FRIENDLY        = 76
ST. LOUIS SIGNED VERIFIED_NO_PETS    = 38
ST. LOUIS UNSIGNED REVIEW ROWS       = 8

ST. LOUIS REGISTERED = FALSE
ST. LOUIS PUBLISHED  = FALSE
ST. LOUIS DEPLOYED   = FALSE
```

Measurement is disabled and zero affiliates are enrolled — unchanged.
