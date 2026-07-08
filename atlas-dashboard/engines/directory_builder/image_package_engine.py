"""Section 5 — Image Package Engine.

Generates image *specifications* only. Never generates images. Every spec
carries deterministic dimensions, format, and a standards-conforming
file name so downstream collection work is unambiguous.
"""

from __future__ import annotations

from engines.directory_builder.models import ImagePackage, ImageSpec, ImportPackage
from engines.directory_builder.models import LaunchPackage
from engines.directory_builder.constants import (
    ID_PREFIX_IMAGE_SPEC,
    IMAGE_DIMENSIONS,
    IMAGE_FORMAT_DEFAULT,
    IMAGE_FORMAT_LOGO,
    IMAGE_NAMING_STANDARD,
    IMAGE_TYPE_BUSINESS,
    IMAGE_TYPE_CATEGORY,
    IMAGE_TYPE_HERO,
    IMAGE_TYPE_ICON,
    IMAGE_TYPE_LOCATION,
    IMAGE_TYPE_LOGO,
    IMAGE_TYPE_PLACEHOLDER,
)
from engines.directory_builder.deterministic import deterministic_id, slugify

ENGINE_VERSION = "1.0.0"


class ImagePackageEngine:
    VERSION = ENGINE_VERSION

    @staticmethod
    def build(package: LaunchPackage, imports: ImportPackage) -> ImagePackage:
        specs: list[ImageSpec] = []
        site = package.blueprint.project_name

        def spec(image_type: str, subject: str, notes: str = "", image_format: str = IMAGE_FORMAT_DEFAULT) -> ImageSpec:
            width, height = IMAGE_DIMENSIONS[image_type]
            subject_slug = slugify(subject) or "site"
            file_name = IMAGE_NAMING_STANDARD.format(
                image_type=image_type,
                subject_slug=subject_slug,
                width=width,
                height=height,
                ext=image_format,
            )
            return ImageSpec(
                spec_id=deterministic_id(ID_PREFIX_IMAGE_SPEC, image_type, subject_slug),
                image_type=image_type,
                subject=subject,
                subject_slug=subject_slug,
                width=width,
                height=height,
                file_name=file_name,
                image_format=image_format,
                notes=notes,
            )

        specs.append(spec(IMAGE_TYPE_HERO, site, notes="Homepage hero. Convey the niche instantly."))
        specs.append(spec(IMAGE_TYPE_LOGO, site, notes="Primary logo, transparent background.", image_format=IMAGE_FORMAT_LOGO))
        specs.append(spec(IMAGE_TYPE_ICON, site, notes="Favicon / app icon derived from logo.", image_format=IMAGE_FORMAT_LOGO))
        specs.append(spec(IMAGE_TYPE_PLACEHOLDER, f"{site} listing placeholder", notes="Shown when a business has no image."))

        for cat in imports.categories:
            specs.append(spec(IMAGE_TYPE_CATEGORY, cat.name, notes=f"Category header for '{cat.name}'."))
        for loc in imports.locations:
            specs.append(spec(IMAGE_TYPE_LOCATION, f"{loc.city} {loc.state}", notes=f"Location header for {loc.city}, {loc.state}."))
        for biz in imports.businesses:
            specs.append(spec(IMAGE_TYPE_BUSINESS, biz.name, notes=f"Primary listing image for '{biz.name}'."))

        specs.sort(key=lambda s: (s.image_type, s.subject_slug))
        return ImagePackage(
            specs=tuple(specs),
            naming_standard=IMAGE_NAMING_STANDARD,
            dimension_standards=tuple(
                (image_type, dims[0], dims[1]) for image_type, dims in sorted(IMAGE_DIMENSIONS.items())
            ),
        )
