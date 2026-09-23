# -*- coding: utf-8 -*-
"""PTF-FAST-NONEMPTY-BUNDLE-GUARD-001 -- FAST rule J must prove the changed
market PRODUCED a bundle, and rule K must never claim determinism from two
empty ones.

Measured before this order: a relative ``--work`` path made the assembler
write under ``<stage>/<work>/<output>`` while the collector read
``<work>/<output>/site``; the bundle collected zero files (sha256 of the empty
string), rule J read PASS and rule K read BYTE_IDENTICAL over two identically
empty bundles -- every rule PASS, ELIGIBLE YES.

The lane cases run the REAL lane over the sealed Dayton withdrawal package
(the ATLAS-THROUGHPUT-003 fixture) with synthetic builders, so no production
assembly runs. The path cases run the REAL ``package_staging.build_changed_market``
-- overlay, output-path resolution and collector -- with only staging, the
contract and the page renderer stubbed. No market name is special-cased.
"""

from __future__ import annotations

import hashlib
import inspect
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.pettripfinder import assemble_netlify_bundle as ANB
from scripts.pettripfinder import assembly_session_cache as ASC
from scripts.pettripfinder import atlas_throughput_003_pilot as PILOT
from scripts.pettripfinder import fast_release_lane as FL
from scripts.pettripfinder import first_party_binding as FPB
from scripts.pettripfinder import market_package_writer as W
from scripts.pettripfinder import package_staging as STAGING
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder.assemble_production_site import bundle_digest
from scripts.pettripfinder.markets import contract as MARKET_CONTRACT

SEALED_AT = "2026-09-08T00:00:00Z"
VALIDATED_AT = FPB.parse_timestamp("2026-09-08T12:00:00Z")
EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

SITE = {"index.html": "<html>a</html>", "hotels/x/index.html": "<html>x</html>", "sitemap.xml": "<urlset/>"}
SITE_B = dict(SITE, **{"index.html": "<html>b</html>"})
NO_HTML = {"sitemap.xml": "<urlset/>", "robots.txt": "User-agent: *"}


@pytest.fixture(scope="module")
def live():
    return RI.live_index()


@pytest.fixture(scope="module")
def package(live):
    return W.build_sealed_package(PILOT.withdrawal_inputs(live), sealed_at=SEALED_AT)


def _build_result(package, context, cold, files, *, output_present=True):
    hashes = OrderedDict((k, hashlib.sha256(v.encode("utf-8")).hexdigest()) for k, v in sorted(files.items()))
    return OrderedDict((("market_id", package["market_id"]), ("package_id", package["package_id"]),
                        ("context", context), ("cold", cold), ("staged_files", {}),
                        ("staged_input_digest", "sha256:" + "5" * 64), ("contract_sha256", "sha256:" + "6" * 64),
                        ("bundle_sha256", bundle_digest(hashes)), ("file_count", len(hashes)),
                        ("html_count", sum(1 for k in hashes if k.endswith(".html"))),
                        ("output_present", output_present), ("release_name", "x"), ("gates_failing", []),
                        ("cache_events", [OrderedDict((("verdict", "BUILD_EXECUTED"), ("assembly_kind", "market_bundle"),
                                                       ("input_key", "k"), ("seconds", 1.0)))]),
                        ("seconds", 1.0)))


def _builder(monkeypatch, *bundles, output_present=True):
    """Patch the lane's builder: call N returns ``bundles[N]`` (the last repeats)."""
    calls = []

    def build(package, stage_root, output_root, *, context="production", cold=True, repo_root=None):
        calls.append(str(output_root))
        files = bundles[min(len(calls), len(bundles)) - 1]
        return _build_result(package, context, cold, files, output_present=output_present if files else False)
    monkeypatch.setattr(STAGING, "build_changed_market", build)
    return calls


def _lane(package, live, work, **kw):
    return FL.run_fast_lane(package, work_dir=work, live=live, now=VALIDATED_AT, **kw)


def _stable(rule_result):
    return OrderedDict((k, v) for k, v in rule_result.items() if k != "seconds")


# --------------------------------------------------------------------------- #
# The contract: bundle_output_defects.
# --------------------------------------------------------------------------- #

