"""Assembly Engine tests (AES-WEB-002J.10; AES-WEB-001 §5.9).

Covers the §19 matrix: public interface, determinism, route mapping, head
injection, SEO binding, CSS assembly, sitemap/robots, security, contract/
schema, and the integration boundary. Deterministic throughout: no clock/
UUID/randomness.
"""

from __future__ import annotations

import pytest

import engines.website_generation as wge
from engines.website_generation.assembly.assembly_builders import (
    build_robots,
    build_sitemap,
    inject_head,
    is_safe_url,
    route_to_output_path,
    stylesheet_href_for,
)
from engines.website_generation.assembly.assembly_engine import AssemblyEngine
from engines.website_generation.contracts.artifacts import (
    SiteBundle,
    artifact_sha256,
    canonical_artifact_json,
    sha256_of_text,
)
from engines.website_generation.contracts.errors import AssemblyError, WebsiteGenerationError
from engines.website_generation.contracts.interfaces import AssemblyEngineInterface

from . import DOC, assemble, brand_package, rendered_page_set, seo_entry, seo_package


def _files(bundle: SiteBundle):
    return {bf.path: bf.content for bf in bundle.files}


# --------------------------------------------------------------------------- #
# A. Public interface / version
# --------------------------------------------------------------------------- #

class TestPublicInterface:
    def test_assembly_engine_exported(self):
        assert "AssemblyEngine" in wge.__all__
        assert wge.AssemblyEngine is AssemblyEngine

    def test_interface_and_error_internal(self):
        assert "AssemblyEngineInterface" not in wge.__all__
        assert "AssemblyError" not in wge.__all__
        assert "SiteBundleV1" not in wge.__all__

    def test_bundle_file_exported(self):
        assert "BundleFile" in wge.__all__

    def test_implements_interface(self):
        assert issubclass(AssemblyEngine, AssemblyEngineInterface)
        assert isinstance(AssemblyEngine(), AssemblyEngineInterface)

    def test_engine_version_registered(self):
        # AES-WEB-002M.1 bumps 1.0.0 -> 1.1.0: assemble() gained an optional
        # listing_dataset input mapping bundle-authorized media assets into
        # the bundle (contracts/versions.py).
        assert wge.ENGINE_VERSIONS["assembly"] == "1.1.0"
        assert AssemblyEngine.version == "1.1.0"

    def test_assembly_error_shape(self):
        err = AssemblyError("boom", diagnostics={"x": 1})
        assert isinstance(err, WebsiteGenerationError)
        assert err.stage == "assembly"
        assert err.retryable is False


# --------------------------------------------------------------------------- #
# B. Output artifact / contract
# --------------------------------------------------------------------------- #

class TestOutputArtifact:
    def test_produces_site_bundle_1_2_0(self):
        # AES-WEB-002M.1: SiteBundle schema is now 1.2.0 (additive assets).
        bundle = assemble()
        assert isinstance(bundle, SiteBundle)
        assert bundle.schema_version == "1.2.0"
        assert bundle.artifact_kind.value == "SITE_BUNDLE"

    def test_file_map_matches_files_hashes(self):
        bundle = assemble()
        assert set(bundle.file_map) == {bf.path for bf in bundle.files}
        for bf in bundle.files:
            assert bundle.file_map[bf.path] == sha256_of_text(bf.content)

    def test_bundle_hash_is_hash_of_sorted_file_map(self):
        from engines.website_generation.contracts.artifacts import canonical_json

        bundle = assemble()
        assert bundle.bundle_hash == sha256_of_text(canonical_json(bundle.file_map))

    def test_source_hashes_complete(self):
        rps, seo, brand = rendered_page_set(), seo_package(), brand_package()
        bundle = AssemblyEngine().assemble(rps, seo, brand)
        assert bundle.source_hashes == {
            "rendered_page_set": artifact_sha256(rps),
            "seo_package": artifact_sha256(seo),
            "brand_package": artifact_sha256(brand),
        }

    def test_bundle_is_frozen(self):
        bundle = assemble()
        with pytest.raises(Exception):
            bundle.file_map = {}


