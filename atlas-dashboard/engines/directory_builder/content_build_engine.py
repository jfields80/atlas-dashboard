"""Section 4 — Content Build Package Engine.

Turns the content plan plus derived gaps (missing business descriptions,
SEO metadata, image ALT text) into deterministic, executable AI work
items. Produces work specifications only — never generated content.
"""

from __future__ import annotations

from engines.directory_builder.models import (
    ContentBuildPackage,
    ContentWorkItem,
    ImagePackage,
    ImportPackage,
    SeoBuildPackage,
)
from engines.directory_builder.models import LaunchPackage
from engines.directory_builder.constants import (
    CONTENT_TYPE_TO_WORK_TYPE,
    DEFAULT_WORK_TYPE,
    ID_PREFIX_CONTENT_ITEM,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    WORK_TYPE_BUSINESS_DESCRIPTION,
    WORK_TYPE_IMAGE_ALT_TEXT,
    WORK_TYPE_SEO_METADATA,
)
from engines.directory_builder.deterministic import deterministic_id

ENGINE_VERSION = "1.0.0"


class ContentBuildEngine:
    VERSION = ENGINE_VERSION

    @staticmethod
    def build(
        package: LaunchPackage,
        imports: ImportPackage,
        seo: SeoBuildPackage,
        images: ImagePackage,
    ) -> ContentBuildPackage:
        items: list[ContentWorkItem] = []

        # Planned editorial content (articles, guides, FAQs, comparisons, city/category pages)
        for entry in package.content_plan:
            work_type = CONTENT_TYPE_TO_WORK_TYPE.get(entry.content_type.strip().lower(), DEFAULT_WORK_TYPE)
            items.append(
                ContentWorkItem(
                    item_id=deterministic_id(ID_PREFIX_CONTENT_ITEM, work_type, entry.title),
                    work_type=work_type,
                    title=entry.title,
                    target_keyword=entry.target_keyword,
                    priority=entry.priority,
                    instructions=(
                        f"Write {work_type.replace('_', ' ')} content titled '{entry.title}'"
                        + (f" targeting keyword '{entry.target_keyword}'." if entry.target_keyword else ".")
                    ),
                )
            )

        # Business descriptions for every business missing one
        for biz in imports.businesses:
            if biz.description.strip():
                continue
            items.append(
                ContentWorkItem(
                    item_id=deterministic_id(ID_PREFIX_CONTENT_ITEM, WORK_TYPE_BUSINESS_DESCRIPTION, biz.business_id),
                    work_type=WORK_TYPE_BUSINESS_DESCRIPTION,
                    title=f"Description: {biz.name}",
                    target_path=f"business:{biz.business_id}",
                    priority=PRIORITY_HIGH,
                    instructions=f"Write a 60-120 word factual listing description for '{biz.name}'.",
                )
            )

        # SEO metadata for every generated page (title tag + meta description review)
        for page in seo.pages:
            items.append(
                ContentWorkItem(
                    item_id=deterministic_id(ID_PREFIX_CONTENT_ITEM, WORK_TYPE_SEO_METADATA, page.page_id),
                    work_type=WORK_TYPE_SEO_METADATA,
                    title=f"Metadata: {page.url_path}",
                    target_path=page.url_path,
                    priority=PRIORITY_HIGH,
                    instructions=(
                        f"Finalize title tag and meta description for {page.url_path} "
                        f"(draft title: '{page.title}')."
                    ),
                )
            )

        # ALT text for every image specification
        for spec in images.specs:
            items.append(
                ContentWorkItem(
                    item_id=deterministic_id(ID_PREFIX_CONTENT_ITEM, WORK_TYPE_IMAGE_ALT_TEXT, spec.spec_id),
                    work_type=WORK_TYPE_IMAGE_ALT_TEXT,
                    title=f"ALT text: {spec.file_name}",
                    target_path=spec.file_name,
                    priority=PRIORITY_LOW,
                    instructions=f"Write descriptive ALT text for {spec.image_type} image of '{spec.subject}'.",
                )
            )

        items.sort(key=lambda i: (i.priority, i.work_type, i.item_id))
        return ContentBuildPackage(items=tuple(items))
