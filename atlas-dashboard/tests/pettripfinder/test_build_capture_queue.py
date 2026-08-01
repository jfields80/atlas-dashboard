"""PTF-CAPTURE-003 -- seed-driven capture-queue generation.

The generator exists because the first pilot's Hilton Columbus at Easton entry
had its street address recovered from a *built HTML bundle* -- nothing in the
queue-authoring path read the seed. So the properties under test are: the seed
is the only source of identity, derived values match the pipeline's own
conventions exactly, and a hotel the seed cannot fully describe is excluded with
a reason rather than guessed at.

Offline: no network, no browser, no production write.
"""

from __future__ import annotations

import csv
import json
import pathlib

import pytest

from scripts.pettripfinder.build_capture_queue import (
    BRAND_DOMAINS, STATUS_ANY, STATUS_PUBLISHED, STATUS_UNPUBLISHED,
    brand_for_url, build_queue, format_summary, hotel_id_for, main,
    published_keys, read_seed_hotels, retrieval_artifacts,
)
from scripts.pettripfinder.site_data import normalize_name
from services.research_workers.capture_automation.adapters import known_brands
from services.research_workers.capture_automation.queue import (
    QUEUE_SCHEMA, load_queue,
)

SEED_HEADER = ("name,category,address,city,state,postal_code,phone,website_url,"
               "source_url,source_type,observed_at,rating,amenities,pet_policy,canonical")

MARRIOTT_URL = ("https://www.marriott.com/en-us/hotels/"
                "cmham-columbus-airport-marriott/overview/")
HILTON_URL = "https://www.hilton.com/en/hotels/cmhaphx-hampton-columbus-airport/"


def seed_row(name, url=MARRIOTT_URL, *, city="Columbus", phone="614-475-7551",
             address="1375 North Cassady Avenue", postal="43219",
             category="pet-friendly-hotels"):
    return {"name": name, "category": category, "address": address, "city": city,
            "state": "OH", "postal_code": postal, "phone": phone,
            "website_url": url, "source_url": url, "source_type": "official",
            "observed_at": "2026-07-01", "rating": "", "amenities": "",
            "pet_policy": "", "canonical": ""}


@pytest.fixture
def workspace(tmp_path):
    """A seed CSV, a launch package and a retrieval tree, all under tmp_path."""
    def build(rows, published_names=(), artifact_ids=None):
        seed = tmp_path / "seed.csv"
        with seed.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=SEED_HEADER.split(","))
            w.writeheader()
            for r in rows:
                w.writerow(r)

        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"hotels": [
            {"key": normalize_name(n), "name": n} for n in published_names]}),
            encoding="utf-8")

        retr = tmp_path / "retrieval"
        retr.mkdir(exist_ok=True)
        ids = artifact_ids if artifact_ids is not None else [
            hotel_id_for(r["name"]) for r in rows]
        for hid in ids:
            (retr / ("retr-%s.json" % hid)).write_text("{}", encoding="utf-8")
        return {"seed_csv": seed, "package_path": pkg, "retrieval_root": retr}
    return build


# --------------------------------------------------------------------------- #
# 1. Derivations match the pipeline's own conventions.
# --------------------------------------------------------------------------- #

class TestDerivations:
    def test_listing_key_matches_the_published_package_rule(self):
        """normalize_name is what keys hotel_policy_facts.json; the queue must
        agree or the capture will not join to anything downstream."""
        assert normalize_name("Drury Inn & Suites Columbus Polaris") == \
            "drury inn and suites columbus polaris"

    def test_hotel_id_is_filename_safe_and_stable(self):
        assert hotel_id_for("Fairfield Inn & Suites Columbus OSU") == \
            "fairfield-inn-suites-columbus-osu"
        assert hotel_id_for("Red Roof PLUS+ Columbus Worthington") == \
            "red-roof-plus-columbus-worthington"

    def test_hotel_id_and_listing_key_are_different_spaces(self):
        """One names files, the other joins to the pipeline. Conflating them
        would silently break either the journal or the promotion join."""
        name = "Courtyard Columbus Easton"
        assert hotel_id_for(name) == "courtyard-columbus-easton"
        assert normalize_name(name) == "courtyard columbus easton"

    @pytest.mark.parametrize("url,expected", [
        (MARRIOTT_URL, "marriott"),
        (HILTON_URL, "hilton"),
        ("https://www.ihg.com/staybridge/hotels/us/en/x/y/hoteldetail", "ihg"),
        ("https://www.hyatt.com/en-US/hotel/ohio/x/cmhrc", "hyatt"),
        ("https://www.daysinncolumbusohio.com/", ""),
        ("", ""),
    ])
    def test_brand_is_derived_from_the_host(self, url, expected):
        assert brand_for_url(url) == expected

    def test_a_lookalike_host_is_not_matched(self):
        """Suffix matching must respect the dot boundary."""
        assert brand_for_url("https://notmarriott.com/x") == ""
        assert brand_for_url("https://www.marriott.com.evil.test/x") == ""

    def test_every_brand_domain_maps_to_a_slug(self):
        for domain, slug in BRAND_DOMAINS:
            assert slug and brand_for_url("https://www.%s/x" % domain) == slug


