"""PTF-CANONICAL-POLICY-LOCATOR-PARITY-019 -- Phase 11.

The canonical locator contract: locate once at capture, replay exactly.

WHAT THESE TESTS ARE GUARDING
-----------------------------
Not "the two locators agree". They do not, and the measurement says they cannot
be made to: one walks DOM ancestors of a visible element, the other grows runs
of adjacent text lines, and a DOM ancestor is not a run of lines.

What is guarded is that a replay never has to ask. The boundary the locator
that RAN chose is persisted, and a replay reads it. That makes parity exact by
construction rather than by tuning two implementations towards each other.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import locator_parity_019 as LP   # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY       # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL        # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR        # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS        # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC      # noqa: E402

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
PARITY_REPORT = REPORTS / "ptf_locator_parity_019.json"

#: A document whose policy sits inside nested containers, so the boundary is a
#: real choice rather than the whole page.
DOCUMENT = """<html><body>
<div class="page"><div class="col"><h2>Amenities</h2>
<div class="pet"><h3>Pet Policy</h3>
<p>Pets are welcome. A $35 fee per night applies, maximum 2 pets per room.</p>
<p>Each pet must weigh 50 lbs or less. Service animals stay free.</p></div>
<div class="other"><p>Free parking and Wi-Fi. Rate per night: 189 USD</p></div>
</div></div></body></html>"""


def report():
    return json.loads(PARITY_REPORT.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 1-2. one contract; persisted evidence replays offline
# --------------------------------------------------------------------------- #

def test_a_capture_persists_the_boundary_its_own_locator_chose(tmp_path):
    """The static lane end to end, through the production persist function."""
    hit = UC.locate_policy_in_html(DOCUMENT)
    assert hit.found
    UC._persist(attempt_dir=tmp_path, html=DOCUMENT,
                body_text=UC.html_to_text(DOCUMENT), block_text=hit.text,
                hit=hit)
    assert (tmp_path / PL.BLOCK_ARTIFACT).is_file()
    assert (tmp_path / PL.LOCATOR_ARTIFACT).is_file()

    record = json.loads((tmp_path / PL.LOCATOR_ARTIFACT).read_text(encoding="utf-8"))
    assert record["contract"] == PL.CONTRACT
    assert record["walk"] == PL.STATIC_TEXT_WALK
    assert record["strategy"] == hit.strategy
    assert record["block_sha256"] == PL.sha256_text(hit.text)
    assert record["document_sha256"]


def test_capture_and_replay_produce_the_identical_block(tmp_path):
    """The core invariant, byte for byte, with no provider and no browser."""
    hit = UC.locate_policy_in_html(DOCUMENT)
    UC._persist(attempt_dir=tmp_path, html=DOCUMENT,
                body_text=UC.html_to_text(DOCUMENT), block_text=hit.text,
                hit=hit)

    replayed = PL.replay(tmp_path)
    assert replayed.status == PL.REPLAYED
    assert replayed.canonical is True
    parity = PL.parity(hit.text, replayed)
    assert parity["identical"] is True
    assert parity["captured_sha256"] == parity["replayed_sha256"]


def test_the_replay_needs_nothing_but_the_directory(tmp_path):
    """No network import may be reachable from the replay path."""
    import ast
    tree = ast.parse(Path(PL.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert imported <= {"__future__", "hashlib", "json", "dataclasses",
                        "pathlib", "typing"}, imported


def test_the_reader_is_reached_with_the_replayed_block_unchanged(tmp_path):
    """Locator parity is not reader correctness. Same block in, same out."""
    hit = UC.locate_policy_in_html(DOCUMENT)
    UC._persist(attempt_dir=tmp_path, html=DOCUMENT,
                body_text=UC.html_to_text(DOCUMENT), block_text=hit.text,
                hit=hit)
    replayed = PL.replay(tmp_path)
    at_capture = PR.to_extraction(PR.parse(hit.text, strategy="x"), location="")
    on_replay = PR.to_extraction(PR.parse(replayed.text, strategy="x"),
                                 location="")
    assert dict(at_capture.extraction) == dict(on_replay.extraction)
    assert dict(at_capture.extraction)["pet_fee"] == 3500


# --------------------------------------------------------------------------- #
# 3-4. the two regressions 018 found cannot recur in a new capture
# --------------------------------------------------------------------------- #

TRUNCATING_DOCUMENT = """<html><body><div class="policy">
<p>Pets are welcome. We love pets, and the pet fee is 75.00 USD per stay.</p>
<div class="facts"><span>Pet fee per night: 75 USD</span>
<span>Pet weight limit: 75</span><span>2 pets allowed</span></div>
</div></body></html>"""


def test_a_truncated_boundary_cannot_recur_because_it_is_not_recomputed(tmp_path):
    """The Crowne Plaza shape: a longer block states the fee on TWO bases, a
    shorter one states only the per-night half and looks clean. Whichever
    boundary the capture chose is the one a replay gets."""
    # The block a real capture selected, taken from the measured corpus rather
    # than approximated: it states the same $75 on TWO bases, which is exactly
    # what the shorter re-walked block loses.
    full = next(r["live_block"] for r in report()["rows"]
                if r["property_slug"] == "crowne-plaza-milwaukee-airport"
                and r["run"] == "milwaukee-router-001")
    UC._persist(attempt_dir=tmp_path, html=TRUNCATING_DOCUMENT,
                body_text=UC.html_to_text(TRUNCATING_DOCUMENT),
                block_text=full,
                hit=UC.locate_policy_in_html(TRUNCATING_DOCUMENT))

    replayed = PL.replay(tmp_path)
    assert replayed.text.strip() == full.strip()

    # the reader sees both bases in the captured block and withholds the fee
    captured_read = PR.to_extraction(PR.parse(replayed.text, strategy="x"),
                                     location="")
    assert "pet_fee" not in dict(captured_read.extraction)

    # and the SHORTER re-walked block would have published one of them, which
    # is precisely what the contract stops a replay from doing
    shorter = next(r["static_block"] for r in report()["rows"]
                   if r["property_slug"] == "crowne-plaza-milwaukee-airport"
                   and r["run"] == "milwaukee-router-001")
    rewalked_read = PR.to_extraction(PR.parse(shorter, strategy="x"),
                                     location="")
    assert dict(rewalked_read.extraction)["pet_fee"] == 7500
    assert shorter.strip() != full.strip()


def test_an_alternate_boundary_cannot_recur_either(tmp_path):
    """The avid hotels shape: two blocks, neither a superset of the other."""
    captured = ("Pets are welcome. Our Pet Policy: Dogs only. We charge 50.00 "
                "per pet, per night, except ADA Service Animals.")
    UC._persist(attempt_dir=tmp_path, html=DOCUMENT,
                body_text=UC.html_to_text(DOCUMENT), block_text=captured,
                hit=UC.locate_policy_in_html(DOCUMENT))
    replayed = PL.replay(tmp_path)
    assert replayed.text.strip() == captured
    assert replayed.canonical is True


def test_a_block_that_disagrees_with_its_record_is_never_silently_preferred(tmp_path):
    hit = UC.locate_policy_in_html(DOCUMENT)
    UC._persist(attempt_dir=tmp_path, html=DOCUMENT,
                body_text=UC.html_to_text(DOCUMENT), block_text=hit.text,
                hit=hit)
    (tmp_path / PL.BLOCK_ARTIFACT).write_text("tampered", encoding="utf-8")
    replayed = PL.replay(tmp_path)
    assert replayed.status == PL.HASH_MISMATCH
    assert replayed.canonical is False
    assert replayed.replayable is False


def test_a_capture_with_no_block_at_all_is_named_not_relocated(tmp_path):
    assert PL.replay(tmp_path).status == PL.INSUFFICIENT


def test_a_legacy_capture_replays_from_its_block_and_says_so(tmp_path):
    (tmp_path / PL.BLOCK_ARTIFACT).write_text("Pets welcome. $25 per night.",
                                              encoding="utf-8")
    replayed = PL.replay(tmp_path)
    assert replayed.status == PL.BLOCK_ONLY
    assert replayed.replayable is True
    assert replayed.canonical is False


# --------------------------------------------------------------------------- #
# 5. historical blocks are untouched
# --------------------------------------------------------------------------- #

def test_no_persisted_policy_block_was_rewritten():
    """019 measures history. It does not edit it."""
    doc = report()
    assert doc["observations_updated"] is False
    assert doc["authority_written"] is False


def test_the_parity_report_records_both_replay_paths_honestly():
    doc = report()
    paths = doc["replay_paths"]
    relocating = paths["relocating_from_saved_html"]
    canonical = paths["canonical_replay_of_the_persisted_block"]
    assert relocating["reproduces_the_captured_block"] < relocating["of"]
    assert canonical["byte_identical_replays"] == canonical["artifacts_examined"]
    # every historical capture predates the record, and says so rather than
    # being labelled as if it had been captured under the new contract
    assert set(canonical["statuses"]) == {PL.BLOCK_ONLY}


def test_the_measured_causes_are_the_ones_reported():
    doc = report()
    assert doc["artifacts_examined"] == sum(doc["causes"].values())
    assert doc["causes"].get(LP.DYNAMIC_RENDERING, 0) == 0, \
        "a dynamic-rendering loss would change what persistence must capture"


# --------------------------------------------------------------------------- #
# 6-7. routing and reader semantics are untouched
# --------------------------------------------------------------------------- #

BASELINE_COMMIT = "d627d3e"

FROZEN = (
    "scripts/pettripfinder/acquisition/routes.json",
    "scripts/pettripfinder/acquisition/providers.py",
    "scripts/pettripfinder/acquisition/registry.py",
    "scripts/pettripfinder/acquisition/router.py",
    "scripts/pettripfinder/acquisition/failures.py",
    "scripts/pettripfinder/acquisition/source_discovery.py",
    "scripts/pettripfinder/acquisition/source_selection.py",
    "scripts/pettripfinder/brightdata/policy_reading.py",
    "launch_packages/pettripfinder/markets/discovered_policy_urls/milwaukee-wi.json",
    "launch_packages/pettripfinder/markets/reports/milwaukee-wi_policy_proposals_001.json",
)


def _prefix():
    return subprocess.run(["git", "rev-parse", "--show-prefix"], cwd=REPO,
                          capture_output=True, check=True).stdout.decode().strip()


def test_routing_and_reader_files_are_untouched():
    for path in FROZEN:
        before = subprocess.run(
            ["git", "rev-parse", "--verify", "-q",
             "%s:%s%s" % (BASELINE_COMMIT, _prefix(), path)],
            cwd=REPO, capture_output=True)
        assert before.returncode == 0, path
        now = subprocess.run(["git", "hash-object", path], cwd=REPO,
                             capture_output=True, check=True).stdout
        assert before.stdout.decode().strip() == now.decode().strip(), path


def test_the_registry_still_routes_every_brand_where_016_left_it():
    expected = {"CHOICE": "firecrawl", "WYNDHAM": "firecrawl",
                "IHG": "firecrawl", "MOTEL6": "brightdata_browser",
                "RED_ROOF": "brightdata_browser"}
    for brand, provider in expected.items():
        assert REGISTRY.resolve(brand=brand,
                                url="https://example.test/").provider == provider


def test_the_locator_record_is_additive_and_the_capture_still_works_without_it(tmp_path):
    """A caller that passes no hit persists exactly what it always did."""
    hit = UC.locate_policy_in_html(DOCUMENT)
    UC._persist(attempt_dir=tmp_path, html=DOCUMENT,
                body_text=UC.html_to_text(DOCUMENT), block_text=hit.text)
    assert (tmp_path / PL.BLOCK_ARTIFACT).is_file()
    assert not (tmp_path / PL.LOCATOR_ARTIFACT).exists()


# --------------------------------------------------------------------------- #
# 8-9. gates and provenance
# --------------------------------------------------------------------------- #

def test_the_locator_contract_adds_no_identity_rule():
    """Identity is decided where it was decided. This module must not soften
    or duplicate that gate."""
    source = Path(PL.__file__).read_text(encoding="utf-8")
    for token in ("identity_confirmed", "assess_identity", "expected_name",
                  "postal_code"):
        assert token not in source, token


def test_every_quote_stays_contiguous_within_the_replayed_block(tmp_path):
    hit = UC.locate_policy_in_html(DOCUMENT)
    UC._persist(attempt_dir=tmp_path, html=DOCUMENT,
                body_text=UC.html_to_text(DOCUMENT), block_text=hit.text,
                hit=hit)
    replayed = PL.replay(tmp_path)
    result = PR.to_extraction(PR.parse(replayed.text, strategy="x"), location="")
    assert result.evidence
    for item in result.evidence:
        assert item["quote"] in replayed.text


def test_the_record_states_which_walk_and_which_visibility_rule_applied():
    """The two walks treat hidden elements differently. A replay is entitled
    to know which one produced the block it is holding."""
    live = PL.build_record(hit=PS.SurfaceHit(found=True, text="Pets welcome."),
                           block_text="Pets welcome.", document_sha256="d",
                           walk=PL.LIVE_DOM_WALK)
    static = PL.build_record(hit=PS.SurfaceHit(found=True, text="Pets welcome."),
                             block_text="Pets welcome.", document_sha256="d",
                             walk=PL.STATIC_TEXT_WALK)
    assert live["visibility_filtered"] is True
    assert static["visibility_filtered"] is False


# --------------------------------------------------------------------------- #
# 10-12. proof, authority, publication
# --------------------------------------------------------------------------- #

def test_the_offline_proof_covers_every_static_lane(tmp_path):
    """Firecrawl, the Web Unlocker and Spider all persist through the same
    function, so proving it once proves it for the three of them."""
    import ast
    for module in ("scripts/pettripfinder/acquisition/firecrawl_capture.py",
                   "scripts/pettripfinder/acquisition/spider_capture.py"):
        source = Path(REPO / module).read_text(encoding="utf-8")
        calls = [n for n in ast.walk(ast.parse(source))
                 if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "_persist"]
        assert calls, module
        for call in calls:
            assert "hit" in {k.arg for k in call.keywords}, module


def test_the_live_lane_passes_its_hit_through_too():
    import ast
    source = (REPO / "scripts/pettripfinder/brightdata/cross_brand_capture.py"
              ).read_text(encoding="utf-8")
    calls = [n for n in ast.walk(ast.parse(source))
             if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr == "_persist"]
    assert calls
    for call in calls:
        assert "hit" in {k.arg for k in call.keywords}


def test_no_milwaukee_policy_authority_exists():
    found = list((REPO / "launch_packages" / "pettripfinder")
                 .rglob("*hotel_policy_facts*milwaukee*"))
    assert not found, found


def test_nothing_was_published():
    doc = report()
    assert doc["published"] is False
    assert doc["provider_calls"] == 0
