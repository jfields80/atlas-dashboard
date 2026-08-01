"""Security and architectural boundaries, enforced by scanning the source.

Prose in an ADR cannot fail a build. These tests can. Each one corresponds to a
promise made in ADR-PTF-AUTOMATED-BROWSING or to an acceptance gate the operator
set, and each is written so that violating the promise breaks the suite rather
than merely contradicting a comment.
"""

from __future__ import annotations

import ast
import hashlib
import pathlib
import re

import pytest

from services.research_workers.capture_automation.doctrine import (
    BANNED_AUTOMATION_MARKERS, MIN_SECONDS_BETWEEN_HOTELS,
    OPERATOR_ONLY_FIELDS, PERMITTED_CHROME_FLAGS,
)

REPO = pathlib.Path(__file__).resolve().parents[3]
CAPTURE_PKG = REPO / "services" / "research_workers" / "capture_automation"
BROWSER_PKG = REPO / "services" / "research_workers" / "browser_control"
EXTENSION = REPO / "tools" / "pettripfinder_official_capture"


def py_files(*roots):
    for root in roots:
        for p in sorted(root.rglob("*.py")):
            yield p


def source_of(path: pathlib.Path) -> str:
    return path.read_text("utf-8")


class TestNoStealth:
    """No concealment, spoofing or evasion technique may enter the sprint."""

    @pytest.mark.parametrize("marker", BANNED_AUTOMATION_MARKERS)
    def test_marker_absent_from_source(self, marker):
        for path in py_files(CAPTURE_PKG, BROWSER_PKG):
            text = source_of(path)
            # doctrine.py is where the list itself lives.
            if path.name == "doctrine.py":
                continue
            assert marker not in text, "%s references banned %s" % (path.name, marker)

    def test_no_stealth_package_is_imported(self):
        banned_modules = {"playwright_stealth", "undetected_chromedriver",
                          "selenium_stealth", "puppeteer"}
        for path in py_files(CAPTURE_PKG, BROWSER_PKG):
            tree = ast.parse(source_of(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                for name in names:
                    root = name.split(".")[0]
                    assert root not in banned_modules, "%s imports %s" % (path.name, name)

    def test_chrome_flags_are_an_allowlist(self):
        from services.research_workers.browser_control.chrome_launcher import (
            LauncherError, assert_flags_permitted, build_flags,
        )
        assert_flags_permitted(build_flags(9222, pathlib.Path("/tmp/p")))
        for bad in ("--headless", "--proxy-server=http://x",
                    "--user-agent=Mozilla", "--disable-web-security"):
            with pytest.raises(LauncherError):
                assert_flags_permitted([bad])

    def test_the_launcher_never_hides_the_window(self):
        from services.research_workers.browser_control.chrome_launcher import build_flags
        flags = build_flags(9222, pathlib.Path("/tmp/p"))
        assert not any("headless" in f for f in flags)

    def test_a_dedicated_profile_is_mandatory(self):
        """The operator's normal Chrome profile is never a valid target: CDP on
        it would expose every live session on the machine."""
        from services.research_workers.browser_control.chrome_launcher import build_flags
        flags = build_flags(9222, pathlib.Path("/tmp/batch/.chrome-profile"))
        assert any(f.startswith("--user-data-dir=") for f in flags)


class TestNoNetworkOutsideTheBrowserSeam:
    """Every socket in the sprint lives in browser_control, and there is
    exactly one module there that opens one."""

    NETWORK_MODULES = {"socket", "requests", "urllib", "http", "httpx",
                       "aiohttp", "ftplib", "telnetlib", "smtplib", "websocket"}

    # Pure-parsing submodules that share a package name with a network one.
    # urllib.parse splits strings; it cannot open anything.
    PURE_SUBMODULES = {"urllib.parse"}

    def _is_network_import(self, name: str) -> bool:
        if name in self.PURE_SUBMODULES:
            return False
        return name.split(".")[0] in self.NETWORK_MODULES

    def test_capture_automation_opens_no_connection(self):
        for path in py_files(CAPTURE_PKG):
            tree = ast.parse(source_of(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module or ""]
                for name in names:
                    assert not self._is_network_import(name), (
                        "%s imports network module %s" % (path.name, name))

    def test_only_the_cdp_client_reaches_the_network(self):
        offenders = []
        for path in py_files(BROWSER_PKG):
            if path.name == "cdp_client.py":
                continue
            tree = ast.parse(source_of(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module or ""]
                for name in names:
                    if name.split(".")[0] in self.NETWORK_MODULES - {"socket"}:
                        offenders.append("%s:%s" % (path.name, name))
        assert not offenders, offenders

    def test_no_analytics_or_telemetry_endpoint_appears(self):
        for path in py_files(CAPTURE_PKG, BROWSER_PKG):
            text = source_of(path).lower()
            for marker in ("analytics", "telemetry", "segment.io", "mixpanel",
                           "sentry", "datadog"):
                assert marker not in text, "%s mentions %s" % (path.name, marker)


class TestNoAttestationOrPublication:
    """Automation gathers evidence; it never vouches for it, approves it, or
    publishes it. This is the load-bearing boundary of the whole sprint."""

    FORBIDDEN_SYMBOLS = (
        "build_attestation", "approve_attestation", "approve_attestation_record",
        "reject_attestation", "OperatorAffirmation", "ApprovalRecord",
        "OfficialAttestation", "store_screenshot", "verify_attestation_record",
    )

    @pytest.mark.parametrize("symbol", FORBIDDEN_SYMBOLS)
    def test_symbol_is_never_imported(self, symbol):
        for path in py_files(CAPTURE_PKG, BROWSER_PKG):
            tree = ast.parse(source_of(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        assert alias.name != symbol, (
                            "%s imports %s" % (path.name, symbol))

    def test_no_promotion_or_publication_module_is_imported(self):
        for path in py_files(CAPTURE_PKG, BROWSER_PKG):
            tree = ast.parse(source_of(path))
            for node in ast.walk(tree):
                mod = ""
                if isinstance(node, ast.ImportFrom) and node.level == 0:
                    mod = node.module or ""
                elif isinstance(node, ast.Import):
                    mod = node.names[0].name
                for banned in ("promote_attested_candidates",
                               "promote_worker_candidates",
                               "export_hotel_policy_facts",
                               "assemble_netlify_bundle",
                               "prod003_approvals"):
                    assert banned not in mod, "%s imports %s" % (path.name, mod)

    @pytest.mark.parametrize("field", OPERATOR_ONLY_FIELDS)
    def test_affirmation_field_is_never_assigned(self, field):
        """Automation may not populate a field that means 'a human looked'."""
        pattern = re.compile(r"""["']?%s["']?\s*[=:]\s*(True|["'][^"']+["'])"""
                             % re.escape(field))
        for path in py_files(CAPTURE_PKG, BROWSER_PKG):
            if path.name == "doctrine.py":
                continue
            assert not pattern.search(source_of(path)), (
                "%s assigns operator-only field %s" % (path.name, field))

    def test_the_written_payload_carries_a_null_affirmation(self):
        from services.research_workers.capture_automation.capture_writer import (
            build_payload,
        )
        from .conftest import snapshot_for
        payload = build_payload(snapshot_for("marriott-cmham.json"),
                                captured_at="t", requested_url="u")
        assert payload["automation"]["affirmation"] is None


class TestTheExtensionIsUntouched:
    """The manual path is the documented fallback for every exception. It is
    credible precisely because it did not change."""

    # sha256 as shipped by PTF-WORKERS-003/006 and PTF-CAPTURE-002 (2e84818).
    # PTF-CAPTURE-003 changes none of it -- not the code, not even the guide --
    # so the fallback an exception routes to is provably the same tool that has
    # captured every hotel published so far.
    EXPECTED = {
        "background.js":
            "a2716f7715707040adde038cc1ea3277731fabf8af64443433f17cc0d0b79159",
        "manifest.json":
            "d3c019a86c0e3745400831d8e71d2590b42cc4c9964a7031084d34ccb9ebd210",
        "CAPTURE_GUIDE.md":
            "4adb5af31c381bc1722ed15299291dabfaed8234c0d1753c5ca02932d7b89154",
    }

    @pytest.mark.parametrize("name", sorted(EXPECTED))
    def test_extension_file_is_byte_for_byte_unchanged(self, name):
        path = EXTENSION / name
        assert path.exists(), name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == self.EXPECTED[name], (
            "%s changed; PTF-CAPTURE-003 must not touch the manual fallback" % name)

    def test_the_directory_gained_no_files(self):
        assert sorted(p.name for p in EXTENSION.iterdir()) == sorted(self.EXPECTED)

    def test_no_python_in_this_sprint_writes_to_the_extension(self):
        for path in py_files(CAPTURE_PKG, BROWSER_PKG):
            text = source_of(path)
            assert "pettripfinder_official_capture" not in text, path.name

    def test_the_extension_still_declares_the_narrow_permission_set(self):
        import json
        manifest = json.loads((EXTENSION / "manifest.json").read_text("utf-8"))
        assert manifest["permissions"] == ["activeTab", "scripting", "downloads"]
        for forbidden in ("cookies", "history", "storage", "webRequest",
                          "<all_urls>", "tabs"):
            assert forbidden not in manifest["permissions"]

    def test_the_extension_still_makes_no_network_request(self):
        """Scans code only. The file's own header comment *describes* the
        absence of fetch() and WebSocket, so a naive substring scan would flag
        the very promise it is checking."""
        js = (EXTENSION / "background.js").read_text("utf-8")
        code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)          # block comments
        code = re.sub(r"^\s*//.*$", "", code, flags=re.M)        # line comments
        for marker in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon"):
            assert marker not in code, marker


class TestFileSystemBoundary:
    def test_writes_are_confined_to_the_batch_directory(self, tmp_path):
        from services.research_workers.capture_automation.capture_writer import (
            CaptureWriteError, build_payload, write_capture,
        )
        from .conftest import make_png, snapshot_for
        payload = build_payload(snapshot_for("marriott-cmham.json"),
                                captured_at="t", requested_url="u")
        for escape in ("../outside", "../../outside", "sub/../../outside"):
            with pytest.raises(CaptureWriteError, match="path_escapes"):
                write_capture(payload, make_png(4, 4),
                              output_dir=tmp_path / "batch", stem=escape)


class TestFixtureHygiene:
    """Checked-in fixtures must carry nothing personal.

    The first build of this corpus stripped query strings from the top-level
    url fields and left the JSON-LD blocks verbatim -- so four Hilton fixtures
    carried `sessionToken=<uuid>` from the operator's own browsing session,
    plus gclid/gbraid ad click ids. It was caught at `git add`, one command
    before those values would have entered git history permanently.

    Fixtures are derived from real pages, so this cannot be a one-time cleanup;
    it has to be a standing check that fails the build.
    """

    FIXTURES = pathlib.Path(__file__).parent / "fixtures"

    PRIVATE = re.compile(
        r"(?i)(sessiontoken|gclid|gbraid|wbraid|fbclid|msclkid|wt\.mc_id|"
        r"gclsrc|gad_source|gad_campaignid|utm_[a-z]+)")

    def _fixture_files(self):
        return sorted(self.FIXTURES.glob("*.json"))

    def test_the_corpus_exists(self):
        assert len(self._fixture_files()) >= 10

    @pytest.mark.parametrize("name", sorted(
        p.name for p in (pathlib.Path(__file__).parent / "fixtures").glob("*.json")))
    def test_no_private_parameter_anywhere_in_the_file(self, name):
        raw = (self.FIXTURES / name).read_text("utf-8")
        hit = self.PRIVATE.search(raw)
        assert hit is None, "%s carries %r" % (name, hit.group(0) if hit else "")

    @pytest.mark.parametrize("name", sorted(
        p.name for p in (pathlib.Path(__file__).parent / "fixtures").glob("*.json")))
    def test_no_url_carries_a_query_string(self, name):
        """Checked at every depth, including inside JSON-LD."""
        import json as _json
        raw = _json.loads((self.FIXTURES / name).read_text("utf-8"))
        urls = re.findall(r"https?://[^\s\"'<>\\]+", _json.dumps(raw))
        offenders = [u for u in urls if "?" in u]
        assert not offenders, offenders[:3]

    @pytest.mark.parametrize("name", sorted(
        p.name for p in (pathlib.Path(__file__).parent / "fixtures").glob("*.json")))
    def test_html_is_head_only(self, name):
        """Third-party page markup is not ours to redistribute; fixtures keep
        only the identity evidence the adapters read."""
        import json as _json
        html = _json.loads((self.FIXTURES / name).read_text("utf-8"))["html"]
        body = re.sub(r".*<body[^>]*>", "", html, flags=re.S)
        assert len(body) < 200, "%s carries page body markup" % name

    @pytest.mark.parametrize("name", sorted(
        p.name for p in (pathlib.Path(__file__).parent / "fixtures").glob("*.json")))
    def test_declared_hashes_match_the_content(self, name):
        import json as _json
        d = _json.loads((self.FIXTURES / name).read_text("utf-8"))
        for field, source in (("html_sha256", "html"), ("text_sha256", "text")):
            actual = hashlib.sha256(d[source].encode("utf-8")).hexdigest()
            assert d[field] == actual, "%s: %s stale" % (name, field)


class TestPacingCannotBeDisabled:
    def test_the_floor_is_a_module_constant(self):
        assert MIN_SECONDS_BETWEEN_HOTELS >= 20.0

    def test_the_cli_exposes_no_pacing_flag(self):
        """A flag would make the floor advisory."""
        from services.research_workers.cli import build_parser
        text = " ".join(build_parser().format_help().split())
        for flag in ("--min-pace", "--max-pace", "--no-pace", "--fast"):
            assert flag not in text


class TestReasonTableIsComplete:
    def test_every_reason_has_a_retry_and_an_explanation(self):
        from services.research_workers.capture_automation.reasons import (
            EXCEPTION_REASONS, RETRY_DISPOSITIONS,
        )
        for reason, (retry, explanation) in EXCEPTION_REASONS.items():
            assert retry in RETRY_DISPOSITIONS, reason
            assert explanation.strip(), reason

    def test_the_state_machine_refuses_an_undeclared_reason(self):
        from services.research_workers.capture_automation.state_machine import (
            NAVIGATING, StateError, fail,
        )
        with pytest.raises(StateError, match="undeclared reason"):
            fail(NAVIGATING, "SOMETHING_I_MADE_UP")