# --------------------------------------------------------------------------- #
# 2. Selection.
# --------------------------------------------------------------------------- #

class TestSelection:
    def test_a_complete_seed_row_is_selected(self, workspace):
        ws = workspace([seed_row("Columbus Airport Marriott")])
        result = build_queue(batch_id="b", **ws)
        assert result.counts["selected"] == 1
        entry = result.selected[0]
        assert entry["hotel_id"] == "columbus-airport-marriott"
        assert entry["listing_key"] == "columbus airport marriott"
        assert entry["brand"] == "marriott"
        assert entry["expected_property_code"] == "cmham"
        assert entry["expected_address"] == "1375 North Cassady Avenue"
        assert entry["expected_phone"] == "614-475-7551"
        assert entry["required_fields"]
        assert entry["retrieval_artifact"]

    def test_non_hotel_categories_are_ignored(self, workspace):
        ws = workspace([seed_row("A Park", category="pet-friendly-parks"),
                        seed_row("Columbus Airport Marriott")])
        assert build_queue(batch_id="b", **ws).counts["selected"] == 1

    def test_market_filter(self, workspace):
        rows = [seed_row("Columbus Airport Marriott", city="Columbus"),
                seed_row("Hampton Inn Columbus Dublin", HILTON_URL, city="Dublin")]
        ws = workspace(rows)
        got = build_queue(batch_id="b", markets=["Dublin"], **ws)
        assert [h["expected_city"] for h in got.selected] == ["Dublin"]

    def test_market_filter_is_case_insensitive(self, workspace):
        ws = workspace([seed_row("Columbus Airport Marriott", city="Columbus")])
        assert build_queue(batch_id="b", markets=["columbus"], **ws).counts["selected"] == 1

    def test_brand_filter(self, workspace):
        rows = [seed_row("Columbus Airport Marriott"),
                seed_row("Hampton Inn Columbus Airport", HILTON_URL)]
        ws = workspace(rows)
        got = build_queue(batch_id="b", brands=["hilton"], **ws)
        assert [h["brand"] for h in got.selected] == ["hilton"]

    def test_status_published_and_unpublished(self, workspace):
        rows = [seed_row("Columbus Airport Marriott"),
                seed_row("Hampton Inn Columbus Airport", HILTON_URL)]
        ws = workspace(rows, published_names=["Columbus Airport Marriott"])
        pub = build_queue(batch_id="b", status=STATUS_PUBLISHED, **ws)
        unp = build_queue(batch_id="b", status=STATUS_UNPUBLISHED, **ws)
        assert [h["hotel_id"] for h in pub.selected] == ["columbus-airport-marriott"]
        assert [h["hotel_id"] for h in unp.selected] == ["hampton-inn-columbus-airport"]
        assert build_queue(batch_id="b", status=STATUS_ANY, **ws).counts["selected"] == 2

    def test_status_is_publication_state_only(self, workspace):
        """Pinned by the operator: `status` compares against the committed
        launch package and means nothing else.

        A published hotel may still need a fresh capture, so publication state
        must never be read as evidence status or capture-worthiness. This test
        exists so a later change cannot quietly redefine it.
        """
        rows = [seed_row("Columbus Airport Marriott")]
        # Present in the package -> published, regardless of anything else.
        ws = workspace(rows, published_names=["Columbus Airport Marriott"])
        assert build_queue(batch_id="b", status=STATUS_PUBLISHED, **ws).counts["selected"] == 1
        assert build_queue(batch_id="b", status=STATUS_UNPUBLISHED, **ws).counts["selected"] == 0

        # Absent from the package -> unpublished, with the SAME seed row and the
        # SAME retrieval artifact. Only package membership moved.
        ws2 = workspace(rows, published_names=[])
        assert build_queue(batch_id="b", status=STATUS_PUBLISHED, **ws2).counts["selected"] == 0
        assert build_queue(batch_id="b", status=STATUS_UNPUBLISHED, **ws2).counts["selected"] == 1

    def test_status_ignores_evidence_and_attestation_state(self):
        """Nothing from the attestation/approval layer is imported or called.

        Checked structurally, via the AST, not by substring: the module's own
        docstring names these concepts precisely to say it does NOT use them,
        and a raw text scan would flag that prose as a violation.
        """
        import ast

        import scripts.pettripfinder.build_capture_queue as mod
        tree = ast.parse(pathlib.Path(mod.__file__).read_text("utf-8"))

        imported, called = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.Call):
                fn = node.func
                name = getattr(fn, "id", None) or getattr(fn, "attr", None)
                if name:
                    called.add(name)

        for forbidden in ("build_attestation", "approve_attestation",
                          "approve_attestation_record", "OfficialAttestation",
                          "listing_readiness", "partition_by_renderability"):
            assert forbidden not in imported, "imports %s" % forbidden
            assert forbidden not in called, "calls %s" % forbidden

        for mod_name in imported:
            assert "operator_capture" not in mod_name, mod_name
            assert "promote_attested" not in mod_name, mod_name

    def test_the_status_meaning_is_documented(self):
        import scripts.pettripfinder.build_capture_queue as mod
        doc = (mod.__doc__ or "")
        assert "publication state only" in doc.lower()
        assert "NOT" in doc and "evidence status" in doc
        help_text = " ".join(mod.build_parser().format_help().split())
        assert "PUBLICATION STATE ONLY" in help_text
        assert "NOT evidence status" in help_text

    def test_explicit_hotel_ids(self, workspace):
        rows = [seed_row("Columbus Airport Marriott"),
                seed_row("Hampton Inn Columbus Airport", HILTON_URL)]
        ws = workspace(rows)
        got = build_queue(batch_id="b", hotel_ids=["hampton-inn-columbus-airport"], **ws)
        assert [h["hotel_id"] for h in got.selected] == ["hampton-inn-columbus-airport"]

    def test_limit_caps_the_selection(self, workspace):
        rows = [seed_row("Columbus Airport Marriott"),
                seed_row("Hampton Inn Columbus Airport", HILTON_URL)]
        ws = workspace(rows)
        got = build_queue(batch_id="b", limit=1, **ws)
        assert got.counts["selected"] == 1

    def test_limit_flags_that_the_scan_was_truncated(self, workspace):
        """The excluded list after a --limit is partial, and must say so."""
        rows = [seed_row("Columbus Airport Marriott"),
                seed_row("Hampton Inn Columbus Airport", HILTON_URL)]
        ws = workspace(rows)
        got = build_queue(batch_id="b", limit=1, **ws)
        assert got.limit_reached
        assert "partial" in format_summary(got)

    def test_a_full_scan_is_not_flagged_truncated(self, workspace):
        ws = workspace([seed_row("Columbus Airport Marriott")])
        got = build_queue(batch_id="b", limit=5, **ws)
        assert not got.limit_reached


