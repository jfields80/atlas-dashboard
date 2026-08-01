"""PETTRIPFINDER-PROD-005A -- local Netlify deployment authority tests.

Covers the tracked config (root netlify.toml, header/redirect templates, release
contract), the deterministic bundle assembler, and its isolation guarantees
(no network, no credential read, no tracked-file mutation, no .netlify/). All
assembly writes go to pytest tmp dirs -- never the repo, never a remote.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import tomllib
from contextlib import contextmanager
from pathlib import Path

import pytest

from scripts.generate_pettripfinder_columbus_site import run as generator_run
import scripts.pettripfinder.assemble_netlify_bundle as asm
from scripts.pettripfinder.assemble_netlify_bundle import (
    AssembleError,
    HEADERS_PREVIEW_PATH,
    HEADERS_PRODUCTION_PATH,
    NETLIFY_TOML_PATH,
    REDIRECTS_PATH,
    RELEASE_CONTRACT_PATH,
    REPO_ROOT,
    assemble,
    bundle_hash,
    load_release_contract,
    parse_headers_file,
    parse_redirects_file,
    validate_output_path,
)
from scripts.pettripfinder.site_data import (
    load_published_hotel_policy_facts,
    read_production_rows,
    verified_public_hotels,
)

EXPECTED_PACKAGE_SHA = "9fd9050f4b21225076973613176efe0318e140e39ec66fab60510663a4ea9bdd"
DEPLOY_DIR = REPO_ROOT / "deploy" / "netlify"


def _sha256(path: Path) -> str:
    """Content hash, matching the gate. A raw byte hash is not a stable
    identity for a text file whose line endings a checkout may rewrite --
    asserting one here passed in the authoring tree and failed in every fresh
    clone, which is how the gate defect stayed hidden."""
    from scripts.pettripfinder.assemble_netlify_bundle import content_sha256
    return content_sha256(path.read_bytes())


def _verified_slugs():
    from scripts.generate_pettripfinder_columbus_site import _slug
    facts = load_published_hotel_policy_facts()
    hotel_rows = [r for r in read_production_rows() if r.get("category") == "pet-friendly-hotels"]
    return {_slug(r["name"]) for r in verified_public_hotels(hotel_rows, facts)}


# --------------------------------------------------------------------------- #
# Root netlify.toml
# --------------------------------------------------------------------------- #

class TestNetlifyToml:
    def test_root_toml_exists_and_parses(self):
        assert NETLIFY_TOML_PATH.exists()
        data = tomllib.loads(NETLIFY_TOML_PATH.read_text(encoding="utf-8"))
        assert "build" in data

    def test_no_operative_toml_in_deploy_dir(self):
        # deploy/netlify/ holds SOURCE templates only; the operative netlify.toml
        # must live at the repository root, never under deploy/netlify/.
        assert not (DEPLOY_DIR / "netlify.toml").exists()

    def test_publish_dir_is_site_and_manual_prebuilt_model(self):
        data = tomllib.loads(NETLIFY_TOML_PATH.read_text(encoding="utf-8"))
        assert data["build"]["publish"] == "site"
        # A Git-triggered build must fail rather than publish repo internals.
        assert "exit 1" in data["build"]["command"]

    def test_toml_contains_no_secret_or_remote_id(self):
        text = NETLIFY_TOML_PATH.read_text(encoding="utf-8")
        # The env-var NAME may be referenced; a VALUE never may.
        assert "nfp_" not in text
        assert not re.search(r"[0-9a-f]{32,}", text)          # no token/site-id hex
        assert not re.search(r"NETLIFY_AUTH_TOKEN\s*=", text)  # no literal assignment
        assert not re.search(r"NETLIFY_SITE_ID\s*=", text)

    def test_cli_dir_override_is_documented(self):
        runbook = (REPO_ROOT / "docs" / "pettripfinder" / "DEPLOYMENT_RUNBOOK.md").read_text(encoding="utf-8")
        assert "--dir" in runbook


# --------------------------------------------------------------------------- #
# Release contract
# --------------------------------------------------------------------------- #

class TestReleaseContract:
    def test_contract_parses(self):
        contract = load_release_contract()
        assert contract["product"] == "pettripfinder-columbus"
        assert contract["canonical"]["base_url"] == "https://pettripfinder.com"

    def test_package_path_exists(self):
        contract = load_release_contract()
        assert (REPO_ROOT / contract["policy_package"]["path"]).exists()

    def test_package_schema_count_hash_match(self):
        contract = load_release_contract()
        spec = contract["policy_package"]
        pkg_path = REPO_ROOT / spec["path"]
        assert _sha256(pkg_path) == spec["expected_sha256"] == EXPECTED_PACKAGE_SHA
        pkg = json.loads(pkg_path.read_text(encoding="utf-8-sig"))
        assert str(pkg["schema_version"]) == spec["expected_schema_version"] == "1.1"
        assert len(pkg["hotels"]) == spec["expected_record_count"] == 34

    def test_package_identity_survives_a_checkout_rewriting_line_endings(self):
        """The defect this closes: the gate hashed raw bytes, so a clone whose
        checkout used CRLF computed a different digest for the SAME reviewed
        package, failed the gate, and refused to assemble. Found by running the
        suite in a clean worktree, not by any existing test."""
        from scripts.pettripfinder.assemble_netlify_bundle import content_sha256
        pkg_path = REPO_ROOT / load_release_contract()["policy_package"]["path"]
        lf = pkg_path.read_bytes().replace(b"\r\n", b"\n")
        assert content_sha256(lf) == EXPECTED_PACKAGE_SHA
        assert content_sha256(lf.replace(b"\n", b"\r\n")) == EXPECTED_PACKAGE_SHA
        assert content_sha256(b"\xef\xbb\xbf" + lf) == EXPECTED_PACKAGE_SHA

    def test_content_hash_still_detects_a_real_change(self):
        """Line-ending tolerance must not become change tolerance."""
        from scripts.pettripfinder.assemble_netlify_bundle import content_sha256
        pkg_path = REPO_ROOT / load_release_contract()["policy_package"]["path"]
        raw = pkg_path.read_bytes()
        assert content_sha256(raw.replace(b'"pet_fee"', b'"pet_price"', 1)) != \
            EXPECTED_PACKAGE_SHA
        assert content_sha256(raw + b" ") != EXPECTED_PACKAGE_SHA

    def test_public_profile_counts_match_the_seed_split(self):
        """15 published + 10 held == the 25 seed hotels. PTF-INVENTORY-001 moved
        one hotel across that line under an explicit tiered-fee approval."""
        contract = load_release_contract()
        published = contract["public_surface"]["public_hotel_profile_count"]
        excluded = contract["public_surface"]["excluded_public_profile_count"]
        assert published == 34
        assert excluded == 9
        assert published + excluded == 43

    def test_identities_derive_from_package_no_duplicated_allowlist(self):
        # The contract must NOT restate the 14 verified hotel identities.
        raw = RELEASE_CONTRACT_PATH.read_text(encoding="utf-8")
        for slug in _verified_slugs():
            assert slug not in raw, "contract duplicates a verified identity: %s" % slug
        # And no value in the contract is a 14-element identity list.
        contract = load_release_contract()

        def _walk(node):
            if isinstance(node, list):
                assert len(node) != 14, "contract holds a 14-element list (possible allow-list)"
                for x in node:
                    _walk(x)
            elif isinstance(node, dict):
                for x in node.values():
                    _walk(x)

        _walk(contract)


# --------------------------------------------------------------------------- #
# Header templates
# --------------------------------------------------------------------------- #

class TestHeaderTemplates:
    def test_both_parse(self):
        prod = parse_headers_file(HEADERS_PRODUCTION_PATH.read_text(encoding="utf-8"))
        prev = parse_headers_file(HEADERS_PREVIEW_PATH.read_text(encoding="utf-8"))
        assert "/*" in prod and "/*" in prev

    def test_preview_has_noindex_production_does_not(self):
        prod = parse_headers_file(HEADERS_PRODUCTION_PATH.read_text(encoding="utf-8"))["/*"]
        prev = parse_headers_file(HEADERS_PREVIEW_PATH.read_text(encoding="utf-8"))["/*"]
        assert "noindex" in prev.get("X-Robots-Tag", "").lower()
        assert "X-Robots-Tag" not in prod   # active directive; comments are ignored by the parser

    def test_required_security_headers_present(self):
        for path in (HEADERS_PRODUCTION_PATH, HEADERS_PREVIEW_PATH):
            root = parse_headers_file(path.read_text(encoding="utf-8"))["/*"]
            assert root.get("X-Content-Type-Options") == "nosniff"
            assert root.get("Referrer-Policy") == "strict-origin-when-cross-origin"
            assert root.get("X-Frame-Options") == "DENY"
            assert root.get("Cross-Origin-Opener-Policy") == "same-origin"
            assert "Permissions-Policy" in root

    def test_csp_is_report_only_and_not_enforced(self):
        for path in (HEADERS_PRODUCTION_PATH, HEADERS_PREVIEW_PATH):
            root = parse_headers_file(path.read_text(encoding="utf-8"))["/*"]
            assert "Content-Security-Policy-Report-Only" in root
            assert "Content-Security-Policy" not in root   # no ENFORCED CSP
            csp = root["Content-Security-Policy-Report-Only"]
            # Restrictive-where-safe directives.
            assert "object-src 'none'" in csp
            assert "base-uri 'self'" in csp
            assert "frame-ancestors 'none'" in csp
            # Inline script/style compatibility preserved (report-only pilot).
            assert "'unsafe-inline'" in csp
            assert "script-src 'self' 'unsafe-inline'" in csp
            assert "style-src 'self' 'unsafe-inline'" in csp

    def test_hsts_not_active(self):
        for path in (HEADERS_PRODUCTION_PATH, HEADERS_PREVIEW_PATH):
            for headers in parse_headers_file(path.read_text(encoding="utf-8")).values():
                assert "Strict-Transport-Security" not in headers

    def test_cache_policy_non_immutable_for_current_assets(self):
        prod = parse_headers_file(HEADERS_PRODUCTION_PATH.read_text(encoding="utf-8"))
        css = prod.get("/*.css", {})
        assert "Cache-Control" in css
        assert "immutable" not in css["Cache-Control"]
        assert "must-revalidate" in css["Cache-Control"]
        # HTML revalidates.
        assert "must-revalidate" in prod["/*"]["Cache-Control"]


# --------------------------------------------------------------------------- #
# Redirects
# --------------------------------------------------------------------------- #

class TestRedirects:
    def test_www_redirects_to_apex(self):
        rules = parse_redirects_file(REDIRECTS_PATH.read_text(encoding="utf-8"))
        www = [r for r in rules if "www.pettripfinder.com" in r[0]]
        assert www, "no www rule found"
        for src, dst, status in www:
            assert dst.startswith("https://pettripfinder.com")
            assert status.startswith("301")

    def test_no_apex_to_www_and_no_loop(self):
        rules = parse_redirects_file(REDIRECTS_PATH.read_text(encoding="utf-8"))
        for src, dst, _ in rules:
            # apex source must never redirect (would create host churn / loop risk)
            assert not re.match(r"^https?://pettripfinder\.com", src)
            assert "www.pettripfinder.com" not in dst

    def test_paths_preserved(self):
        rules = parse_redirects_file(REDIRECTS_PATH.read_text(encoding="utf-8"))
        for src, dst, _ in rules:
            if src.endswith("/*"):
                assert ":splat" in dst

    def test_no_spa_catch_all_and_no_go_rewrite(self):
        text = REDIRECTS_PATH.read_text(encoding="utf-8")
        rules = parse_redirects_file(text)
        for src, dst, status in rules:
            # No same-origin SPA catch-all serving index.html at 200.
            assert not (src.strip() in ("/*", "/*") and dst.endswith("/index.html") and status == "200")
            assert "/go/" not in src   # never rewrite the /go/ interstitials
        assert "/index.html   200" not in text.replace("  ", " ")


# --------------------------------------------------------------------------- #
# Assembler (full generation; module-scoped so it runs once per context).
# --------------------------------------------------------------------------- #

class _NetworkAttempt(RuntimeError):
    pass


@contextmanager
def _no_network():
    orig_connect = socket.socket.connect
    orig_create = socket.create_connection
    orig_getaddr = socket.getaddrinfo

    def _blocked(*a, **k):
        raise _NetworkAttempt("network access is forbidden during assembly")

    socket.socket.connect = _blocked
    socket.create_connection = _blocked
    socket.getaddrinfo = _blocked
    try:
        yield
    finally:
        socket.socket.connect = orig_connect
        socket.create_connection = orig_create
        socket.getaddrinfo = orig_getaddr


SENTINEL_TOKEN = "SENTINEL_NETLIFY_TOKEN_do_not_leak_ZZZ999"
SENTINEL_SITE = "SENTINEL_NETLIFY_SITE_ID_do_not_leak_ZZZ999"


@pytest.fixture(scope="module")
def assembled(tmp_path_factory):
    """Assemble both contexts once, under a no-network guard and with sentinel
    NETLIFY_* credentials in the environment. Success proves the assembler needs
    no network and never reads/leaks credentials."""
    prev_out = tmp_path_factory.mktemp("prod005a_preview")
    prod_out = tmp_path_factory.mktemp("prod005a_production")
    saved = {k: os.environ.get(k) for k in ("NETLIFY_AUTH_TOKEN", "NETLIFY_SITE_ID")}
    os.environ["NETLIFY_AUTH_TOKEN"] = SENTINEL_TOKEN
    os.environ["NETLIFY_SITE_ID"] = SENTINEL_SITE
    try:
        with _no_network():
            prev_manifest = assemble("preview", str(prev_out))
            prod_manifest = assemble("production", str(prod_out))
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return {
        "preview": {"root": Path(prev_out), "manifest": prev_manifest},
        "production": {"root": Path(prod_out), "manifest": prod_manifest},
    }


class TestAssembler:
    def test_reuses_existing_generator(self):
        # The assembler calls the committed generator; it does not reimplement it.
        assert asm.generate_site is generator_run

    def test_both_contexts_succeed(self, assembled):
        assert assembled["preview"]["manifest"]["all_gates_pass"] is True
        assert assembled["production"]["manifest"]["all_gates_pass"] is True

    def test_output_isolated_site_dir_only_publishable(self, assembled):
        for ctx in ("preview", "production"):
            root = assembled[ctx]["root"]
            assert (root / "site").is_dir()
            # Reports live OUTSIDE site/.
            for report in ("deployment_manifest.json", "file_hash_manifest.json",
                           "route_inventory.json", "validation_report.json"):
                assert (root / report).exists()
                assert not (root / "site" / report).exists()

    def test_no_build_reports_or_json_in_site(self, assembled):
        for ctx in ("preview", "production"):
            site = assembled[ctx]["root"] / "site"
            assert list(site.rglob("*.json")) == []
            for name in ("_build_report.json", "_broken_link_report.json",
                         "_quality_report.json", "bundle_manifest.json"):
                assert not (site / name).exists()

    def test_correct_headers_per_context(self, assembled):
        prev = (assembled["preview"]["root"] / "site" / "_headers").read_text(encoding="utf-8")
        prod = (assembled["production"]["root"] / "site" / "_headers").read_text(encoding="utf-8")
        assert prev == HEADERS_PREVIEW_PATH.read_text(encoding="utf-8")
        assert prod == HEADERS_PRODUCTION_PATH.read_text(encoding="utf-8")
        assert "noindex" in parse_headers_file(prev)["/*"].get("X-Robots-Tag", "").lower()
        assert "X-Robots-Tag" not in parse_headers_file(prod)["/*"]

    def test_redirects_copied_exactly(self, assembled):
        for ctx in ("preview", "production"):
            copied = (assembled[ctx]["root"] / "site" / "_redirects").read_bytes()
            assert copied == REDIRECTS_PATH.read_bytes()

    def test_exactly_fourteen_hotel_profiles(self, assembled):
        for ctx in ("preview", "production"):
            inv = json.loads((assembled[ctx]["root"] / "route_inventory.json").read_text(encoding="utf-8"))
            assert inv["hotel_profile_routes"] == 34
            assert len(inv["hotel_slugs"]) == 34

    def test_all_fourteen_committed_identities_present(self, assembled):
        verified = _verified_slugs()
        for ctx in ("preview", "production"):
            hotels = assembled[ctx]["root"] / "site" / "pet-friendly-hotels"
            for slug in verified:
                assert (hotels / slug / "index.html").exists(), slug

    def test_held_hotels_absent(self, assembled):
        for ctx in ("preview", "production"):
            inv = json.loads((assembled[ctx]["root"] / "route_inventory.json").read_text(encoding="utf-8"))
            assert len(inv["excluded_hotel_slugs"]) == 9
            hotels = assembled[ctx]["root"] / "site" / "pet-friendly-hotels"
            for slug in inv["excluded_hotel_slugs"]:
                assert not (hotels / slug).exists(), slug
            assert not (hotels / "drury-plaza-hotel-columbus-downtown").exists()

    def test_no_broken_links_and_gates_all_pass(self, assembled):
        for ctx in ("preview", "production"):
            report = json.loads((assembled[ctx]["root"] / "validation_report.json").read_text(encoding="utf-8"))
            assert report["all_gates_pass"] is True
            assert report["failing_gates"] == {}
            assert report["minimum_gates_missing"] == []
            assert report["gates"]["content.zero_broken_links"]["pass"] is True

    def test_no_forbidden_file_or_path(self, assembled):
        forbidden_ext = {".py", ".pyc", ".pyo", ".patch", ".map", ".json", ".env"}
        forbidden_seg = {".git", ".github", ".claude", ".netlify", "__pycache__",
                         "data", "docs", "tests", "scripts", "services", "launch_packages",
                         "engines", "repositories"}
        for ctx in ("preview", "production"):
            site = assembled[ctx]["root"] / "site"
            for p in site.rglob("*"):
                if not p.is_file():
                    continue
                rel = p.relative_to(site)
                assert p.suffix.lower() not in forbidden_ext, rel.as_posix()
                assert not (set(rel.parts) & forbidden_seg), rel.as_posix()

    def test_no_credential_or_secret_leak(self, assembled):
        for ctx in ("preview", "production"):
            root = assembled[ctx]["root"]
            for p in list((root / "site").rglob("*")) + [
                    root / "deployment_manifest.json", root / "file_hash_manifest.json",
                    root / "route_inventory.json", root / "validation_report.json"]:
                if not p.is_file():
                    continue
                text = p.read_text(encoding="utf-8", errors="ignore")
                assert SENTINEL_TOKEN not in text
                assert SENTINEL_SITE not in text
                assert "NETLIFY_AUTH_TOKEN" not in text
                assert "nfp_" not in text

    def test_no_runtime_or_operational_path_leak(self, assembled):
        needles = ("C:\\Atlas", "C:/Atlas", str(REPO_ROOT), "AppData",
                   "data/import", "/Users/")
        for ctx in ("preview", "production"):
            site = assembled[ctx]["root"] / "site"
            for p in site.rglob("*"):
                if p.is_file() and (p.suffix.lower() in {".html", ".css", ".txt", ".xml"}
                                    or p.name in {"_headers", "_redirects"}):
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    for needle in needles:
                        assert needle not in text, "%s in %s" % (needle, p)

    def test_no_netlify_dir_created(self, assembled):
        assert not (REPO_ROOT / ".netlify").exists()
        assert not (Path.cwd() / ".netlify").exists()
        for ctx in ("preview", "production"):
            assert not (assembled[ctx]["root"] / ".netlify").exists()

    def test_committed_package_unchanged_by_assembly(self, assembled):
        pkg = REPO_ROOT / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json"
        assert _sha256(pkg) == EXPECTED_PACKAGE_SHA

    def test_deterministic_and_atomic_replace(self, tmp_path):
        # Two production builds into the SAME dir (pre-seeded with a stale site/):
        # proves determinism AND that a pre-existing site/ is atomically replaced.
        out = tmp_path / "det"
        stale = out / "site"
        stale.mkdir(parents=True)
        (stale / "STALE_SENTINEL.txt").write_text("stale", encoding="utf-8")
        m1 = assemble("production", str(out))
        assert not (out / "site" / "STALE_SENTINEL.txt").exists()   # replaced
        h1 = json.loads((out / "file_hash_manifest.json").read_text(encoding="utf-8"))["bundle_sha256"]
        m2 = assemble("production", str(out))
        h2 = json.loads((out / "file_hash_manifest.json").read_text(encoding="utf-8"))["bundle_sha256"]
        assert m1["bundle_sha256"] == m2["bundle_sha256"] == h1 == h2


# --------------------------------------------------------------------------- #
# Fail-closed behavior (no full generation needed).
# --------------------------------------------------------------------------- #

class TestFailClosed:
    def test_invalid_context_rejected(self, tmp_path):
        with pytest.raises(AssembleError):
            assemble("staging", str(tmp_path / "x"))

    def test_invalid_package_hash_fails_before_output(self, tmp_path):
        contract = load_release_contract()
        contract["policy_package"] = dict(contract["policy_package"],
                                          expected_sha256="0" * 64)
        out = tmp_path / "badhash"
        with pytest.raises(AssembleError):
            assemble("production", str(out), contract=contract)
        assert not (out / "site").exists()               # no final output produced
        assert not (out / "deployment_manifest.json").exists()

    def test_pre_existing_output_not_overwritten_on_failure(self, tmp_path):
        out = tmp_path / "preexist"
        site = out / "site"
        site.mkdir(parents=True)
        (site / "KEEP.txt").write_text("keep", encoding="utf-8")
        contract = load_release_contract()
        contract["policy_package"] = dict(contract["policy_package"],
                                          expected_sha256="0" * 64)
        with pytest.raises(AssembleError):
            assemble("production", str(out), contract=contract)
        assert (site / "KEEP.txt").read_text(encoding="utf-8") == "keep"

    @pytest.mark.parametrize("bad", [
        "",                                  # repo root
        "scripts/pettripfinder/x",           # source tree
        "tests/pettripfinder/x",             # tests
        "launch_packages/pettripfinder/x",   # launch package
        "docs/pettripfinder/x",              # docs
        "data/import/x",                     # operational corpus
    ])
    def test_tracked_or_source_output_rejected(self, bad):
        with pytest.raises(AssembleError):
            validate_output_path(str(REPO_ROOT / bad) if bad else str(REPO_ROOT))

    def test_traversal_escape_rejected(self):
        with pytest.raises(AssembleError):
            validate_output_path("data/../scripts/escape")

    def test_symlink_escape_rejected(self, tmp_path):
        link = tmp_path / "link_into_scripts"
        try:
            os.symlink(REPO_ROOT / "scripts", link, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("symlink creation not permitted on this platform")
        with pytest.raises(AssembleError):
            validate_output_path(str(link / "escape"))

    def test_data_deployment_staging_allowed(self, tmp_path):
        # A path under the gitignored data/ tree (not data/import) is permitted.
        p = validate_output_path("data/deployment_staging/pettripfinder/prod005a_unit_ok")
        assert p.name == "prod005a_unit_ok"
        # And an outside-repo tmp path is permitted.
        assert validate_output_path(str(tmp_path / "ok")).name == "ok"
