# -*- coding: utf-8 -*-
"""PTF-FAST-RECEIPT-READER-GUARD-001 -- the READ side of f182cc08.

f182cc08 made rule J fail when a build produced nothing, but only for
receipts written from then on. ``eligible_receipts`` still trusted a stored
``FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES``, so a receipt written by the old
lane over an empty bundle stayed CURRENT-eligible. Augusta's committed
receipt is exactly that one: J PASS, file_count 0, html_count 0, bundle
e3b0c442... (the sha256 of the empty string).

That receipt must stay byte-identical: founder packet 005 binds its digest
and ``ptf-auth-augusta-006`` (DEPLOYED) was granted under that packet. So
the reader, not the receipt, changes -- and two questions stay separate:

  CURRENT ELIGIBILITY   may this receipt vouch for a release today?
                        ``eligible_receipts`` / ``receipt_output_defects``.
  HISTORICAL REFERENCE  are the bytes an authorization bound still the
                        bytes on disk? A digest check; never today's rules.

The synthetic cases use a temporary receipts directory. The Augusta cases
read the committed tree and write nothing.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.pettripfinder import deployment_authorization as DA
from scripts.pettripfinder import fast_release_lane as FL
from scripts.pettripfinder import global_deployment as GD
from scripts.pettripfinder import registration_data_only as REG
from scripts.pettripfinder import release_coordinator as RC
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import sealed_market_package as SMP

EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
MARKET = "synthetic-reader-mkt"
PACKAGE_DIGEST = "sha256:" + "a" * 64

REPO = Path(__file__).resolve().parents[2]
AUGUSTA = "augusta-ga"
AUGUSTA_RECEIPT = (REPO / "launch_packages" / "pettripfinder" / "markets" / "receipts" / AUGUSTA
                   / "pkg-augusta-ga-14806eca154760a0-5f8116aaecd97d09.json")
#: ``git hash-object`` would differ by line endings; this is the file's own sha256.
AUGUSTA_RECEIPT_SHA256 = "a2e22ce8ca4f74e12fcd46c683d0f2dbbffffd314f94c5dafe2e4d92aa2ae439"
AUGUSTA_RECEIPT_DIGEST = "sha256:5f8116aaecd97d0948810aab759a1670ce99cb7ce81b27adc7691bf87dafbe80"
AUGUSTA_PACKET = (REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
                  / "augusta_ga_founder_authorization_packet_005.json")
AUGUSTA_AUTH = REPO / "deploy" / "netlify" / "deployment_authorizations" / "ptf-auth-augusta-006-55e0f5bbf02a.json"
AUGUSTA_DEPLOY = REPO / "deploy" / "netlify" / "deployment_records" / "ptf-deploy-augusta-006-6aaeb3b7384e1bb712adb084.json"
SUPERSESSIONS = REPO / "tests" / "pettripfinder" / "pins" / "supersessions.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _self_digest(doc) -> str:
    """How the receipt writer (and every reader that re-checks it) hashes a receipt."""
    return SMP.sha256_text(SMP.canonical_json(OrderedDict(
        (k, v) for k, v in doc.items() if k not in ("TIMESTAMPS", "ENVIRONMENT", "PERFORMANCE", "RECEIPT_DIGEST"))))


def _j_fresh(file_count=120, html_count=104, bundle="5" * 64, **extra):
    detail = OrderedDict((("bundle_sha256", bundle), ("file_count", file_count), ("html_count", html_count)))
    detail.update(extra)
    return detail


def _j_cached(file_count=120, bundle="6" * 64):
    return OrderedDict((("MARKET_BUILD_REQUIRED", "NO"), ("cache_status", "HIT"), ("build_input_key", "k"),
                        ("bundle_sha256", bundle), ("file_count", file_count), ("output_defects", [])))


def _receipt(j_detail, *, package_id="pkg-%s-0001" % MARKET, eligible=FL.YES, drop=()):
    """A receipt in the stored shape: every rule PASS, J carrying ``j_detail``."""
    results = OrderedDict((r, OrderedDict((("rule", r), ("status", FL.PASS), ("detail", OrderedDict()))))
                          for r in FL.RULES)
    if j_detail is None:
        del results["J"]
    else:
        results["J"]["detail"] = j_detail
    doc = OrderedDict((("schema", FL.RECEIPT_SCHEMA), ("lane", FL.LANE), ("PACKAGE_ID", package_id),
                       ("PACKAGE_DIGEST", PACKAGE_DIGEST), ("MARKET_ID", MARKET), ("RESULTS", results),
                       ("UNKNOWN_RULES", []), ("FAILED_RULES", []),
                       ("FAST_DATA_ONLY_RELEASE_ELIGIBLE", eligible)))
    for key in drop:
        doc.pop(key)
    doc["RECEIPT_DIGEST"] = _self_digest(doc)
    return doc


def _put(root: Path, name: str, doc) -> Path:
    directory = root / MARKET
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    return path


def _names(root: Path):
    return [p.name for p in FL.eligible_receipts(MARKET, PACKAGE_DIGEST, root)]


def _codes(defects):
    return [d.split(":", 1)[0] for d in defects]


# --------------------------------------------------------------------------- #
# 1-5  One receipt: a stored PASS is not enough.
# --------------------------------------------------------------------------- #

class TestAStoredPassIsNotCurrentEligibility:
    def test_zero_files_is_not_current_eligible(self, tmp_path):
        doc = _receipt(_j_fresh(file_count=0))
        _put(tmp_path, "pkg-a.json", doc)
        assert doc["RESULTS"]["J"]["status"] == FL.PASS and doc["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES
        assert _codes(FL.receipt_output_defects(doc)) == [FL.EMPTY_BUNDLE]
        assert _names(tmp_path) == []

    def test_zero_html_is_not_current_eligible(self, tmp_path):
        doc = _receipt(_j_fresh(html_count=0))
        _put(tmp_path, "pkg-a.json", doc)
        assert _codes(FL.receipt_output_defects(doc)) == [FL.NO_HTML_OUTPUT]
        assert _names(tmp_path) == []

    @pytest.mark.parametrize("j_detail, codes", [
        (OrderedDict((("bundle_sha256", "5" * 64), ("html_count", 9))), [FL.EMPTY_BUNDLE]),
        (_j_fresh(file_count="120"), [FL.EMPTY_BUNDLE]),
        (_j_fresh(file_count=True), [FL.EMPTY_BUNDLE]),
        (_j_fresh(file_count=-3), [FL.EMPTY_BUNDLE]),
        (_j_fresh(file_count=None), [FL.EMPTY_BUNDLE]),
        (OrderedDict((("bundle_sha256", "5" * 64), ("file_count", 9))), [FL.NO_HTML_OUTPUT]),
        (_j_fresh(html_count=1.5), [FL.NO_HTML_OUTPUT]),
        (_j_fresh(output_present=False), [FL.MISSING_BUILD_OUTPUT]),
        (OrderedDict(), [FL.EMPTY_BUNDLE, FL.NO_HTML_OUTPUT]),
        ("not-a-mapping", [FL.EMPTY_BUNDLE, FL.NO_HTML_OUTPUT]),
        (None, [FL.EMPTY_BUNDLE, FL.NO_HTML_OUTPUT]),
    ], ids=["file_count_missing", "file_count_string", "file_count_bool", "file_count_negative",
            "file_count_null", "html_count_missing", "html_count_float", "output_absent",
            "empty_detail", "detail_not_a_mapping", "no_rule_j"])
    def test_a_missing_or_invalid_count_is_not_current_eligible(self, tmp_path, j_detail, codes):
        doc = _receipt(j_detail)
        _put(tmp_path, "pkg-a.json", doc)
        assert _codes(FL.receipt_output_defects(doc)) == codes
        assert _names(tmp_path) == []

    def test_the_empty_string_bundle_cannot_qualify_even_with_counts(self, tmp_path):
        doc = _receipt(_j_fresh(bundle=EMPTY_SHA))
        _put(tmp_path, "pkg-a.json", doc)
        assert _codes(FL.receipt_output_defects(doc)) == [FL.EMPTY_BUNDLE]
        assert _names(tmp_path) == []
        prefixed = _receipt(_j_fresh(bundle="sha256:" + EMPTY_SHA))
        assert _codes(FL.receipt_output_defects(prefixed)) == [FL.EMPTY_BUNDLE]

    def test_a_valid_non_empty_receipt_remains_eligible(self, tmp_path):
        doc = _receipt(_j_fresh(output_present=True))
        _put(tmp_path, "pkg-a.json", doc)
        assert FL.receipt_output_defects(doc) == []
        assert _names(tmp_path) == ["pkg-a.json"]

    def test_a_cached_bundle_receipt_needs_no_html_count_like_the_writer(self, tmp_path):
        # The writer's cache path records no html_count in J's detail and does
        # not require one there; the reader asks exactly the same.
        doc = _receipt(_j_cached())
        _put(tmp_path, "pkg-a.json", doc)
        assert FL.receipt_output_defects(doc) == []
        assert _names(tmp_path) == ["pkg-a.json"]
        assert _codes(FL.receipt_output_defects(_receipt(_j_cached(file_count=0)))) == [FL.EMPTY_BUNDLE]

    def test_the_pre_existing_filters_still_apply(self, tmp_path):
        _put(tmp_path, "pkg-a.json", _receipt(_j_fresh(), eligible=FL.NO))
        wrong = _receipt(_j_fresh())
        wrong["PACKAGE_DIGEST"] = "sha256:" + "b" * 64
        _put(tmp_path, "pkg-b.json", wrong)
        assert _names(tmp_path) == []


# --------------------------------------------------------------------------- #
# 6-7  Several receipts: selection is among CURRENT-eligible receipts only.
# --------------------------------------------------------------------------- #

class TestSelectionAmongSeveralReceipts:
    def test_an_invalid_lexicographically_later_receipt_cannot_displace_a_valid_one(self, tmp_path):
        _put(tmp_path, "pkg-x-0000aaaa.json", _receipt(_j_fresh()))
        _put(tmp_path, "pkg-x-ffffffff.json", _receipt(_j_fresh(file_count=0, html_count=0, bundle=EMPTY_SHA)))
        paths = FL.eligible_receipts(MARKET, PACKAGE_DIGEST, tmp_path)
        assert [p.name for p in paths] == ["pkg-x-0000aaaa.json"]
        assert paths[-1].name == "pkg-x-0000aaaa.json"          # what every caller takes

    def test_only_invalid_receipts_selects_nothing(self, tmp_path):
        _put(tmp_path, "pkg-x-1.json", _receipt(_j_fresh(file_count=0)))
        _put(tmp_path, "pkg-x-2.json", _receipt(_j_fresh(html_count=0)))
        assert _names(tmp_path) == []

    def test_several_valid_receipts_keep_the_existing_sorted_order(self, tmp_path):
        for name in ("pkg-x-cccc.json", "pkg-x-aaaa.json", "pkg-x-bbbb.json"):
            _put(tmp_path, name, _receipt(_j_fresh()))
        _put(tmp_path, "pkg-x-bbbc.json", _receipt(_j_fresh(html_count=0)))
        assert _names(tmp_path) == ["pkg-x-aaaa.json", "pkg-x-bbbb.json", "pkg-x-cccc.json"]


# --------------------------------------------------------------------------- #
# 8-11  Augusta: history preserved, current eligibility withdrawn.
# --------------------------------------------------------------------------- #

class TestAugustaHistoricalReceipt:
    def test_the_committed_receipt_bytes_are_the_historical_bytes(self):
        assert _sha256(AUGUSTA_RECEIPT) == AUGUSTA_RECEIPT_SHA256

    def test_the_historical_reference_still_verifies(self):
        # bytes exist -> they hash to their own RECEIPT_DIGEST -> packet 005
        # binds that digest and that package. Today's eligibility is not asked.
        doc = _load(AUGUSTA_RECEIPT)
        packet = _load(AUGUSTA_PACKET)["the_digests_this_authorization_binds"]
        assert doc["RECEIPT_DIGEST"] == AUGUSTA_RECEIPT_DIGEST == _self_digest(doc)
        assert packet["validation_receipt_digest"] == doc["RECEIPT_DIGEST"]
        assert packet["sealed_package_digest"] == doc["PACKAGE_DIGEST"]
        assert packet["sealed_package_id"] == doc["PACKAGE_ID"]
        assert AUGUSTA_RECEIPT.name == "%s-%s.json" % (doc["PACKAGE_ID"], doc["RECEIPT_DIGEST"].split(":", 1)[1][:16])
        # The stored historical verdict is untouched by the reader.
        assert doc["RESULTS"]["J"]["status"] == FL.PASS
        assert doc["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES

    def test_the_historical_authorization_chain_remains_verifiable(self):
        auth = _load(AUGUSTA_AUTH)
        record = _load(AUGUSTA_DEPLOY)
        assert auth["authorization_id"] == "ptf-auth-augusta-006-55e0f5bbf02a"
        assert auth["authorization_status"] == "DEPLOYED"
        assert "augusta_ga_founder_authorization_packet_005.json" in auth["authorization_source"]
        assert AUGUSTA_PACKET.is_file()
        assert record["final_status"] == "DEPLOYED"
        assert record["authorization_id"] == auth["authorization_id"]
        assert record["bundle_sha256"] == auth["bundle_sha256"]
        assert auth["authorization_id"] in _load(SUPERSESSIONS)["authorizations"]
        listed = {a["authorization_id"]: a for a in DA.list_authorizations()}
        assert listed[auth["authorization_id"]] == auth

    def test_historical_verification_never_consults_current_receipt_eligibility(self):
        # Authorization, manifest and live-state verification read no receipt,
        # so withdrawing a receipt's CURRENT eligibility cannot unverify them.
        for module in (DA, GD, RI):
            source = inspect.getsource(module)
            assert "eligible_receipts" not in source and "receipt_output_defects" not in source, module.__name__

    def test_the_vacuous_receipt_is_not_current_eligible(self):
        doc = _load(AUGUSTA_RECEIPT)
        assert FL.receipt_output_defects(doc) == [
            "EMPTY_BUNDLE: the bundle contains no files (file_count 0, bundle e3b0c44298fc1c14)",
            "NO_HTML_OUTPUT: the bundle contains no HTML (html_count 0)",
        ]
        assert FL.eligible_receipts(AUGUSTA, doc["PACKAGE_DIGEST"]) == []

    def test_current_candidate_selection_does_not_use_it(self):
        package = SMP.read_sealed(SMP.list_packages(AUGUSTA)[-1])
        assert package["package_digest"] == _load(AUGUSTA_RECEIPT)["PACKAGE_DIGEST"]
        with pytest.raises(RC.CoordinatorError) as exc:
            RC.bound_fast_receipt(package, None)
        assert exc.value.code == RC.RECEIPT_NOT_BOUND
        verdict = REG.check_fast_receipt(package, AUGUSTA, None, None)
        assert verdict["status"] == REG.FAIL
        assert verdict["why"].startswith("no committed receipt says FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES")

    def test_reading_never_mutates_a_receipt(self, tmp_path):
        before = _sha256(AUGUSTA_RECEIPT)
        doc = _load(AUGUSTA_RECEIPT)
        FL.receipt_output_defects(doc)
        FL.eligible_receipts(AUGUSTA, doc["PACKAGE_DIGEST"])
        written = _put(tmp_path, "pkg-a.json", _receipt(_j_fresh(file_count=0)))
        synthetic = written.read_bytes()
        FL.eligible_receipts(MARKET, PACKAGE_DIGEST, tmp_path)
        assert _sha256(AUGUSTA_RECEIPT) == before == AUGUSTA_RECEIPT_SHA256
        assert written.read_bytes() == synthetic
        assert _load(AUGUSTA_RECEIPT) == doc

    def test_every_other_committed_receipt_stays_current_eligible(self):
        root = SMP.RECEIPTS_DIR
        withdrawn, kept = [], 0
        for path in sorted(root.glob("*/pkg-*.json")):
            doc = _load(path)
            if path in FL.eligible_receipts(doc["MARKET_ID"], doc["PACKAGE_DIGEST"]):
                kept += 1
            else:
                withdrawn.append(path.name)
        assert withdrawn == [AUGUSTA_RECEIPT.name]
        assert kept >= 22


# --------------------------------------------------------------------------- #
# 12  Diagnostics are deterministic.
# --------------------------------------------------------------------------- #

class TestDeterministicDiagnostics:
    def test_the_same_receipt_always_gives_the_same_defects_in_the_same_order(self):
        detail = _j_fresh(file_count=0, html_count=0, bundle=EMPTY_SHA, output_present=False)
        doc = _receipt(detail)
        reordered = _receipt(OrderedDict(reversed(list(detail.items()))))
        first = FL.receipt_output_defects(doc)
        assert _codes(first) == [FL.MISSING_BUILD_OUTPUT, FL.EMPTY_BUNDLE, FL.NO_HTML_OUTPUT]
        assert all(FL.receipt_output_defects(doc) == first for _ in range(5))
        assert FL.receipt_output_defects(reordered) == first
        assert FL.receipt_output_defects(json.loads(json.dumps(doc))) == first

    def test_the_reader_reuses_the_writers_rule_not_a_copy(self):
        doc = _receipt(_j_fresh(file_count=0, html_count=0, bundle=EMPTY_SHA))
        assert FL.receipt_output_defects(doc) == FL.bundle_output_defects(doc["RESULTS"]["J"]["detail"])
        assert "bundle_output_defects" in inspect.getsource(FL.receipt_output_defects)
        assert "receipt_output_defects" in inspect.getsource(FL.eligible_receipts)