# --------------------------------------------------------------------------- #
# 3. Fails closed, with a reason.
# --------------------------------------------------------------------------- #

class TestFailsClosed:
    def _only_exclusion(self, workspace, row, **kw):
        ws = workspace([row])
        result = build_queue(batch_id="b", **dict(ws, **kw))
        assert result.counts["selected"] == 0, "should not have been queued"
        assert len(result.excluded) == 1
        return result.excluded[0].reason

    def test_generic_brand_url_is_refused(self, workspace):
        """A URL that is not property-shaped can never be a stable citation."""
        reason = self._only_exclusion(
            workspace, seed_row("Some Marriott", "https://www.marriott.com/default.mi"))
        assert "url_shape_not_property" in reason or "property_code" in reason

    def test_search_url_is_refused(self, workspace):
        reason = self._only_exclusion(
            workspace, seed_row("Some Marriott",
                                "https://www.marriott.com/search/findHotels.mi?d=Columbus"))
        assert "url_shape_not_property" in reason

    def test_http_url_is_refused(self, workspace):
        reason = self._only_exclusion(
            workspace, seed_row("Some Marriott", MARRIOTT_URL.replace("https", "http")))
        assert "url_not_https" in reason

    def test_missing_address_is_refused(self, workspace):
        reason = self._only_exclusion(
            workspace, seed_row("Columbus Airport Marriott", address=""))
        assert "expected_address" in reason

    def test_missing_phone_is_refused(self, workspace):
        """The seed really does have four hotels with no phone; they must not
        silently become queue entries the identity gate cannot corroborate."""
        reason = self._only_exclusion(
            workspace, seed_row("Columbus Airport Marriott", phone=""))
        assert "expected_phone" in reason

    def test_missing_city_is_refused(self, workspace):
        reason = self._only_exclusion(
            workspace, seed_row("Columbus Airport Marriott", city=""))
        assert "expected_city" in reason

    def test_brand_without_an_adapter_is_refused(self, workspace):
        """Hyatt, deliberately. hyatt.com serves a Kasada interstitial our
        automation must not try to defeat, so no adapter exists and its hotels
        must be excluded here with a reason rather than queued and failed."""
        reason = self._only_exclusion(
            workspace, seed_row("Hyatt House Columbus OSU Short North",
                                "https://www.hyatt.com/hyatt-house/en-US/"
                                "cmhxo-hyatt-house-columbus-osu-short-north"))
        assert "no_adapter_for_brand:hyatt" in reason

    def test_a_brand_that_gained_an_adapter_is_now_selectable(self, workspace):
        """IHG was excluded for this reason until Phase 2A; the same seed row
        must now pass."""
        ws = workspace([seed_row("Staybridge Suites Columbus Dublin",
                                 "https://www.ihg.com/staybridge/hotels/us/en/"
                                 "dublin/cmhtc/hoteldetail")])
        result = build_queue(batch_id="b", **ws)
        assert result.counts["selected"] == 1
        assert result.selected[0]["brand"] == "ihg"
        assert result.selected[0]["expected_property_code"] == "cmhtc"

    def test_unrecognised_host_is_refused(self, workspace):
        reason = self._only_exclusion(
            workspace, seed_row("Days Inn Columbus",
                                "https://www.daysinncolumbusohio.com/rooms/"))
        assert "brand_unrecognised" in reason

    def test_missing_retrieval_artifact_is_refused_by_default(self, workspace):
        ws = workspace([seed_row("Columbus Airport Marriott")], artifact_ids=[])
        result = build_queue(batch_id="b", **ws)
        assert result.counts["selected"] == 0
        assert result.excluded[0].reason == "retrieval_artifact_missing"

    def test_missing_retrieval_artifact_can_be_waived_explicitly(self, workspace):
        ws = workspace([seed_row("Columbus Airport Marriott")], artifact_ids=[])
        result = build_queue(batch_id="b", require_retrieval_artifact=False, **ws)
        assert result.counts["selected"] == 1
        assert result.selected[0]["retrieval_artifact"] == ""

    def test_a_shared_official_url_is_refused_for_the_second_hotel(self, workspace):
        """One URL cannot be property-specific for two properties."""
        rows = [seed_row("Hotel One"), seed_row("Hotel Two")]
        ws = workspace(rows)
        result = build_queue(batch_id="b", **ws)
        assert result.counts["selected"] == 1
        assert "official_url_not_unique" in result.excluded[0].reason

    def test_every_exclusion_carries_a_non_empty_reason(self, workspace):
        rows = [seed_row("No Phone", phone=""),
                seed_row("Bad Brand", "https://www.hyatt.com/en-US/hotel/x/cmhrc"),
                seed_row("Bad Url", "https://www.marriott.com/default.mi")]
        ws = workspace(rows)
        for exc in build_queue(batch_id="b", **ws).excluded:
            assert exc.reason.strip()
            assert exc.hotel_id and exc.name


