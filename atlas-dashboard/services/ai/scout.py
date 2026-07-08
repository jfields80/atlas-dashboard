import time

from services.connectors import CONNECTORS
from services.job_manager import JobManager
from services.repositories.business_repository import (
    BusinessRepository
)


class ScoutAI:

    def __init__(self):
        self.jobs = JobManager()
        self.businesses = BusinessRepository()

    @staticmethod
    def normalize_text(
        value
    ):
        return " ".join(
            str(value or "")
            .strip()
            .lower()
            .split()
        )

    @classmethod
    def build_business_key(
        cls,
        business
    ):
        business_name = cls.normalize_text(
            business.get(
                "business_name"
            )
            or business.get(
                "name"
            )
        )

        city = cls.normalize_text(
            business.get(
                "city"
            )
        )

        state = cls.normalize_text(
            business.get(
                "state"
            )
        )

        phone = "".join(
            character
            for character in str(
                business.get(
                    "phone",
                    ""
                )
            )
            if character.isdigit()
        )

        website = cls.normalize_text(
            business.get(
                "website"
            )
        )

        if website:
            website = (
                website
                .replace(
                    "https://",
                    ""
                )
                .replace(
                    "http://",
                    ""
                )
                .replace(
                    "www.",
                    ""
                )
                .rstrip("/")
            )

        return (
            business_name,
            city,
            state,
            phone,
            website
        )

    @staticmethod
    def prepare_business(
        business,
        project_id,
        source_name
    ):
        if not isinstance(
            business,
            dict
        ):
            return None

        prepared_business = dict(
            business
        )

        business_name = (
            prepared_business.get(
                "business_name"
            )
            or prepared_business.get(
                "name"
            )
            or ""
        )

        business_name = " ".join(
            str(business_name)
            .strip()
            .split()
        )

        if not business_name:
            return None

        prepared_business[
            "business_name"
        ] = business_name

        prepared_business[
            "project_id"
        ] = project_id

        prepared_business.setdefault(
            "source",
            source_name
        )

        for field_name in (
            "category",
            "city",
            "state",
            "phone",
            "website",
            "status"
        ):
            value = prepared_business.get(
                field_name,
                ""
            )

            if value is None:
                value = ""

            if isinstance(
                value,
                str
            ):
                value = " ".join(
                    value
                    .strip()
                    .split()
                )

            prepared_business[
                field_name
            ] = value

        return prepared_business

    def run(
        self,
        project_id,
        search_term,
        location,
        sources,
        max_results=20
    ):
        job_id = self.jobs.create_job(
            project_id,
            "Scout AI",
            search_term
        )

        print(
            "\n========== SCOUT AI =========="
        )

        print(
            f"Project     : {project_id}"
        )

        print(
            f"Search      : {search_term}"
        )

        print(
            f"Location    : {location}"
        )

        print(
            f"Sources     : "
            f"{', '.join(sources)}"
        )

        print(
            f"Max Results : {max_results}"
        )

        print(
            "==============================\n"
        )

        self.jobs.update_progress(
            job_id,
            10
        )

        total_inserted = 0
        total_updated = 0
        total_skipped = 0
        total_found = 0
        total_invalid = 0
        total_run_duplicates = 0

        seen_business_keys = set()

        source_count = max(
            len(sources),
            1
        )

        try:
            for source_index, source in enumerate(
                sources,
                start=1
            ):
                normalized_source = (
                    str(source)
                    .strip()
                    .lower()
                )

                connector_class = (
                    CONNECTORS.get(
                        normalized_source
                    )
                )

                if connector_class is None:
                    print(
                        "[WARNING] No connector "
                        f"registered for "
                        f"'{source}'"
                    )

                    total_skipped += 1

                    continue

                connector = connector_class()

                connector_name = getattr(
                    connector,
                    "name",
                    normalized_source
                )

                print(
                    "[SCOUT] Running "
                    f"{connector_name}"
                )

                connector_results = (
                    connector.search(
                        search_term,
                        location,
                        max_results=max_results
                    )
                )

                if connector_results is None:
                    connector_results = []

                if not isinstance(
                    connector_results,
                    list
                ):
                    connector_results = list(
                        connector_results
                    )

                total_found += len(
                    connector_results
                )

                for raw_business in (
                    connector_results
                ):
                    business = (
                        self.prepare_business(
                            raw_business,
                            project_id,
                            connector_name
                        )
                    )

                    if business is None:
                        total_invalid += 1
                        total_skipped += 1

                        print(
                            "[SCOUT] Skipped "
                            "invalid business record"
                        )

                        continue

                    business_key = (
                        self.build_business_key(
                            business
                        )
                    )

                    if not business_key[0]:
                        total_invalid += 1
                        total_skipped += 1

                        continue

                    if (
                        business_key
                        in seen_business_keys
                    ):
                        total_run_duplicates += 1
                        total_skipped += 1

                        print(
                            "[SCOUT] Skipped "
                            "duplicate result: "
                            f"{business['business_name']}"
                        )

                        continue

                    seen_business_keys.add(
                        business_key
                    )

                    result = (
                        self.businesses.save(
                            business
                        )
                    )

                    if not isinstance(
                        result,
                        dict
                    ):
                        result = {
                            "action": "skipped"
                        }

                    action = str(
                        result.get(
                            "action",
                            "skipped"
                        )
                    ).strip().lower()

                    if action == "inserted":
                        total_inserted += 1

                    elif action == "updated":
                        total_updated += 1

                    else:
                        total_skipped += 1

                progress = 10 + int(
                    (
                        source_index
                        / source_count
                    )
                    * 85
                )

                self.jobs.update_progress(
                    job_id,
                    min(
                        progress,
                        95
                    )
                )

            self.jobs.update_progress(
                job_id,
                100
            )

            time.sleep(
                0.25
            )

            self.jobs.complete_job(
                job_id
            )

        except Exception:
            try:
                self.jobs.complete_job(
                    job_id
                )

            except Exception:
                pass

            raise

        print(
            "\n========== COMPLETE =========="
        )

        print(
            f"Businesses Found    : "
            f"{total_found}"
        )

        print(
            f"New Records Saved   : "
            f"{total_inserted}"
        )

        print(
            f"Existing Updated    : "
            f"{total_updated}"
        )

        print(
            f"Records Skipped     : "
            f"{total_skipped}"
        )

        print(
            f"Run Duplicates      : "
            f"{total_run_duplicates}"
        )

        print(
            f"Invalid Records     : "
            f"{total_invalid}"
        )

        print(
            "==============================\n"
        )

        return {
            "found": total_found,
            "inserted": total_inserted,
            "updated": total_updated,
            "skipped": total_skipped,
            "run_duplicates": (
                total_run_duplicates
            ),
            "invalid": total_invalid
        }