class TestTheOutputContract:
    def test_the_empty_bundle_identity_is_the_sha256_of_nothing(self):
        assert FL.EMPTY_BUNDLE_SHA256 == EMPTY_SHA == bundle_digest(OrderedDict())

    def test_a_meaningful_bundle_has_no_defects(self):
        assert FL.bundle_output_defects({"file_count": 3, "html_count": 2, "bundle_sha256": "a" * 64,
                                         "output_present": True}) == []

    def test_zero_files_is_an_empty_bundle(self):
        codes = [d.split(":")[0] for d in FL.bundle_output_defects(
            {"file_count": 0, "html_count": 0, "bundle_sha256": EMPTY_SHA, "output_present": True})]
        assert codes == [FL.EMPTY_BUNDLE, FL.NO_HTML_OUTPUT]

    def test_files_without_html_is_no_html_output(self):
        assert [d.split(":")[0] for d in FL.bundle_output_defects(
            {"file_count": 2, "html_count": 0, "bundle_sha256": "a" * 64})] == [FL.NO_HTML_OUTPUT]

    def test_an_absent_output_root_is_missing_build_output(self):
        codes = [d.split(":")[0] for d in FL.bundle_output_defects(
            {"file_count": 0, "html_count": 0, "bundle_sha256": EMPTY_SHA, "output_present": False})]
        assert codes == [FL.MISSING_BUILD_OUTPUT, FL.EMPTY_BUNDLE, FL.NO_HTML_OUTPUT]

    def test_the_empty_digest_is_empty_whatever_count_is_claimed(self):
        assert [d.split(":")[0] for d in FL.bundle_output_defects(
            {"file_count": 5, "html_count": 5, "bundle_sha256": "sha256:" + EMPTY_SHA})] == [FL.EMPTY_BUNDLE]

    @pytest.mark.parametrize("count", [None, "3", 3.0, True, -1])
    def test_a_count_that_is_not_a_positive_integer_fails_closed(self, count):
        codes = [d.split(":")[0] for d in FL.bundle_output_defects(
            {"file_count": count, "html_count": count, "bundle_sha256": "a" * 64})]
        assert codes == [FL.EMPTY_BUNDLE, FL.NO_HTML_OUTPUT]

    def test_a_cached_bundle_without_an_html_count_is_judged_on_its_files(self):
        assert FL.bundle_output_defects({"file_count": 2, "bundle_sha256": "a" * 64}, require_html=False) == []
        assert FL.bundle_output_defects({"file_count": 0, "bundle_sha256": EMPTY_SHA},
                                        require_html=False)[0].startswith(FL.EMPTY_BUNDLE)

    def test_the_diagnostics_are_deterministic(self):
        build = {"file_count": 0, "html_count": 0, "bundle_sha256": EMPTY_SHA, "output_present": False}
        assert FL.bundle_output_defects(build) == FL.bundle_output_defects(dict(build))

    def test_no_market_is_special_cased(self):
        source = inspect.getsource(FL.bundle_output_defects) + inspect.getsource(FL._k_blocked_by_j)
        assert "market_id" not in source and "palm" not in source.lower()


# --------------------------------------------------------------------------- #
# The lane: rule J fails closed, rule K is not eligible after it.
# --------------------------------------------------------------------------- #

