"""PTF-BREWDOG-PROMOTION-001 -- the reviewed same-campus exception is opt-in,
so this test makes forgetting it a test failure rather than a deleted business.

``listing_dataset_builder`` is pure: it cannot read the resolution authority
itself, so every caller that feeds it the REAL seed authority has to pass
``distinct_entity_groups``. A caller that forgets does not crash and does not
warn -- it silently merges two reviewed businesses back into one and drops the
loser's listing, route and images. That is exactly how the BrewDog taproom
disappeared from a 71-hotel build, with twelve broken links as the only symptom.

The rule enforced here is deliberately narrow:

  * a call whose ``seed_businesses`` comes from the real launch package or the
    tracked seed CSV MUST pass ``distinct_entity_groups``;
  * a call built from synthetic rows (a literal list) is exempt -- unit fixtures
    that exercise the dedup rule itself must be free to omit it;
  * nothing here changes the builder's default. Same-address records still
    deduplicate unless one exact, valid, reviewed resolution covers the group.
"""

from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SEARCH_ROOTS = ("scripts", "tests", "services", "engines", "repositories")

CALL = "build_listing_dataset("
REQUIRED_ARG = "distinct_entity_groups"

#: How a file proves it reads the real seed authority rather than fixtures.
AUTHORITY_MARKERS = ("load_launch_package", "seed_businesses.csv")

#: Expressions that name real seed rows at a call site.
AUTHORITY_SEED_EXPRESSIONS = (
    'seed_businesses=package["seed_businesses"]',
    "seed_businesses=seed,",
    "seed_businesses=seed_rows,",
)


def _call_text(source: str, start: int) -> str:
    """The full parenthesised call beginning at ``start``."""
    i = source.index("(", start)
    depth, j = 0, i
    while j < len(source):
        if source[j] == "(":
            depth += 1
        elif source[j] == ")":
            depth -= 1
            if depth == 0:
                return source[i:j + 1]
        j += 1
    raise AssertionError("unbalanced call at offset %d" % start)


#: This module names the call and the markers in its own constants, so it would
#: otherwise inventory itself.
_SELF = pathlib.Path(__file__).resolve()


def _python_files():
    for root in SEARCH_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if path.resolve() != _SELF:
                yield path


def _authority_aware_call_sites():
    """(path, line, call_text) for every call fed by the real seed authority."""
    sites = []
    for path in _python_files():
        source = path.read_text(encoding="utf-8", errors="replace")
        if CALL not in source:
            continue
        if not any(marker in source for marker in AUTHORITY_MARKERS):
            continue                      # fixture-only module
        for match in re.finditer(re.escape(CALL), source):
            if source[:match.start()].rstrip().endswith("def"):
                continue                  # the definition itself
            text = _call_text(source, match.start())
            normalized = " ".join(text.split())
            if not any(expr.rstrip(",") in normalized for expr in AUTHORITY_SEED_EXPRESSIONS):
                continue                  # synthetic rows at an otherwise real-seed module
            line = source[:match.start()].count("\n") + 1
            sites.append((path.relative_to(REPO_ROOT).as_posix(), line, normalized))
    return sites


def test_the_inventory_finds_the_known_authority_aware_callers():
    """A guard that silently matches nothing guards nothing."""
    found = {path for path, _line, _text in _authority_aware_call_sites()}
    expected = {
        "scripts/generate_pettripfinder_columbus_site.py",
        "scripts/generate_pettripfinder_pilot.py",
        "scripts/promote_import_candidates.py",
        "tests/pettripfinder/test_listing_renderability_boundary.py",
        "tests/website_generation/integration/test_pettripfinder_demo_media.py",
        "tests/website_generation/integration/test_pettripfinder_launch_package.py",
    }
    assert expected <= found, "stopped seeing known call sites: %s" % sorted(expected - found)


def test_every_authority_aware_caller_passes_the_reviewed_resolutions():
    missing = [(path, line) for path, line, text in _authority_aware_call_sites()
               if REQUIRED_ARG not in text]
    assert not missing, (
        "build_listing_dataset is called with the real seed authority but without "
        "distinct_entity_groups at %s. Without it a reviewed same-campus pair is "
        "merged and one real business loses its listing and route. Pass "
        "publication_guard.distinct_entity_groups()." % missing)


def test_a_fixture_only_caller_is_not_required_to_pass_them():
    """The exemption is real and intentional: the dedup rule's own unit tests
    build synthetic rows and must be able to observe the default behaviour."""
    fixture_module = REPO_ROOT / "tests" / "pettripfinder" / "test_listing_dataset_builder.py"
    source = fixture_module.read_text(encoding="utf-8")
    assert CALL in source
    assert not any(marker in source for marker in AUTHORITY_MARKERS)
    assert fixture_module.relative_to(REPO_ROOT).as_posix() not in {
        path for path, _l, _t in _authority_aware_call_sites()}