# --------------------------------------------------------------------------- #
# 4. Output is a real, loadable queue.
# --------------------------------------------------------------------------- #

class TestOutputIsValid:
    def test_the_emitted_queue_passes_the_real_preflight(self, workspace, tmp_path):
        rows = [seed_row("Columbus Airport Marriott"),
                seed_row("Hampton Inn Columbus Airport", HILTON_URL,
                         address="4280 International Gateway", postal="43219",
                         phone="614-235-0717")]
        ws = workspace(rows)
        result = build_queue(batch_id="generated-001", **ws)
        out = tmp_path / "queue.json"
        out.write_text(json.dumps(result.queue, indent=2), encoding="utf-8")

        queue = load_queue(out, known_brands=known_brands())
        assert len(queue) == 2
        assert queue.batch_id == "generated-001"

    def test_schema_and_shape(self, workspace):
        ws = workspace([seed_row("Columbus Airport Marriott")])
        q = build_queue(batch_id="b", **ws).queue
        assert q["schema"] == QUEUE_SCHEMA
        assert isinstance(q["hotels"], list)

    def test_every_required_field_is_emitted(self, workspace):
        ws = workspace([seed_row("Columbus Airport Marriott")])
        entry = build_queue(batch_id="b", **ws).selected[0]
        for field in ("hotel_id", "listing_key", "hotel_name", "brand",
                      "official_url", "expected_property_code", "expected_address",
                      "expected_city", "expected_state", "expected_postal_code",
                      "expected_phone", "required_fields", "retrieval_artifact"):
            assert field in entry, field

    def test_no_capture_or_attestation_state_leaks_into_the_queue(self, workspace):
        """The queue is an INPUT. It must carry nothing that looks like
        evidence, approval, page content or a published fact.

        Scanned by key and by value, with the two fields that legitimately hold
        filesystem paths excluded -- pytest's tmp_path embeds the test's own
        name, so a raw substring scan flags the word "attestation" in a
        directory name and proves nothing.
        """
        ws = workspace([seed_row("Columbus Airport Marriott")])
        entry = dict(build_queue(batch_id="b", **ws).selected[0])
        entry.pop("retrieval_artifact")     # a path, by design
        entry.pop("notes")                  # provenance prose, by design
        blob = json.dumps(entry)

        for forbidden in ("attestation", "approval", "APPROVED", "evidence",
                          "html", "text_sha256", "publishable", "captured_at"):
            assert forbidden not in blob, forbidden

        # required_fields NAMES the policy fields to capture; it must not carry
        # any captured VALUE.
        assert "pet_fee" in entry["required_fields"]
        assert not any(str(v).startswith("$") for v in entry.values()
                       if isinstance(v, str))

    def test_the_queue_keys_are_exactly_the_contract(self, workspace):
        ws = workspace([seed_row("Columbus Airport Marriott")])
        entry = build_queue(batch_id="b", **ws).selected[0]
        assert set(entry) == {
            "hotel_id", "listing_key", "hotel_name", "brand", "official_url",
            "expected_address", "expected_city", "expected_state",
            "expected_postal_code", "expected_phone", "expected_property_code",
            "required_fields", "retrieval_artifact", "notes"}


