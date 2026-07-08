"""Unit tests: ProjectStructureEngine and ImportPackageEngine."""

from engines.directory_builder.constants import PROJECT_DIRECTORIES, SCAFFOLD_TABLES
from engines.directory_builder.import_package_engine import ImportPackageEngine
from engines.directory_builder.structure_engine import ProjectStructureEngine


def test_structure_plan_contains_all_required_directories():
    plan = ProjectStructureEngine.build("demo-directory")
    assert plan.project_slug == "demo-directory"
    for required in ("config", "database", "imports", "content", "seo", "tasks",
                     "reports", "logs", "exports", "assets/images", "assets/templates", "documentation"):
        assert required in plan.directories
    assert plan.directories == tuple(PROJECT_DIRECTORIES)


def test_structure_plan_is_deterministic():
    assert ProjectStructureEngine.build("x") == ProjectStructureEngine.build("x")


def test_duplicate_businesses_removed(launch_package):
    imports = ImportPackageEngine.build(launch_package)
    names = [(b.name, b.location_id) for b in imports.businesses]
    assert len(names) == len(set(names))
    assert len(imports.businesses) == 4  # 5 seeds, 1 duplicate
    assert any("Alpha Services" in d for d in imports.duplicates_removed)


def test_ids_are_deterministic_and_stable(launch_package):
    a = ImportPackageEngine.build(launch_package)
    b = ImportPackageEngine.build(launch_package)
    assert a == b
    alpha = next(x for x in a.businesses if x.name == "Alpha Services")
    assert alpha.business_id.startswith("BIZ-")
    assert len(alpha.business_id) == len("BIZ-") + 10


def test_relationships_reference_existing_records(launch_package):
    imports = ImportPackageEngine.build(launch_package)
    business_ids = {b.business_id for b in imports.businesses}
    category_ids = {c.category_id for c in imports.categories}
    location_ids = {l.location_id for l in imports.locations}
    assert imports.relationships  # at least the fully-resolvable businesses
    for rel in imports.relationships:
        assert rel.business_id in business_ids
        assert rel.category_id in category_ids
        assert rel.location_id in location_ids


def test_unresolvable_category_yields_empty_reference(launch_package):
    imports = ImportPackageEngine.build(launch_package)
    ghost = next(b for b in imports.businesses if b.name == "Delta Undefined")
    assert ghost.category_id == ""
    assert ghost.location_id != ""


def test_tags_and_amenities_normalized(launch_package):
    imports = ImportPackageEngine.build(launch_package)
    alpha = next(b for b in imports.businesses if b.name == "Alpha Services")
    alpha_tags = sorted(t.tag for t in imports.tags if t.business_id == alpha.business_id)
    assert alpha_tags == ["insured", "licensed"]
    alpha_amenities = [a.amenity for a in imports.amenities if a.business_id == alpha.business_id]
    assert alpha_amenities == ["parking"]


def test_scaffold_tables_declared(launch_package):
    imports = ImportPackageEngine.build(launch_package)
    assert imports.scaffold_tables == tuple(SCAFFOLD_TABLES)