# --------------------------------------------------------------------------- #
# C. Determinism
# --------------------------------------------------------------------------- #

class TestDeterminism:
    def test_equal_models_json_and_hash(self):
        rps = rendered_page_set(pages=(("/", DOC), ("/about", DOC)))
        seo = seo_package(
            entries=(seo_entry("/"), seo_entry("/about")),
            sitemap_routes=("/", "/about"),
        )
        a = AssemblyEngine().assemble(rps, seo, brand_package())
        b = AssemblyEngine().assemble(rps, seo, brand_package())
        assert a == b
        assert canonical_artifact_json(a) == canonical_artifact_json(b)
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_fresh_instances_byte_identical(self):
        rps, seo = rendered_page_set(), seo_package()
        a = AssemblyEngine().assemble(rps, seo, brand_package())
        b = AssemblyEngine().assemble(rps, seo, brand_package())
        assert _files(a) == _files(b)

    def test_page_order_independent(self):
        # The same pages supplied in opposite input order yield the same
        # assembled files, file_map, and bundle_hash (Assembly sorts
        # internally). Only source_hashes differ, because they faithfully
        # hash the two genuinely different input artifacts (different page
        # tuple order) -- that is correct provenance, not nondeterminism.
        seo = seo_package(entries=(seo_entry("/"), seo_entry("/a")), sitemap_routes=("/", "/a"))
        fwd = rendered_page_set(pages=(("/", DOC), ("/a", DOC)))
        rev = rendered_page_set(pages=(("/a", DOC), ("/", DOC)))
        a = AssemblyEngine().assemble(fwd, seo, brand_package())
        b = AssemblyEngine().assemble(rev, seo, brand_package())
        assert _files(a) == _files(b)
        assert a.file_map == b.file_map
        assert a.bundle_hash == b.bundle_hash

    def test_stable_diagnostics(self):
        def attempt():
            try:
                AssemblyEngine().assemble(rendered_page_set(), seo_package(entries=()), brand_package())
                return None
            except AssemblyError as e:
                return e.diagnostics
        assert attempt() == attempt()


# --------------------------------------------------------------------------- #
# D. Route mapping
# --------------------------------------------------------------------------- #

class TestRouteMapping:
    @pytest.mark.parametrize(
        "route,expected",
        [
            ("/", "index.html"),
            ("/about", "about/index.html"),
            ("/about/", "about/index.html"),
            ("/categories/dogs", "categories/dogs/index.html"),
            ("/a/b/c", "a/b/c/index.html"),
        ],
    )
    def test_route_to_path(self, route, expected):
        path, err = route_to_output_path(route)
        assert err is None
        assert path == expected

    @pytest.mark.parametrize(
        "route",
        ["", "about", "/../etc", "/a/../b", "/a//b", "/a/./b", "/C:/x", "/a\\b", "//host"],
    )
    def test_unsafe_routes_rejected(self, route):
        path, err = route_to_output_path(route)
        assert path is None
        assert err is not None

    def test_reserved_windows_name_rejected(self):
        path, err = route_to_output_path("/con")
        assert path is None

    def test_output_paths_are_relative_and_forward_slash(self):
        bundle = assemble(rendered_page_set(pages=(("/a/b", DOC),)),
                          seo_package(entries=(seo_entry("/a/b"),)))
        for bf in bundle.files:
            assert not bf.path.startswith("/")
            assert "\\" not in bf.path
            assert ".." not in bf.path.split("/")

    def test_duplicate_output_path_detected(self):
        # "/about" and "/about/" both map to about/index.html.
        rps = rendered_page_set(pages=(("/about", DOC), ("/about/", DOC)))
        seo = seo_package(
            entries=(seo_entry("/about"), seo_entry("/about/")),
            sitemap_routes=("/about",),
        )
        with pytest.raises(AssemblyError) as exc:
            AssemblyEngine().assemble(rps, seo, brand_package())
        assert "duplicate_output_paths" in exc.value.diagnostics


# --------------------------------------------------------------------------- #
# E. Head injection
# --------------------------------------------------------------------------- #