class TestTheLane:
    def test_1_a_zero_file_bundle_fails_rule_j(self, package, live, tmp_path, monkeypatch):
        calls = _builder(monkeypatch, {})
        receipt = _lane(package, live, tmp_path)
        j = receipt["RESULTS"]["J"]
        assert j["status"] == FL.FAIL
        assert j["detail"]["file_count"] == 0 and j["detail"]["bundle_sha256"] == EMPTY_SHA
        assert FL.EMPTY_BUNDLE in j["detail"]["output_defects"]
        assert any(p.startswith(FL.EMPTY_BUNDLE) for p in j["problems"])
        assert len(calls) == 1                                      # no second build to "prove" it
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.NO

    def test_2_a_bundle_with_no_html_fails_rule_j(self, package, live, tmp_path, monkeypatch):
        _builder(monkeypatch, NO_HTML)
        receipt = _lane(package, live, tmp_path)
        j = receipt["RESULTS"]["J"]
        assert j["status"] == FL.FAIL and j["detail"]["file_count"] == 2
        assert j["detail"]["output_defects"] == [FL.NO_HTML_OUTPUT]
        assert receipt["RESULTS"]["K"]["status"] == FL.UNKNOWN
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.NO

    def test_5_two_empty_builds_never_satisfy_determinism(self, package, live, tmp_path, monkeypatch):
        _builder(monkeypatch, {}, {})
        receipt = _lane(package, live, tmp_path)
        k = receipt["RESULTS"]["K"]
        assert receipt["RESULTS"]["J"]["status"] == FL.FAIL
        assert k["status"] == FL.UNKNOWN and k["detail"]["blocked_by"] == "J"
        assert receipt["DETERMINISM_RESULT"] != "BYTE_IDENTICAL"
        assert receipt["UNKNOWN_RULES"] == ["K"] and receipt["FAILED_RULES"] == ["J"]
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.NO

    def test_6_a_valid_non_empty_bundle_passes_rule_j(self, package, live, tmp_path, monkeypatch):
        _builder(monkeypatch, SITE)
        receipt = _lane(package, live, tmp_path, determinism=False)
        j = receipt["RESULTS"]["J"]
        assert j["status"] == FL.PASS, j["problems"]
        assert (j["detail"]["file_count"], j["detail"]["html_count"]) == (3, 2)
        assert j["detail"]["output_present"] is True and j["detail"]["output_defects"] == []

    def test_7_two_identical_non_empty_builds_are_deterministic(self, package, live, tmp_path, monkeypatch):
        calls = _builder(monkeypatch, SITE, SITE)
        receipt = _lane(package, live, tmp_path)
        k = receipt["RESULTS"]["K"]
        assert len(calls) == 2
        assert receipt["RESULTS"]["J"]["status"] == FL.PASS
        assert k["status"] == FL.PASS and k["detail"]["result"] == "BYTE_IDENTICAL"
        assert k["detail"]["output_digest_a"] == k["detail"]["output_digest_b"] != EMPTY_SHA
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES

    def test_8_two_differing_builds_fail_determinism(self, package, live, tmp_path, monkeypatch):
        _builder(monkeypatch, SITE, SITE_B)
        receipt = _lane(package, live, tmp_path)
        assert receipt["RESULTS"]["J"]["status"] == FL.PASS
        assert receipt["RESULTS"]["K"]["status"] == FL.FAIL
        assert receipt["DETERMINISM_RESULT"] == "DIFFERENT"

    def test_an_empty_second_build_fails_determinism_with_its_own_diagnostic(self, package, live, tmp_path, monkeypatch):
        _builder(monkeypatch, SITE, {})
        receipt = _lane(package, live, tmp_path)
        k = receipt["RESULTS"]["K"]
        assert k["status"] == FL.FAIL
        assert any(p.startswith("second build: %s" % FL.MISSING_BUILD_OUTPUT) for p in k["problems"])
        assert any(p.startswith("second build: %s" % FL.EMPTY_BUNDLE) for p in k["problems"])

    def test_9_the_empty_bundle_diagnostics_are_deterministic(self, package, live, tmp_path, monkeypatch):
        _builder(monkeypatch, {})
        first = _lane(package, live, tmp_path / "a")
        second = _lane(package, live, tmp_path / "b")
        for rule in ("J", "K"):
            a, b = _stable(first["RESULTS"][rule]), _stable(second["RESULTS"][rule])
            if rule == "J":
                a["detail"].pop("build_seconds"), b["detail"].pop("build_seconds")
            assert a == b, rule

    def test_a_cached_empty_bundle_cannot_pass_j_or_inherit_determinism(self, package, live, tmp_path):
        class EmptyCache:
            def build_or_reuse(self, package, **kw):
                return OrderedDict((("cache_status", "HIT"), ("build_input_key", "sha256:" + "1" * 64),
                                    ("bundle_sha256", EMPTY_SHA), ("file_count", 0), ("receipt_digest", "r"),
                                    ("builder_invocations", 0), ("trust_state", "TRUSTED")))

            def read_receipt(self, digest):
                return {"results": {"determinism": {"result": "BYTE_IDENTICAL"}}}
        receipt = _lane(package, live, tmp_path, bundle_cache=EmptyCache())
        assert receipt["RESULTS"]["J"]["status"] == FL.FAIL
        assert receipt["RESULTS"]["J"]["detail"]["output_defects"] == [FL.EMPTY_BUNDLE]
        assert receipt["RESULTS"]["K"]["status"] == FL.UNKNOWN
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.NO


# --------------------------------------------------------------------------- #
# The path regression: the real staged build, a relative vs absolute --work.
# --------------------------------------------------------------------------- #

