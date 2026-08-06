"""The one missing link: a discovery capture entering the attestation chain.

Everything downstream already works and has published 38 hotels. What did not
exist was a way IN for a capture whose hotel was never in the legacy seed CSV --
which is all 62 discovery-captured properties.

A bridge is where evidence changes hands, so nothing here is believed. Hashes
are recomputed from bytes, the screenshot is re-digested from disk, the final
URL must match what was asked for, and the recorded policy offsets must still
frame the recorded excerpt in the captured text. Identity must be exactly
IDENTITY_CONFIRMED -- not "ok", not "close enough".

The output is PENDING and not publishable. This module has no authority: it
does not approve, promote, assemble, deploy, or touch published data, and every
extraction rule, vocabulary and validator downstream is untouched.
"""

from __future__ import annotations

import copy
import hashlib
import json
import pathlib

import pytest

from services.research_workers.capture_automation.attestation_bridge import (
    REQUIRED_IDENTITY_FIELDS, BridgeInput, BridgeRefusal, bridge_capture,
    bridge_many, normalized_url, published_overlaps,
)
from services.research_workers.capture_automation.identity_keys import (
    IDENTITY_CONFIRMED, IDENTITY_INCOMPLETE,
)

from .conftest import make_png

URL = "https://www.hilton.com/en/hotels/cmhcagi-hilton-garden-inn-columbus-airport"
TEXT_HEAD = "Hilton Garden Inn Columbus Airport\n\nAmenities\n\n"
POLICY = ("Pets\n\nPets allowed\n\nYes\n\nDeposit\n\nYes. $75.00 Non-refundable Fee\n\n"
          "Max weight\n\n75 lbs\n\nOther pet information\n\n$75(1-4n)$125(5+n)2pet")
TEXT = TEXT_HEAD + POLICY + "\n\nFooter"
#: ingest_capture requires MIN_USEFUL_TEXT_BYTES (400) of normalized text and
#: rejects a JavaScript-only shell -- a real property page easily clears both.
#: The fixture has to as well, or the bridge would be validated against a page
#: the downstream contract would refuse anyway.
HTML = (
    "<html><body>"
    "<h1>Hilton Garden Inn Columbus Airport</h1>"
    "<p>3288 Lane Ave, Columbus, OH 43219. Telephone 614-476-3600.</p>"
    "<p>Guest rooms and suites with complimentary WiFi, on-site dining, "
    "a fitness center, an indoor pool and free parking. The hotel is minutes "
    "from John Glenn Columbus International Airport and Easton Town Center.</p>"
    "<section data-testid='policies-pets'><h2>Pets</h2>"
    "<p>Pets allowed: Yes</p><p>Deposit: Yes. $75.00 Non-refundable Fee</p>"
    "<p>Max weight: 75 lbs</p>"
    "<p>Other pet information: $75(1-4n)$125(5+n)2pet</p></section>"
    "<p>Check-in 3:00 PM. Check-out 11:00 AM. Smoking is not permitted "
    "anywhere on the property.</p>"
    "</body></html>")


def entry(**over):
    base = {
        "hotel_id": "hilton-garden-inn-columbus-airport",
        "listing_key": "hilton garden inn columbus airport",
        "hotel_name": "Hilton Garden Inn Columbus Airport",
        "brand": "hilton",
        "official_url": URL + "/?SEO_id=GMB-AMER-GI-CMHC",
        "expected_address": "3288 Lane Ave", "expected_city": "Columbus",
        "expected_state": "OH", "expected_postal_code": "43219",
        "expected_phone": "614-476-3600",
        "expected_property_code": "cmhcagi",
    }
    base.update(over)
    return base


def identity_block(outcome=IDENTITY_CONFIRMED, groups=("address", "phone"), auth=True):
    return {"outcome": outcome, "may_proceed": outcome == IDENTITY_CONFIRMED,
            "keys": {"outcome": outcome, "independent_groups": list(groups),
                     "has_authoritative_key": auth,
                     "keys": [{"key": "normalized_street_address",
                               "basis": "structured_metadata", "counts": True,
                               "authoritative": auth}]}}