class TestHeadInjection:
    def test_title_meta_canonical_stylesheet_injected(self):
        bundle = assemble(
            rendered_page_set(),
            seo_package(entries=(seo_entry("/", title="Home", meta="Desc", canonical="/"),)),
        )
        html = _files(bundle)["index.html"]
        assert "<title>Home</title>" in html
        assert '<meta content="Desc" name="description">' in html
        assert '<link href="/" rel="canonical">' in html
        assert '<link href="styles.css" rel="stylesheet">' in html

    def test_body_preserved_byte_for_byte(self):
        bundle = assemble()
        html = _files(bundle)["index.html"]
        # everything after </head> is the Renderer's untouched output
        assert html.split("</head>")[1] == DOC.split("</head>")[1]

    def test_existing_head_meta_preserved(self):
        bundle = assemble()
        html = _files(bundle)["index.html"]
        assert '<meta charset="utf-8">' in html
        # injected content sits after the charset, before </head>
        assert html.index('charset="utf-8"') < html.index("<title>")
        assert html.index("<title>") < html.index("</head>")

    def test_injected_before_head_close_only(self):
        bundle = assemble()
        html = _files(bundle)["index.html"]
        assert html.count("</head>") == 1
        assert html.count("<title>") == 1

    def test_missing_head_is_diagnostic(self):
        rps = rendered_page_set(pages=(("/", "<html><body>no head</body></html>"),))
        with pytest.raises(AssemblyError) as exc:
            AssemblyEngine().assemble(rps, seo_package(), brand_package())
        assert "head_injection_failures" in exc.value.diagnostics

    def test_duplicate_head_is_diagnostic(self):
        rps = rendered_page_set(pages=(("/", "<html><head></head><head></head><body>x</body></html>"),))
        with pytest.raises(AssemblyError) as exc:
            AssemblyEngine().assemble(rps, seo_package(), brand_package())
        assert "head_injection_failures" in exc.value.diagnostics

    def test_empty_title_and_meta_omitted(self):
        from engines.website_generation.contracts.artifacts import SEOEntry

        # Construct SEOEntry directly so the empty title/meta are not
        # defaulted away by the seo_entry helper.
        entry = SEOEntry(route="/", title="", meta_description="", canonical_url="/")
        bundle = assemble(rendered_page_set(), seo_package(entries=(entry,)))
        html = _files(bundle)["index.html"]
        assert "<title>" not in html
        assert 'name="description"' not in html
        # canonical + stylesheet always present
        assert 'rel="canonical"' in html

    def test_no_json_ld_injected(self):
        # SEO Decision D4: no structured data exists in the SEO artifact, so
        # Assembly injects none (never invents it).
        bundle = assemble()
        html = _files(bundle)["index.html"]
        assert "application/ld+json" not in html
        assert "<script" not in html

    def test_alphabetical_attribute_order_in_injected_meta(self):
        bundle = assemble(
            rendered_page_set(),
            seo_package(entries=(seo_entry("/", meta="D", canonical="/"),)),
        )
        html = _files(bundle)["index.html"]
        # content before name (alphabetical)
        assert '<meta content="D" name="description">' in html


# --------------------------------------------------------------------------- #
# F. SEO binding
# --------------------------------------------------------------------------- #

class TestSeoBinding:
    def test_every_rendered_route_requires_seo(self):
        with pytest.raises(AssemblyError) as exc:
            AssemblyEngine().assemble(rendered_page_set(), seo_package(entries=()), brand_package())
        assert "missing_seo_routes" in exc.value.diagnostics

    def test_unknown_seo_route_rejected(self):
        seo = seo_package(entries=(seo_entry("/"), seo_entry("/ghost")))
        with pytest.raises(AssemblyError) as exc:
            AssemblyEngine().assemble(rendered_page_set(), seo, brand_package())
        assert "unknown_seo_routes" in exc.value.diagnostics

    def test_seo_bound_by_exact_route(self):
        rps = rendered_page_set(pages=(("/", DOC), ("/about", DOC)))
        seo = seo_package(
            entries=(
                seo_entry("/", title="HOME"),
                seo_entry("/about", title="ABOUT"),
            ),
            sitemap_routes=("/", "/about"),
        )
        files = _files(AssemblyEngine().assemble(rps, seo, brand_package()))
        assert "<title>HOME</title>" in files["index.html"]
        assert "<title>ABOUT</title>" in files["about/index.html"]

    def test_assembly_does_not_recompute_seo(self):
        # Whatever title the SEO artifact supplies is emitted verbatim
        # (escaped) -- Assembly never re-derives it.
        seo = seo_package(entries=(seo_entry("/", title="Exactly This Title"),))
        html = _files(assemble(rendered_page_set(), seo))["index.html"]
        assert "<title>Exactly This Title</title>" in html


