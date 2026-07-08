"""Section 8 — AI Build Queue Engine.

Aggregates every executable work unit for downstream AI operators:
content work items, listing verification, image collection, plus any
pre-planned tasks from the launch package's ai_task_queue.csv. Output is
a deterministic, priority-ordered queue of self-contained work units.
"""

from __future__ import annotations

from engines.directory_builder.models import (
    AiBuildQueue,
    AiWorkUnit,
    ContentBuildPackage,
    ImagePackage,
    ImportPackage,
)
from engines.directory_builder.models import LaunchPackage
from engines.directory_builder.constants import (
    ID_PREFIX_WORK_UNIT,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
)
from engines.directory_builder.deterministic import deterministic_id

ENGINE_VERSION = "1.0.0"

UNIT_TYPE_CONTENT = "content"
UNIT_TYPE_VERIFY_LISTING = "verify_listing"
UNIT_TYPE_COLLECT_IMAGE = "collect_image"
UNIT_TYPE_PLANNED_TASK = "planned_task"


class AiBuildQueueEngine:
    VERSION = ENGINE_VERSION

    @staticmethod
    def build(
        package: LaunchPackage,
        imports: ImportPackage,
        content: ContentBuildPackage,
        images: ImagePackage,
    ) -> AiBuildQueue:
        units: list[AiWorkUnit] = []

        # Pre-planned tasks from the launch package.
        for task in package.ai_task_queue:
            units.append(
                AiWorkUnit(
                    unit_id=deterministic_id(ID_PREFIX_WORK_UNIT, UNIT_TYPE_PLANNED_TASK, task.task_type, task.description),
                    unit_type=UNIT_TYPE_PLANNED_TASK,
                    title=task.task_type,
                    instructions=task.description,
                    priority=task.priority,
                )
            )

        # Every content work item becomes an executable unit.
        for item in content.items:
            units.append(
                AiWorkUnit(
                    unit_id=deterministic_id(ID_PREFIX_WORK_UNIT, UNIT_TYPE_CONTENT, item.item_id),
                    unit_type=UNIT_TYPE_CONTENT,
                    title=item.title,
                    instructions=item.instructions,
                    priority=item.priority,
                    depends_on=(item.item_id,),
                )
            )

        # Verify every imported listing.
        for biz in imports.businesses:
            units.append(
                AiWorkUnit(
                    unit_id=deterministic_id(ID_PREFIX_WORK_UNIT, UNIT_TYPE_VERIFY_LISTING, biz.business_id),
                    unit_type=UNIT_TYPE_VERIFY_LISTING,
                    title=f"Verify listing: {biz.name}",
                    instructions=(
                        f"Verify name, address, phone, and website for '{biz.name}' "
                        f"({biz.business_id}) against authoritative sources."
                    ),
                    priority=PRIORITY_HIGH,
                )
            )

        # Collect every specified image.
        for spec in images.specs:
            units.append(
                AiWorkUnit(
                    unit_id=deterministic_id(ID_PREFIX_WORK_UNIT, UNIT_TYPE_COLLECT_IMAGE, spec.spec_id),
                    unit_type=UNIT_TYPE_COLLECT_IMAGE,
                    title=f"Collect image: {spec.file_name}",
                    instructions=(
                        f"Source or commission a {spec.width}x{spec.height} {spec.image_format} "
                        f"{spec.image_type} image of '{spec.subject}'. Save as {spec.file_name}."
                    ),
                    priority=PRIORITY_MEDIUM,
                    depends_on=(spec.spec_id,),
                )
            )

        units.sort(key=lambda u: (u.priority, u.unit_type, u.unit_id))
        return AiBuildQueue(units=tuple(units))
