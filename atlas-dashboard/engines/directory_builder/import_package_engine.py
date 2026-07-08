"""Section 2 — Database Import Package Engine.

Normalizes seed data into import-ready records: businesses, categories,
locations, relationships, tags, amenities, plus header-only scaffolds for
the remaining directory tables. No SQL. Pure computation.

Deduplication key for a business: (name, city, state), case-insensitive.
First occurrence in sorted order wins; removed duplicates are reported.
"""

from __future__ import annotations

from engines.directory_builder.models import (
    AmenityRecord,
    BusinessRecord,
    CategoryRecord,
    ImportPackage,
    LocationRecord,
    RelationshipRecord,
    TagRecord,
)
from engines.directory_builder.models import LaunchPackage
from engines.directory_builder.constants import (
    ID_PREFIX_AMENITY,
    ID_PREFIX_BUSINESS,
    ID_PREFIX_CATEGORY,
    ID_PREFIX_LOCATION,
    ID_PREFIX_RELATIONSHIP,
    ID_PREFIX_TAG,
    SCAFFOLD_TABLES,
)
from engines.directory_builder.deterministic import deterministic_id, slugify

ENGINE_VERSION = "1.0.0"


class ImportPackageEngine:
    VERSION = ENGINE_VERSION

    @staticmethod
    def build(package: LaunchPackage) -> ImportPackage:
        categories = ImportPackageEngine._categories(package)
        locations = ImportPackageEngine._locations(package)
        cat_by_slug = {c.slug: c for c in categories}
        loc_by_slug = {l.slug: l for l in locations}

        businesses: list[BusinessRecord] = []
        relationships: list[RelationshipRecord] = []
        tags: list[TagRecord] = []
        amenities: list[AmenityRecord] = []
        duplicates: list[str] = []
        seen_keys: set[tuple[str, str, str]] = set()

        for biz in sorted(package.seed_businesses, key=lambda b: (b.name.lower(), b.city.lower(), b.state.lower())):
            key = (biz.name.strip().lower(), biz.city.strip().lower(), biz.state.strip().lower())
            if key in seen_keys:
                duplicates.append(f"{biz.name} ({biz.city}, {biz.state})")
                continue
            seen_keys.add(key)

            business_id = deterministic_id(ID_PREFIX_BUSINESS, biz.name, biz.city, biz.state)
            category = cat_by_slug.get(slugify(biz.category))
            location = loc_by_slug.get(slugify(f"{biz.city}-{biz.state}"))
            category_id = category.category_id if category else ""
            location_id = location.location_id if location else ""

            businesses.append(
                BusinessRecord(
                    business_id=business_id,
                    name=biz.name,
                    slug=slugify(biz.name),
                    category_id=category_id,
                    location_id=location_id,
                    website=biz.website,
                    phone=biz.phone,
                    description=biz.description,
                )
            )
            if category_id and location_id:
                relationships.append(
                    RelationshipRecord(
                        relationship_id=deterministic_id(
                            ID_PREFIX_RELATIONSHIP, business_id, category_id, location_id
                        ),
                        business_id=business_id,
                        category_id=category_id,
                        location_id=location_id,
                    )
                )
            for tag in sorted({t.strip() for t in biz.tags if t.strip()}, key=str.lower):
                tags.append(
                    TagRecord(
                        tag_id=deterministic_id(ID_PREFIX_TAG, business_id, tag),
                        business_id=business_id,
                        tag=tag,
                    )
                )
            for amenity in sorted({a.strip() for a in biz.amenities if a.strip()}, key=str.lower):
                amenities.append(
                    AmenityRecord(
                        amenity_id=deterministic_id(ID_PREFIX_AMENITY, business_id, amenity),
                        business_id=business_id,
                        amenity=amenity,
                    )
                )

        return ImportPackage(
            businesses=tuple(businesses),
            categories=categories,
            locations=locations,
            relationships=tuple(relationships),
            tags=tuple(tags),
            amenities=tuple(amenities),
            scaffold_tables=tuple(SCAFFOLD_TABLES),
            duplicates_removed=tuple(duplicates),
        )

    @staticmethod
    def _categories(package: LaunchPackage) -> tuple[CategoryRecord, ...]:
        records = []
        for cat in sorted(package.categories, key=lambda c: c.slug):
            records.append(
                CategoryRecord(
                    category_id=deterministic_id(ID_PREFIX_CATEGORY, cat.slug),
                    name=cat.name,
                    slug=cat.slug,
                    description=cat.description,
                )
            )
        return tuple(records)

    @staticmethod
    def _locations(package: LaunchPackage) -> tuple[LocationRecord, ...]:
        records = []
        for loc in sorted(package.locations, key=lambda l: l.slug):
            records.append(
                LocationRecord(
                    location_id=deterministic_id(ID_PREFIX_LOCATION, loc.slug),
                    city=loc.city,
                    state=loc.state,
                    slug=loc.slug,
                )
            )
        return tuple(records)