# --------------------------------------------------------------------------- #
# G. CSS assembly
# --------------------------------------------------------------------------- #

class TestCssAssembly:
    def test_shared_css_is_a_single_bundle_entry(self):
        bundle = assemble(rendered_page_set(shared_css=":root{--x:1}"))
        files = _files(bundle)
        assert files["styles.css"] == ":root{--x:1}"
        assert list(bundle.file_map).count("styles.css") == 1

    def test_stylesheet_href_is_relative_per_depth(self):
        assert stylesheet_href_for("index.html") == "styles.css"
        assert stylesheet_href_for("about/index.html") == "../styles.css"
        assert stylesheet_href_for("a/b/index.html") == "../../styles.css"

    def test_nested_page_links_relative_stylesheet(self):
        bundle = assemble(
            rendered_page_set(pages=(("/a/b", DOC),)),
            seo_package(entries=(seo_entry("/a/b"),)),
        )
        html = _files(bundle)["a/b/index.html"]
        assert '<link href="../../styles.css" rel="stylesheet">' in html

    def test_no_external_stylesheet(self):
        html = _files(assemble())["index.html"]
        assert "http://" not in html
        assert "https://" not in html


# --------------------------------------------------------------------------- #
# H. Sitemap / robots
# --------------------------------------------------------------------------- #

class TestSitemapRobots:
    def test_sitemap_is_deterministic_xml(self):
        bundle = assemble(
            rendered_page_set(pages=(("/", DOC), ("/a", DOC))),
            seo_package(entries=(seo_entry("/"), seo_entry("/a")), sitemap_routes=("/", "/a")),
        )
        sitemap = _files(bundle)["sitemap.xml"]
        assert sitemap.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "<loc>/</loc>" in sitemap
        assert "<loc>/a</loc>" in sitemap
        assert sitemap.index("<loc>/</loc>") < sitemap.index("<loc>/a</loc>")

    def test_sitemap_xml_escaped(self):
        bundle = assemble(seo=seo_package(sitemap_routes=("/a&b<c>",)))
        sitemap = _files(bundle)["sitemap.xml"]
        assert "<loc>/a&amp;b&lt;c&gt;</loc>" in sitemap
        assert "/a&b<c>" not in sitemap

    def test_sitemap_no_invented_timestamp(self):
        sitemap = _files(assemble())["sitemap.xml"]
        assert "lastmod" not in sitemap

    def test_robots_from_directives(self):
        bundle = assemble(seo=seo_package(robots_directives=("User-agent: *", "Disallow: /admin")))
        robots = _files(bundle)["robots.txt"]
        assert robots == "User-agent: *\nDisallow: /admin\n"

    def test_robots_has_no_guessed_hostname(self):
        robots = _files(assemble())["robots.txt"]
        assert "http" not in robots
        assert "Sitemap:" not in robots  # requires absolute URL, none exists

    def test_builders_directly(self):
        assert build_sitemap(()) == (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
        )
        assert build_robots(("A", "B")) == "A\nB\n"


# --------------------------------------------------------------------------- #
# I. Security
# --------------------------------------------------------------------------- #