# --------------------------------------------------------------------------- #
# 5. CLI: dry-run and validation-only.
# --------------------------------------------------------------------------- #

class TestCli:
    def test_dry_run_writes_nothing(self, workspace, tmp_path, monkeypatch, capsys):
        ws = workspace([seed_row("Columbus Airport Marriott")])
        _patch_defaults(monkeypatch, ws)
        out = tmp_path / "queue.json"
        code = main(["--batch-id", "b", "--output", str(out), "--dry-run"])
        assert code == 0
        assert not out.exists()
        assert "would write" in capsys.readouterr().out

    def test_write_produces_a_loadable_file(self, workspace, tmp_path, monkeypatch, capsys):
        ws = workspace([seed_row("Columbus Airport Marriott")])
        _patch_defaults(monkeypatch, ws)
        out = tmp_path / "sub" / "queue.json"
        assert main(["--batch-id", "gen", "--output", str(out)]) == 0
        assert out.exists()
        assert len(load_queue(out, known_brands=known_brands())) == 1
        assert "wrote" in capsys.readouterr().out

    def test_an_empty_selection_refuses_to_write(self, workspace, tmp_path,
                                                 monkeypatch, capsys):
        ws = workspace([seed_row("Columbus Airport Marriott")], artifact_ids=[])
        _patch_defaults(monkeypatch, ws)
        out = tmp_path / "queue.json"
        assert main(["--batch-id", "b", "--output", str(out)]) == 2
        assert not out.exists()
        assert "refusing to write an empty queue" in capsys.readouterr().err

    def test_validate_only_accepts_a_good_queue(self, workspace, tmp_path, capsys):
        ws = workspace([seed_row("Columbus Airport Marriott")])
        result = build_queue(batch_id="b", **ws)
        out = tmp_path / "queue.json"
        out.write_text(json.dumps(result.queue), encoding="utf-8")
        assert main(["--validate-only", str(out)]) == 0
        assert "queue VALID" in capsys.readouterr().out

    def test_validate_only_rejects_a_bad_queue(self, tmp_path, capsys):
        out = tmp_path / "queue.json"
        out.write_text(json.dumps({"schema": QUEUE_SCHEMA, "batch_id": "b",
                                   "hotels": [{"hotel_id": "x"}]}), encoding="utf-8")
        assert main(["--validate-only", str(out)]) == 2
        assert "queue INVALID" in capsys.readouterr().err

    def test_batch_id_is_required(self, capsys):
        assert main(["--output", "x.json"]) == 2
        assert "--batch-id is required" in capsys.readouterr().err

    def test_json_summary_is_machine_readable(self, workspace, tmp_path,
                                              monkeypatch, capsys):
        ws = workspace([seed_row("Columbus Airport Marriott")])
        _patch_defaults(monkeypatch, ws)
        main(["--batch-id", "b", "--dry-run", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert payload["counts"]["selected"] == 1
        assert payload["wrote"] is False


def _patch_defaults(monkeypatch, ws):
    """Point the module's default input paths at the temp workspace."""
    import scripts.pettripfinder.build_capture_queue as mod
    monkeypatch.setattr(mod, "PRODUCTION_CSV", ws["seed_csv"])
    monkeypatch.setattr(mod, "LAUNCH_PACKAGE", ws["package_path"])
    monkeypatch.setattr(mod, "RETRIEVAL_ROOT", ws["retrieval_root"])


# --------------------------------------------------------------------------- #
# 6. Against the REAL seed -- read-only.
# --------------------------------------------------------------------------- #

class TestAgainstTheRealSeed:
    def test_the_real_seed_is_readable(self):
        rows = read_seed_hotels()
        assert len(rows) >= 40
        assert all(r["category"] == "pet-friendly-hotels" for r in rows)

    def test_the_real_seed_yields_a_valid_queue(self, tmp_path):
        result = build_queue(batch_id="real-seed-check",
                             brands=["marriott", "hilton"])
        assert result.counts["selected"] >= 10
        out = tmp_path / "q.json"
        out.write_text(json.dumps(result.queue), encoding="utf-8")
        assert len(load_queue(out, known_brands=known_brands())) == result.counts["selected"]

    def test_every_real_selection_has_a_property_code_in_its_url(self):
        for entry in build_queue(batch_id="c", brands=["marriott", "hilton"]).selected:
            assert entry["expected_property_code"]
            assert entry["expected_property_code"] in entry["official_url"]

    def test_unsupported_brands_are_excluded_not_silently_dropped(self):
        result = build_queue(batch_id="c")
        reasons = " ".join(e.reason for e in result.excluded)
        assert "no_adapter_for_brand" in reasons

    def test_building_is_deterministic(self):
        a = build_queue(batch_id="c", brands=["marriott"])
        b = build_queue(batch_id="c", brands=["marriott"])
        assert a.queue == b.queue

    def test_nothing_is_written_by_building(self, tmp_path):
        before = sorted(p.name for p in pathlib.Path(
            "launch_packages/pettripfinder").iterdir())
        build_queue(batch_id="c", brands=["marriott", "hilton"])
        after = sorted(p.name for p in pathlib.Path(
            "launch_packages/pettripfinder").iterdir())
        assert before == after
