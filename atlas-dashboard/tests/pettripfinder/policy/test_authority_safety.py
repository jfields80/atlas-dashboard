"""PTF-POLICY-P0-001 -- structural proof that the policy layer cannot publish.

The most important guarantee in this work order is a negative one: an
observation may never become a published fact by itself. A comment saying so
is worth nothing, so this module proves it three ways -- the package declares
no writer, it never imports a promotion path, and the authority files are
byte-identical after the whole suite has run.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

POLICY_PKG = Path(__file__).resolve().parents[3] / "scripts" / "pettripfinder" / "policy"
LAUNCH = Path(__file__).resolve().parents[3] / "launch_packages" / "pettripfinder"

PROTECTED = (
    "hotel_policy_facts.json",
    "hotel_exclusions.json",
    "identity_resolutions.json",
    "seed_businesses.csv",
    "markets/columbus-oh.json",
    "markets/cleveland-akron-canton-oh.json",
)

#: Modules whose presence in an import list would mean the policy layer can
#: reach a promotion or publication path.
FORBIDDEN_IMPORTS = (
    "export_hotel_policy_facts",
    "promote_attested_candidates",
    "promote_worker_candidates",
    "publication_guard",
    "assemble_netlify_bundle",
    "generate_pettripfinder_columbus_site",
)


def policy_modules():
    return sorted(POLICY_PKG.rglob("*.py"))


def test_the_policy_package_exists_and_has_modules():
    assert len(policy_modules()) >= 6


@pytest.mark.parametrize("path", policy_modules(), ids=lambda p: p.name)
def test_no_module_imports_a_promotion_or_publication_path(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    for forbidden in FORBIDDEN_IMPORTS:
        assert not any(forbidden in name for name in imported), (
            "%s imports %r; the policy observation layer must have no path to "
            "publication" % (path.name, forbidden))


@pytest.mark.parametrize("path", policy_modules(), ids=lambda p: p.name)
def test_no_module_opens_a_file_for_writing(path):
    """The layer is pure: it never writes. A write call here would be the
    first step toward an observation mutating authority."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "attr", None) or getattr(func, "id", None)
            if name in ("write_text", "write_bytes", "unlink", "mkdir", "rmtree"):
                raise AssertionError(
                    "%s calls %s(); the policy layer writes nothing" % (path.name, name))
            if name == "open":
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant) \
                            and "w" in str(kw.value.value):
                        raise AssertionError("%s opens a file for writing" % path.name)
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) \
                        and "w" in str(node.args[1].value):
                    raise AssertionError("%s opens a file for writing" % path.name)


def test_protected_authority_is_unchanged_by_importing_and_running_the_layer():
    """Import every policy module, exercise the main entry points, and assert
    the authority files did not move a byte."""
    before = {rel: hashlib.sha256((LAUNCH / rel).read_bytes()).hexdigest()
              for rel in PROTECTED}

    from scripts.pettripfinder.policy import (  # noqa: F401
        evidence_bundle, policy_membrane, policy_observation, readiness,
        worker_bridge,
    )
    from scripts.pettripfinder.policy.adapters import drury
    from scripts.pettripfinder.policy.pilots import sonesta

    obs = drury.observe(
        text="Dogs and cats accepted. A daily fee of $50 per room applies.",
        hotel_ref={"market_id": "columbus-oh", "canonical_name": "Sample Inn",
                   "normalized_name": "sample inn"},
        source_url="https://example.test/sample", obs_id="o1",
        observed_at="2026-08-08", retrieved_at="2026-08-08T00:00:00Z",
        name_on_page="Sample Inn")
    policy_membrane.evaluate(obs)
    readiness.derive([obs])
    sonesta.plan(sonesta.build_targets([{"canonical_name": "Sonesta Sample"}],
                                       market_id="columbus-oh"))

    after = {rel: hashlib.sha256((LAUNCH / rel).read_bytes()).hexdigest()
             for rel in PROTECTED}
    assert before == after, "the policy layer moved a protected authority file"


def test_published_columbus_count_is_still_83():
    from scripts.pettripfinder.site_data import load_published_hotel_policy_facts
    assert len(load_published_hotel_policy_facts()) == 83


def test_cleveland_identities_remain_policy_not_verified():
    import json
    census = (Path(__file__).resolve().parents[3] / "data" / "worker_runs"
              / "pettripfinder" / "discovery" / "review_batches"
              / "cleveland-akron-canton-007" / "identity_census_v5.json")
    if not census.exists():          # operational corpus is gitignored
        pytest.skip("Cleveland census artifact absent in this checkout")
    hotels = json.loads(census.read_text(encoding="utf-8"))["hotels"]
    assert len(hotels) == 193
    assert {h.get("policy_state") for h in hotels} == {"POLICY_NOT_VERIFIED"}