class TestSecurity:
    def test_malicious_title_escaped(self):
        seo = seo_package(entries=(seo_entry("/", title="<script>alert(1)</script>"),))
        html = _files(assemble(rendered_page_set(), seo))["index.html"]
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html

    def test_malicious_meta_escaped(self):
        seo = seo_package(entries=(seo_entry("/", meta='x" onload="evil'),))
        html = _files(assemble(rendered_page_set(), seo))["index.html"]
        assert 'onload="evil' not in html
        assert "&quot;" in html

    def test_unsafe_canonical_rejected(self):
        for bad in ("javascript:alert(1)", "data:text/html,x", "//evil.example.com"):
            seo = seo_package(entries=(seo_entry("/", canonical=bad),))
            with pytest.raises(AssemblyError) as exc:
                AssemblyEngine().assemble(rendered_page_set(), seo, brand_package())
            assert "unsafe_canonical_urls" in exc.value.diagnostics

    def test_unsafe_sitemap_url_rejected(self):
        seo = seo_package(sitemap_routes=("javascript:evil",))
        with pytest.raises(AssemblyError) as exc:
            AssemblyEngine().assemble(rendered_page_set(), seo, brand_package())
        assert "unsafe_sitemap_urls" in exc.value.diagnostics

    def test_route_traversal_rejected(self):
        rps = rendered_page_set(pages=(("/../secret", DOC),))
        seo = seo_package(entries=(seo_entry("/../secret"),), sitemap_routes=())
        with pytest.raises(AssemblyError) as exc:
            AssemblyEngine().assemble(rps, seo, brand_package())
        assert "invalid_output_paths" in exc.value.diagnostics

    def test_payload_hash_mismatch_rejected(self):
        rps = rendered_page_set(tamper_html_hash={"/": "deadbeef" * 8})
        with pytest.raises(AssemblyError) as exc:
            AssemblyEngine().assemble(rps, seo_package(), brand_package())
        assert "payload_hash_mismatches" in exc.value.diagnostics

    def test_css_hash_mismatch_rejected(self):
        rps = rendered_page_set(tamper_css_hash="deadbeef" * 8)
        with pytest.raises(AssemblyError) as exc:
            AssemblyEngine().assemble(rps, seo_package(), brand_package())
        assert "payload_hash_mismatches" in exc.value.diagnostics

    def test_no_local_path_or_metadata_leakage(self):
        html = _files(assemble())["index.html"]
        for marker in ("C:\\", "/Atlas/", "selection_trace", "registry_version", "build_id"):
            assert marker not in html

    def test_is_safe_url_primitive(self):
        assert is_safe_url("/ok") is True
        assert is_safe_url("#frag") is True
        assert is_safe_url("https://x.example") is True
        assert is_safe_url("javascript:x") is False
        assert is_safe_url("//host") is False
        assert is_safe_url("") is False

    def test_no_partial_bundle_on_error(self):
        # Even when only one of several pages is broken, nothing is returned.
        rps = rendered_page_set(pages=(("/", DOC), ("/bad", "<html><body>no head</body></html>")))
        seo = seo_package(entries=(seo_entry("/"), seo_entry("/bad")), sitemap_routes=("/",))
        result = None
        try:
            result = AssemblyEngine().assemble(rps, seo, brand_package())
        except AssemblyError:
            pass
        assert result is None


# --------------------------------------------------------------------------- #
# J. Integration boundary + purity
# --------------------------------------------------------------------------- #

class TestBoundary:
    def test_inputs_not_mutated(self):
        rps, seo, brand = rendered_page_set(), seo_package(), brand_package()
        before = (artifact_sha256(rps), artifact_sha256(seo), artifact_sha256(brand))
        AssemblyEngine().assemble(rps, seo, brand)
        after = (artifact_sha256(rps), artifact_sha256(seo), artifact_sha256(brand))
        assert before == after

    def test_final_html_hash_differs_from_rendered_hash(self):
        # Assembly produces new content (head injected), so the bundled
        # page's hash is not the Renderer's page hash -- and Assembly never
        # recomputes/overwrites the Renderer artifact.
        rps = rendered_page_set()
        bundle = AssemblyEngine().assemble(rps, seo_package(), brand_package())
        assert bundle.file_map["index.html"] != rps.pages[0].html_hash

    def test_head_injection_direct_helper(self):
        out, err = inject_head("<head></head>", "<title>x</title>")
        assert err is None
        assert out == "<head><title>x</title></head>"
        out2, err2 = inject_head("<html></html>", "x")
        assert out2 is None and err2 is not None