@pytest.fixture
def stub_render(monkeypatch):
    """The real ``build_changed_market`` (overlay, output-path resolution,
    collector) with staging, the contract and the renderer stubbed. The stub
    renderer resolves its output exactly as the assembler does and writes a
    tiny site there -- unless told to write nothing."""
    state = {"write": True, "written": []}

    def stage(package, stage_root, repo_root=None):
        Path(stage_root).mkdir(parents=True, exist_ok=True)
        return OrderedDict((("stub", "sha256:" + "7" * 64),))

    def assemble(context, output, contract=None, market=None):
        out_root = ANB.validate_output_path(output)
        if state["write"]:
            site = out_root / "site"
            site.mkdir(parents=True, exist_ok=True)
            (site / "index.html").write_text("<html>stub</html>", encoding="utf-8")
            (site / "sitemap.xml").write_text("<urlset/>", encoding="utf-8")
            state["written"].append(site.resolve())
        ASC.EVENTS.append({"verdict": "BUILD_EXECUTED", "assembly_kind": "market_bundle",
                           "input_key": "stub", "seconds": 0.0})
        return {"release_name": "stub", "gates": {}}

    monkeypatch.setattr(STAGING, "stage_package", stage)
    monkeypatch.setattr(STAGING, "derive_staged_contract", lambda package, stage_root, repo_root=None: {"stub": True})
    monkeypatch.setattr(MARKET_CONTRACT, "parse_market", lambda doc, source=None: doc)
    monkeypatch.setattr(ANB, "assemble", assemble)
    return state


class TestTheWorkPath:
    def test_3_a_build_that_writes_no_output_root_fails_rule_j(self, package, live, tmp_path, stub_render):
        stub_render["write"] = False
        receipt = _lane(package, live, tmp_path / "w")
        j = receipt["RESULTS"]["J"]
        assert j["status"] == FL.FAIL
        assert j["detail"]["output_present"] is False
        assert j["detail"]["output_defects"] == [FL.MISSING_BUILD_OUTPUT, FL.EMPTY_BUNDLE, FL.NO_HTML_OUTPUT]
        assert receipt["RESULTS"]["K"]["status"] == FL.UNKNOWN

    def test_4_a_relative_work_path_that_collects_nothing_is_refused(self, package, live, tmp_path,
                                                                      stub_render, monkeypatch):
        monkeypatch.chdir(tmp_path)
        receipt = _lane(package, live, Path("data") / "fast_work" / "w")
        j, k = receipt["RESULTS"]["J"], receipt["RESULTS"]["K"]
        # The measured defect class: the assembler joined the work path twice ...
        written = stub_render["written"][0]
        assert written == (tmp_path / "data/fast_work/w/sa/data/fast_work/w/oa/site").resolve()
        # ... so the collector, reading <work>/oa/site, saw nothing -- and FAST now says so.
        assert j["detail"]["file_count"] == 0 and j["detail"]["bundle_sha256"] == EMPTY_SHA
        assert j["status"] == FL.FAIL
        assert j["detail"]["output_defects"] == [FL.MISSING_BUILD_OUTPUT, FL.EMPTY_BUNDLE, FL.NO_HTML_OUTPUT]
        assert k["status"] == FL.UNKNOWN and k["detail"]["blocked_by"] == "J"
        assert receipt["DETERMINISM_RESULT"] != "BYTE_IDENTICAL"
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.NO

    def test_an_absolute_work_path_builds_and_proves_determinism(self, package, live, tmp_path, stub_render):
        receipt = _lane(package, live, tmp_path / "w")
        j, k = receipt["RESULTS"]["J"], receipt["RESULTS"]["K"]
        assert stub_render["written"][0] == (tmp_path / "w" / "oa" / "site").resolve()
        assert j["status"] == FL.PASS, j["problems"]
        assert (j["detail"]["file_count"], j["detail"]["html_count"], j["detail"]["output_present"]) == (2, 1, True)
        assert k["status"] == FL.PASS and k["detail"]["result"] == "BYTE_IDENTICAL"
        assert k["detail"]["output_digest_a"] != EMPTY_SHA
        assert receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES

    def test_the_staged_build_reports_whether_its_output_root_exists(self, package, tmp_path, stub_render):
        built = STAGING.build_changed_market(package, tmp_path / "s", tmp_path / "o")
        assert built["output_present"] is True and built["file_count"] == 2
        stub_render["write"] = False
        built = STAGING.build_changed_market(package, tmp_path / "s2", tmp_path / "o2")
        assert built["output_present"] is False and built["bundle_sha256"] == EMPTY_SHA
