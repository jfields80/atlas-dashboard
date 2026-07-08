# Developer Guide — Directory Data Ingestion & Seeding Engine

Audience: anyone extending the ingestion subsystem. Read
`directory_ingestion_engine.md` first for the architecture.

## Ground rules (frozen Atlas contract)

1. Engines are pure: no I/O, no SQL, no Flask, no wall clock, no randomness.
2. All SQL lives in `DirectoryIngestionRepository`. Nowhere else.
3. Business logic lives in engines and the service. Never in the repository.
4. Every model is a frozen dataclass. Mutation = `dataclasses.replace`.
5. Every scoring number is a named module-level constant with a comment.
6. Any behavior change bumps `ENGINE_VERSION` in `ingestion_models.py`
   and gets registered with the Engine Version Registry at integration time.

## Common extension tasks

### Add a source vocabulary (new CSV/dataset shape)

Don't touch the normalizer logic — add keys to the mapping profile, or
supply a custom profile per source:

```python
from engines.directory_ingestion import FieldMapping, DEFAULT_MAPPING_PROFILE, ListingNormalizer

odh_profile = DEFAULT_MAPPING_PROFILE + (
    # already-covered fields are found first; append only NEW source keys
)
# or a fully custom profile for a weird source:
custom = tuple(
    FieldMapping(m.atlas_field, m.source_keys + ("facility_nm",))
    if m.atlas_field == "business_name" else m
    for m in DEFAULT_MAPPING_PROFILE
)
normalizer = ListingNormalizer(mapping_profile=custom)
```

Mapping profiles are data, not code — keep them declarative so future
tooling can store them per-source in the database.

### Add a canonical field

1. Add the field to `NormalizedListing` (TaggedValue for optional text).
2. Add a `FieldMapping` entry with candidate source keys.
3. Add a normalizer function if the value needs cleaning.
4. Add the column to `models/directory_ingestion_schema.sql` and both row
   mappers in the repository (`_listing_to_row`, `_row_to_listing`).
5. Decide whether it participates in completeness weights
   (`_COMPLETENESS_FIELDS` — keep the weights summing to 100).
6. Add round-trip coverage in `TestRepository`.

### Tune duplicate detection

All knobs are constants at the top of `duplicate_detector.py`:
signal weights (must sum to 1.0), `DUPLICATE_THRESHOLD`,
`AUTO_MERGE_THRESHOLD`, geo radii, name stopwords. Never tune inline —
change the constant, add a test that pins the new behavior, bump the
engine version.

Adding a new signal: compute similarity in `_score_pair`, give it a named
weight, rebalance the others, and (if it can find pairs the current
blocks miss) add a blocking key in `_blocked_pairs`.

### Add a quality dimension

`QualityScore` is frozen — adding a dimension is a model change:
extend the dataclass, add a `_dimension` method with named point
constants, rebalance `_W_*` weights to 100, extend the schema table and
repository mapper, and update `TestQualityEngine.test_all_dimensions_bounded`.

### Add an enrichment rule

Append a `(task_type, priority, rule_fn)` entry to `_RULES` in
`enrichment_generator.py`. Rules return a rationale string (task fires)
or `None` (skip). New task types go in `EnrichmentTaskType`. Rule order
is part of the contract — append, don't reorder.

### Implement a future provider (later phase — NOT 3B)

Subclass the reserved interface in `extension_points.py`:

```python
class RealGooglePlacesProvider(GooglePlacesProvider):
    def capabilities(self) -> ProviderCapabilities: ...
    def fetch(self, blueprint, limit) -> list[RawListing]: ...
```

Providers return **raw** payloads verbatim — no cleaning inside the
provider (the normalizer owns cleaning, so the raw record remains an
honest audit artifact). Providers never write to the database.
LLM enrichment providers must tag every proposed value ESTIMATED.

## Testing conventions

* All tests offline; fixtures are in-file sample datasets.
* Every id-producing function gets a determinism test.
* Every threshold change gets a test pinning behavior on both sides.
* Repository changes require a full round-trip equality test
  (frozen dataclass `==` makes this cheap).

## Debugging tips

* `QualityScore.explanations` names every earned/missed point bucket.
* `DuplicatePair.matched_signals` shows why two listings paired.
* `IngestionResult.rejected_raw_ids` lists records dropped at
  normalization (currently only: no recoverable business name).
* Replays: if `run_ingestion` returns `replayed=True`, the identical
  package already exists — check `di_ingestion_runs.package_id`.
