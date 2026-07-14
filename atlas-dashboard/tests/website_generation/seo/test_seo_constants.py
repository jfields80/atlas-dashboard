"""SEO Engine constants sanity checks (AES-WEB-001 §5.8; AES-WEB-002J.5).

Cross-module role/slot-id consistency, byte-identical limit values, the
stdlib-only import discipline, and the no-floats rule -- kept separate from
behavioral engine tests (test_seo_engine.py) and validator-internal tests
(test_seo_validators.py).
"""

from __future__ import annotations

import ast
import inspect

from engines.website_generation.constants import seo as seo_constants
from engines.website_generation.constants.ia import (
    PAGE_ROLE_CATEGORY,
    PAGE_ROLE_HOME,
)
from engines.website_generation.constants.seo import (
    CANONICAL_URL_MAX_LENGTH,
    META_DESCRIPTION_MAX_LENGTH,
    META_DESCRIPTION_MIN_LENGTH,
    META_SOURCE_SLOT,
    META_SOURCE_SLOT_BY_ROLE,
    ROBOTS_DIRECTIVES,
    SITEMAP_FILENAME,
    ROBOTS_FILENAME,
    SUPPORTED_PAGE_ROLES,
    TITLE_MAX_LENGTH,
    TITLE_SEPARATOR,
    TITLE_SOURCE_SLOT,
    TITLE_SOURCE_SLOT_BY_ROLE,
)


class TestExistingLimitsUnchanged:
    """The four named limits and two filenames predate this sprint and must
    stay byte-identical (D1/D2/D3 build directly on them)."""

    def test_title_max_length(self):
        assert TITLE_MAX_LENGTH == 60

    def test_meta_description_max_length(self):
        assert META_DESCRIPTION_MAX_LENGTH == 160

    def test_meta_description_min_length(self):
        assert META_DESCRIPTION_MIN_LENGTH == 50

    def test_canonical_url_max_length(self):
        assert CANONICAL_URL_MAX_LENGTH == 2048

    def test_sitemap_filename_unchanged(self):
        assert SITEMAP_FILENAME == "sitemap.xml"

    def test_robots_filename_unchanged(self):
        assert ROBOTS_FILENAME == "robots.txt"


class TestRoleRuleTables:
    """Role-keyed rule tables (D1/D2) cover exactly the roles the IA Engine
    emits -- "add-an-entry-not-a-branch", mirroring constants/content.py's
    slot-length tables and constants/brand.py's per-family dict tables."""

    def test_title_source_slot_by_role_covers_exactly_home_category_and_profile(self):
        # AES-WEB-002K.1: business-profile pages need a real <title>/meta
        # description too (IA now emits them), same D1/D2 hero_h1/intro
        # source slots -- no new rule needed. PILOT-PTF-1: editorial-guide
        # (About/Methodology/Contact) needs the same treatment.
        assert set(TITLE_SOURCE_SLOT_BY_ROLE) == {
            "home", "category", "business-profile", "editorial-guide",
        }

    def test_meta_source_slot_by_role_covers_exactly_home_category_and_profile(self):
        assert set(META_SOURCE_SLOT_BY_ROLE) == {
            "home", "category", "business-profile", "editorial-guide",
        }

    def test_both_tables_share_the_same_role_key_set(self):
        assert set(TITLE_SOURCE_SLOT_BY_ROLE) == set(META_SOURCE_SLOT_BY_ROLE)

    def test_supported_page_roles_matches_the_table_keys_sorted(self):
        assert SUPPORTED_PAGE_ROLES == tuple(sorted(TITLE_SOURCE_SLOT_BY_ROLE))

    def test_every_role_resolves_to_hero_h1_and_intro(self):
        for role in SUPPORTED_PAGE_ROLES:
            assert TITLE_SOURCE_SLOT_BY_ROLE[role] == "hero_h1"
            assert META_SOURCE_SLOT_BY_ROLE[role] == "intro"

    def test_role_ids_match_ia_constants(self):
        # Independently declared (constants may not import constants); must
        # stay byte-identical to constants/ia.py's role ids, mirroring
        # test_content_constants.py's slot-id cross-module check.
        # "business-profile" (AES-WEB-002K.1) is independently declared as
        # a literal string here too -- it lives in
        # information_architecture_engine.py
        # (PAGE_ROLE_BUSINESS_PROFILE), not constants/ia.py, by the same
        # "profile pages carry no content_slots" design choice that keeps
        # it out of that module's role-keyed tables.
        assert set(SUPPORTED_PAGE_ROLES) == {
            PAGE_ROLE_HOME, PAGE_ROLE_CATEGORY, "business-profile", "editorial-guide",
        }


class TestSourceSlotConstants:
    def test_title_source_slot_is_hero_h1(self):
        assert TITLE_SOURCE_SLOT == "hero_h1"

    def test_meta_source_slot_is_intro(self):
        assert META_SOURCE_SLOT == "intro"


class TestTitleComposition:
    def test_separator_is_space_pipe_space(self):
        assert TITLE_SEPARATOR == " | "

    def test_template_documents_the_composition_rule(self):
        assert seo_constants.TITLE_TEMPLATE == "{hero_h1}" + TITLE_SEPARATOR + "{business_name}"


class TestRobotsPlan:
    def test_robots_directives_is_fixed_allow_all(self):
        assert ROBOTS_DIRECTIVES == ("User-agent: *", "Allow: /")


class TestConstantsModuleIsStdlibOnly:
    def test_no_non_stdlib_imports(self):
        path = inspect.getfile(seo_constants)
        tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
        allowed = {"typing"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert not node.level, "relative import found in constants/seo.py"
                names = [node.module.split(".")[0]] if node.module else []
            else:
                continue
            for name in names:
                assert name in allowed, "constants/seo.py imports non-stdlib %r" % name


class TestNoFloats:
    def test_no_float_values_in_module(self):
        for name in dir(seo_constants):
            if name.startswith("_"):
                continue
            value = getattr(seo_constants, name)
            assert not isinstance(value, float), name
            if isinstance(value, dict):
                assert all(not isinstance(v, float) for v in value.values()), name
            if isinstance(value, (tuple, list)):
                assert all(not isinstance(v, float) for v in value), name

    def test_no_float_literals_in_source(self):
        path = inspect.getfile(seo_constants)
        tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                raise AssertionError("float literal found in constants/seo.py")