def write_capture(tmp_path, *, payload_over=None, view_over=None, png=None,
                  omit_png=False, omit_view=False):
    """A capture package shaped exactly as the runner writes one."""
    start = TEXT.index(POLICY)
    payload = {
        "schema": "ptf-official-capture/1.0",
        "captured_at": "2026-08-04T07:06:03.627Z",
        "final_url": URL, "requested_url": URL, "canonical_url": URL,
        "title": "Hilton Garden Inn Columbus Airport",
        "html": HTML, "text": TEXT, "jsonld": [],
        # The runner stamps this on every capture; ingest_capture requires
        # it. All 67 real captures carry it -- the fixture must too, or the
        # bridge would be tested against a contract nothing produces.
        "extension_version": "ptf-capture-003/1.0.0",
        "html_sha256": hashlib.sha256(HTML.encode()).hexdigest(),
        "text_sha256": hashlib.sha256(TEXT.encode()).hexdigest(),
        "automation": {
            "identity": identity_block(),
            "policy": {"selector": "[data-testid='policies-pets']",
                       "matched_anchors": ["Pets", "Deposit"], "score": 46,
                       "text_excerpt": POLICY, "text_start": start,
                       "text_end": start + len(POLICY), "confidence": "HIGH"},
        },
    }
    if payload_over:
        for k, v in payload_over.items():
            if k == "automation":
                payload["automation"].update(v)
            else:
                payload[k] = v

    cap = tmp_path / "capture.json"
    cap.write_text(json.dumps(payload), encoding="utf-8")

    data = png if png is not None else make_png(320, 200)
    if not omit_png:
        (tmp_path / "capture.png").write_bytes(data)
    view = {"png_file": "capture.png", "png_sha256": hashlib.sha256(data).hexdigest(),
            "png_bytes": len(data), "png_width": 320, "png_height": 200,
            "final_url": URL, "captured_at": "2026-08-04T07:06:28.367Z",
            "field_observations": []}
    if view_over:
        view.update(view_over)
    if not omit_view:
        (tmp_path / "capture.view.json").write_text(json.dumps(view), encoding="utf-8")
    return cap


def bridged(tmp_path, **kw):
    """Identity travels beside the capture, as the journal records it."""
    e = kw.pop("entry_over", {})
    ident = kw.pop("identity", None)
    cap = write_capture(tmp_path, **kw)
    if ident is None:
        ident = identity_block()
    return bridge_capture(BridgeInput.from_capture(entry(**e), cap, identity=ident))


# --------------------------------------------------------------------------- #
# Refusals.
# --------------------------------------------------------------------------- #

class TestRefusals:
    def test_identity_not_confirmed(self, tmp_path):
        with pytest.raises(BridgeRefusal, match="identity_not_confirmed"):
            bridged(tmp_path, identity=identity_block(outcome=IDENTITY_INCOMPLETE))

    def test_identity_absent_entirely(self, tmp_path):
        with pytest.raises(BridgeRefusal, match="identity_not_confirmed:none_recorded"):
            bridged(tmp_path, identity={})

    def test_identity_confirmed_but_thin_evidence(self, tmp_path):
        """CONFIRMED is necessary, not sufficient -- the evidence behind it is
        re-checked rather than taken on the label."""
        with pytest.raises(BridgeRefusal, match="identity_evidence_insufficient"):
            bridged(tmp_path, identity=identity_block(groups=("address",)))
        with pytest.raises(BridgeRefusal, match="identity_evidence_insufficient"):
            bridged(tmp_path, identity=identity_block(auth=False))

    def test_capture_hash_mismatch(self, tmp_path):
        with pytest.raises(BridgeRefusal, match="capture_hash_mismatch:text_sha256"):
            bridged(tmp_path, payload_over={"text_sha256": "0" * 64})

    def test_capture_html_hash_mismatch(self, tmp_path):
        with pytest.raises(BridgeRefusal, match="capture_hash_mismatch:html_sha256"):
            bridged(tmp_path, payload_over={"html_sha256": "0" * 64})

    def test_screenshot_hash_mismatch(self, tmp_path):
        with pytest.raises(BridgeRefusal, match="screenshot_hash_mismatch"):
            bridged(tmp_path, view_over={"png_sha256": "0" * 64})

    @pytest.mark.parametrize("field", REQUIRED_IDENTITY_FIELDS)
    def test_missing_queue_identity_fields(self, tmp_path, field):
        with pytest.raises(BridgeRefusal, match="missing_queue_identity_fields:%s" % field):
            bridged(tmp_path, entry_over={field: ""})

    def test_final_url_mismatch(self, tmp_path):
        with pytest.raises(BridgeRefusal, match="final_url_mismatch"):
            bridged(tmp_path, payload_over={
                "final_url": "https://www.hilton.com/en/hotels/other-hotel"})

    def test_policy_offsets_outside_text(self, tmp_path):
        with pytest.raises(BridgeRefusal, match="policy_offsets_outside_text"):
            bridged(tmp_path, payload_over={"automation": {"policy": {
                "text_excerpt": POLICY, "text_start": 5, "text_end": 99_999}}})

    def test_policy_offsets_do_not_frame_the_excerpt(self, tmp_path):
        """Offsets that land somewhere else in the page are worse than absent."""
        with pytest.raises(BridgeRefusal, match="policy_offsets_do_not_frame_excerpt"):
            bridged(tmp_path, payload_over={"automation": {"policy": {
                "text_excerpt": POLICY, "text_start": 0, "text_end": len(POLICY)}}})

    def test_policy_block_absent(self, tmp_path):
        with pytest.raises(BridgeRefusal, match="policy_block_absent"):
            bridged(tmp_path, payload_over={"automation": {"policy": {}}})

    def test_missing_screenshot(self, tmp_path):
        with pytest.raises(BridgeRefusal, match="missing_screenshot"):
            bridged(tmp_path, omit_png=True)

    def test_missing_view_metadata(self, tmp_path):
        with pytest.raises(BridgeRefusal, match="missing_view_metadata"):
            bridged(tmp_path, omit_view=True)

    def test_duplicate_final_url_is_dropped_not_bridged(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir(); b.mkdir()
        cap_a = write_capture(a)
        cap_b = write_capture(b)
        batch = bridge_many([
            BridgeInput.from_capture(entry(), cap_a, identity=identity_block()),
            BridgeInput.from_capture(entry(hotel_id="hilton-garden-inn",
                                           official_url=URL + "/"), cap_b,
                                     identity=identity_block()),
        ])
        assert batch.summary() == {"bridged": 1, "refused": 0, "duplicates": 1}
        assert batch.duplicates[0][0] == "hilton-garden-inn"


class TestNoSeedDependency:
    def test_the_bridge_never_reads_the_seed(self):
        """The whole reason this module exists. A discovery hotel is not in the
        legacy seed CSV and must not need to be."""
        import inspect

        from services.research_workers.capture_automation import attestation_bridge

        src = inspect.getsource(attestation_bridge)
        for token in ("seed_businesses", "read_production_rows", "load_seed",
                      "seed_rows", "--seed"):
            assert token not in src, token

    def test_a_hotel_absent_from_the_seed_still_bridges(self, tmp_path):
        result = bridged(tmp_path, entry_over={
            "hotel_id": "a-hotel-that-is-in-no-seed-file",
            "listing_key": "a hotel that is in no seed file"})
        assert result.job.listing_key == "a hotel that is in no seed file"


# --------------------------------------------------------------------------- #
# Positive path.
# --------------------------------------------------------------------------- #

class TestValidCrossing:
    def test_a_valid_capture_becomes_a_valid_attestation_input(self, tmp_path):
        from services.research_workers.operator_capture import CaptureJob, ingest_capture

        result = bridged(tmp_path)
        assert isinstance(result.job, CaptureJob)
        assert result.job.official_url == entry()["official_url"]
        assert result.job.expected_address == "3288 Lane Ave"
        assert result.job.expected_postal_code == "43219"
        # The real downstream consumer accepts it.
        outcome = ingest_capture(result.payload, result.job, observed_at="2026-08-04")
        assert outcome.accepted, outcome.failure_reason

    def test_provenance_and_screenshot_linkage_are_preserved(self, tmp_path):
        result = bridged(tmp_path)
        assert result.screenshot_path.exists() and result.view_path.exists()
        view = json.loads(result.view_path.read_text("utf-8"))
        assert view["png_sha256"] == hashlib.sha256(
            result.screenshot_path.read_bytes()).hexdigest()
        assert result.payload["text_sha256"] == hashlib.sha256(
            result.payload["text"].encode()).hexdigest()
        assert result.policy_excerpt == POLICY
        assert set(result.verified) >= {"identity_confirmed", "capture_hashes",
                                        "screenshot_hash", "final_url",
                                        "policy_block_offsets"}

    def test_explicit_unknowns_stay_unknown(self, tmp_path):
        """An absent optional field is carried as empty, never invented."""
        result = bridged(tmp_path, entry_over={"expected_postal_code": "",
                                               "expected_property_code": ""})
        assert result.job.expected_postal_code == ""
        assert "43219" not in json.dumps(result.job.to_dict())

    def test_output_is_pending_and_not_publishable(self, tmp_path):
        result = bridged(tmp_path)
        assert result.status == "PENDING"
        assert result.publishable is False
        blob = json.dumps(result.to_dict())
        for word in ("APPROVED", "approval_record_id", "promoted"):
            assert word not in blob

    def test_the_bridge_has_no_approval_or_promotion_authority(self):
        """Scanned over EXECUTABLE code only.

        The prose deliberately says the module never approves and never
        promotes; asserting those words are absent from the source would mean
        deleting the sentence that states the guarantee. What matters is that
        no such call exists.
        """
        import ast
        import inspect

        from services.research_workers.capture_automation import attestation_bridge

        tree = ast.parse(inspect.getsource(attestation_bridge))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    names.add(a.name.split(".")[-1])
                if isinstance(node, ast.ImportFrom) and node.module:
                    names.update(node.module.split("."))
        for banned in ("approve_attestation", "build_attestation",
                       "promote_attested_candidates", "promote_worker_candidates",
                       "export_hotel_policy_facts", "assemble_netlify_bundle"):
            assert banned not in names, banned
        # And the only thing it imports from the attestation module is the
        # input contract itself.
        assert "CaptureJob" in names

    def test_deterministic_replay(self, tmp_path):
        """Same bytes in, same crossing out."""
        first = bridged(tmp_path).to_dict()
        for _ in range(3):
            again = bridge_capture(BridgeInput.from_capture(
                entry(), tmp_path / "capture.json",
                identity=identity_block())).to_dict()
            assert again == first
        h = lambda d: hashlib.sha256(
            json.dumps(d, sort_keys=True).encode()).hexdigest()
        assert h(first) == h(bridged(tmp_path).to_dict())

    def test_normalized_url_collapses_the_real_duplicate_shapes(self):
        base = "https://www.hilton.com/en/hotels/lckcoht-home2-suites-columbus-downtown"
        for variant in (base, base + "/", base + "/?SEO_id=GMB-AMER-HT",
                        base.upper().replace("HTTPS://WWW.HILTON.COM",
                                             "https://www.hilton.com")):
            assert normalized_url(variant) == normalized_url(base), variant


class TestPublishedOverlap:
    def test_an_existing_published_hotel_is_a_comparison_not_an_overwrite(self, tmp_path):
        result = bridged(tmp_path)
        published = [{"name": "Hilton Garden Inn Columbus Airport",
                      "source_url": URL,
                      "facts": {"fee_tiers": {}, "pets_allowed": {}, "weight_limit": {}}}]
        overlaps = published_overlaps([result], published)
        assert len(overlaps) == 1
        assert overlaps[0]["action"] == "COMPARE_ONLY"
        assert overlaps[0]["published_facts"] == ["fee_tiers", "pets_allowed", "weight_limit"]

    def test_a_deliberate_published_state_is_reported_not_replaced(self, tmp_path):
        """fee_conflict and fee_withheld were REACHED, not failed into."""
        result = bridged(tmp_path)
        published = [{"name": "X", "source_url": URL,
                      "facts": {"fee_conflict": {}, "pets_allowed": {}}}]
        overlaps = published_overlaps([result], published)
        assert overlaps[0]["published_facts"] == ["fee_conflict", "pets_allowed"]
        assert overlaps[0]["action"] == "COMPARE_ONLY"

    def test_no_overlap_reports_nothing(self, tmp_path):
        result = bridged(tmp_path)
        assert published_overlaps([result], [{"name": "Other",
                                              "source_url": "https://x.test/other"}]) == ()


class TestBatchAccounting:
    def test_every_input_gets_exactly_one_disposition(self, tmp_path):
        good, bad = tmp_path / "g", tmp_path / "b"
        good.mkdir(); bad.mkdir()
        cap_good = write_capture(good)
        cap_bad = write_capture(bad)
        batch = bridge_many([
            BridgeInput.from_capture(entry(), cap_good, identity=identity_block()),
            BridgeInput.from_capture(entry(hotel_id="bad", official_url="https://x.test/b"),
                                     cap_bad,
                                     identity=identity_block(outcome=IDENTITY_INCOMPLETE)),
        ])
        s = batch.summary()
        assert s["bridged"] + s["refused"] + s["duplicates"] == 2
        assert batch.refused[0][0] == "bad"
        assert "identity_not_confirmed" in batch.refused[0][1]

    def test_refusals_carry_a_named_reason(self, tmp_path):
        d = tmp_path / "x"; d.mkdir()
        cap = write_capture(d, view_over={"png_sha256": "0" * 64})
        batch = bridge_many([BridgeInput.from_capture(entry(), cap,
                                                      identity=identity_block())])
        assert batch.bridged == ()
        assert batch.refused[0][1] == "screenshot_hash_mismatch"


# --------------------------------------------------------------------------- #
# PTF-OVERLAP-001 -- published-overlap matching by property identifier.
# --------------------------------------------------------------------------- #

class _R:
    """Only the two fields published_overlaps reads."""
    def __init__(self, url, key="k"):
        self.normalized_url = url
        self.job = type("J", (), {"listing_key": key})()


HILTON = "https://www.hilton.com/en/hotels/cmhduhw-homewood-suites-columbus-dublin"


def test_a_property_subpage_matches_the_published_property():
    """The defect this fix exists for: /hotel-info differs by a path SEGMENT.

    normalized_url keeps segments by design, so a URL-only join missed a hotel
    that was already published and classified it net-new.
    """
    published = [{"key": "homewood suites by hilton columbus dublin",
                  "name": "Homewood Suites", "source_url": HILTON + "/hotel-info/"}]
    got = published_overlaps([_R(HILTON)], published)
    assert len(got) == 1 and got[0]["action"] == "COMPARE_ONLY"


def test_two_hotels_behind_one_brand_policy_url_are_never_merged():
    """Both Red Roof properties publish the same brand pet-policy page.

    That URL names a brand, not a property, so it may not identify either.
    """
    brand = "https://www.redroof.com/why-red-roof/pet-policy"
    published = [{"key": "red roof plus columbus downtown convention center",
                  "name": "A", "source_url": brand},
                 {"key": "red roof plus columbus worthington",
                  "name": "B", "source_url": brand}]
    assert published_overlaps([_R(brand)], published) == ()


def test_a_url_match_is_refused_when_the_property_codes_differ():
    other = "https://www.hilton.com/en/hotels/cmhaphx-hampton-columbus-airport"
    published = [{"key": "hampton inn columbus airport", "name": "H",
                  "source_url": other}]
    assert published_overlaps([_R(HILTON)], published) == ()


def test_an_unrelated_property_still_does_not_match():
    published = [{"key": "somewhere else", "name": "X",
                  "source_url": "https://www.hilton.com/en/hotels/cmhzzzz-other"}]
    assert published_overlaps([_R(HILTON)], published) == ()


def test_codeless_urls_still_match_exactly_as_before():
    """Wyndham URLs carry no code, so tier 2 must still decide them."""
    url = ("https://www.wyndhamhotels.com/laquinta/columbus-ohio/"
           "la-quinta-columbus-west-hilliard/overview")
    published = [{"key": "la quinta columbus west hilliard", "name": "LQ",
                  "source_url": url}]
    got = published_overlaps([_R(url)], published)
    assert len(got) == 1
