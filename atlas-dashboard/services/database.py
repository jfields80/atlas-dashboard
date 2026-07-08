import sqlite3

from collections import defaultdict

from config import DATABASE


class Database:

    BUSINESS_ENRICHMENT_COLUMNS = {
        "email": "TEXT DEFAULT ''",
        "facebook_url": "TEXT DEFAULT ''",
        "instagram_url": "TEXT DEFAULT ''",
        "tiktok_url": "TEXT DEFAULT ''",
        "linkedin_url": "TEXT DEFAULT ''",
        "youtube_url": "TEXT DEFAULT ''",
        "contact_page_url": "TEXT DEFAULT ''",
        "contact_form_detected": (
            "INTEGER DEFAULT 0"
        ),
        "last_enriched_at": "TEXT DEFAULT ''"
    }

    def __init__(self):
        self.database = DATABASE

        self.ensure_business_enrichment_columns()

    def connect(self):
        connection = sqlite3.connect(
            self.database
        )

        connection.row_factory = (
            sqlite3.Row
        )

        return connection

    def ensure_business_enrichment_columns(
        self
    ):
        connection = sqlite3.connect(
            self.database
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            PRAGMA table_info(businesses)
            """
        )

        existing_columns = {
            row[1]
            for row in cursor.fetchall()
        }

        for (
            column_name,
            column_definition
        ) in (
            self.BUSINESS_ENRICHMENT_COLUMNS
            .items()
        ):
            if column_name in existing_columns:
                continue

            cursor.execute(
                f"""
                ALTER TABLE businesses
                ADD COLUMN {column_name}
                {column_definition}
                """
            )

        connection.commit()
        connection.close()

    def get_projects(self):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                name,
                status
            FROM projects
            ORDER BY name
            """
        )

        rows = cursor.fetchall()
        connection.close()

        return [
            (
                row["id"],
                row["name"],
                row["status"]
            )
            for row in rows
        ]

    def get_businesses(self):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                business_name,
                category,
                city,
                state,
                status
            FROM businesses
            ORDER BY business_name
            """
        )

        rows = cursor.fetchall()
        connection.close()

        return [
            (
                row["business_name"],
                row["category"],
                row["city"],
                row["state"],
                row["status"]
            )
            for row in rows
        ]

    def get_businesses_detailed(self):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                project_id,
                business_name,
                category,
                city,
                state,
                phone,
                website,
                email,
                facebook_url,
                instagram_url,
                tiktok_url,
                linkedin_url,
                youtube_url,
                contact_page_url,
                contact_form_detected,
                last_enriched_at,
                status
            FROM businesses
            ORDER BY
                business_name,
                city,
                state,
                id
            """
        )

        rows = cursor.fetchall()
        connection.close()

        return [
            dict(row)
            for row in rows
        ]

    def get_business_count(self):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM businesses
            """
        )

        count = cursor.fetchone()[0]

        connection.close()

        return count

    def get_sources(self):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                name,
                connector,
                enabled
            FROM research_sources
            WHERE enabled = 1
            ORDER BY name
            """
        )

        rows = cursor.fetchall()
        connection.close()

        return [
            (
                row["id"],
                row["name"],
                row["connector"],
                row["enabled"]
            )
            for row in rows
        ]

    @staticmethod
    def normalize_text(value):
        if value is None:
            return ""

        return " ".join(
            str(value)
            .strip()
            .lower()
            .split()
        )

    def get_duplicate_key(
        self,
        business
    ):
        return (
            business["project_id"],
            self.normalize_text(
                business["business_name"]
            ),
            self.normalize_text(
                business["city"]
            ),
            self.normalize_text(
                business["state"]
            )
        )

    @staticmethod
    def get_record_score(
        business
    ):
        score = 0

        fields = [
            "business_name",
            "category",
            "city",
            "state",
            "phone",
            "website",
            "email",
            "facebook_url",
            "instagram_url",
            "tiktok_url",
            "linkedin_url",
            "youtube_url",
            "contact_page_url",
            "last_enriched_at",
            "status"
        ]

        for field in fields:
            value = business.get(
                field
            )

            if (
                value is not None
                and str(value).strip()
            ):
                score += 1

        if business.get("phone"):
            score += 2

        if business.get("website"):
            score += 2

        if business.get("email"):
            score += 3

        social_fields = (
            "facebook_url",
            "instagram_url",
            "tiktok_url",
            "linkedin_url",
            "youtube_url"
        )

        for field in social_fields:
            if business.get(field):
                score += 1

        if business.get(
            "contact_page_url"
        ):
            score += 1

        if business.get(
            "contact_form_detected"
        ):
            score += 1

        if business.get("status"):
            normalized_status = str(
                business["status"]
            ).strip().lower()

            if normalized_status == (
                "verified"
            ):
                score += 3

            elif normalized_status.startswith(
                "found"
            ):
                score += 1

        return score

    def get_duplicate_groups(self):
        businesses = (
            self.get_businesses_detailed()
        )

        grouped_businesses = defaultdict(
            list
        )

        for business in businesses:
            key = self.get_duplicate_key(
                business
            )

            business_name = key[1]

            if not business_name:
                continue

            grouped_businesses[
                key
            ].append(
                business
            )

        duplicate_groups = []

        for (
            key,
            records
        ) in grouped_businesses.items():
            if len(records) < 2:
                continue

            ranked_records = sorted(
                records,
                key=lambda record: (
                    self.get_record_score(
                        record
                    ),
                    -record["id"]
                ),
                reverse=True
            )

            keep_record = (
                ranked_records[0]
            )

            remove_records = (
                ranked_records[1:]
            )

            duplicate_groups.append(
                {
                    "project_id": key[0],
                    "business_name": (
                        keep_record[
                            "business_name"
                        ]
                    ),
                    "city": (
                        keep_record[
                            "city"
                        ]
                        or ""
                    ),
                    "state": (
                        keep_record[
                            "state"
                        ]
                        or ""
                    ),
                    "record_count": len(
                        ranked_records
                    ),
                    "duplicate_count": len(
                        remove_records
                    ),
                    "keep_record": (
                        keep_record
                    ),
                    "remove_records": (
                        remove_records
                    )
                }
            )

        duplicate_groups.sort(
            key=lambda group: (
                self.normalize_text(
                    group[
                        "business_name"
                    ]
                ),
                self.normalize_text(
                    group["city"]
                ),
                self.normalize_text(
                    group["state"]
                )
            )
        )

        return duplicate_groups

    def get_duplicate_summary(self):
        duplicate_groups = (
            self.get_duplicate_groups()
        )

        duplicate_record_count = sum(
            group["duplicate_count"]
            for group in duplicate_groups
        )

        return {
            "group_count": len(
                duplicate_groups
            ),
            "duplicate_record_count": (
                duplicate_record_count
            ),
            "business_count": (
                self.get_business_count()
            )
        }

    @staticmethod
    def select_best_value(
        records,
        field
    ):
        values = []

        for record in records:
            value = record.get(
                field
            )

            if value is None:
                continue

            cleaned_value = str(
                value
            ).strip()

            if cleaned_value:
                values.append(
                    cleaned_value
                )

        if not values:
            return ""

        return max(
            values,
            key=lambda value: len(
                value
            )
        )

    @staticmethod
    def select_contact_form_value(
        records
    ):
        for record in records:
            value = record.get(
                "contact_form_detected"
            )

            if value in (
                1,
                True,
                "1",
                "true",
                "True"
            ):
                return 1

        return 0

    def select_best_status(
        self,
        records
    ):
        statuses = [
            self.normalize_text(
                record.get(
                    "status"
                )
            )
            for record in records
        ]

        if "verified" in statuses:
            return "Verified"

        for status in statuses:
            if status.startswith(
                "found via google"
            ):
                return self.select_best_value(
                    records,
                    "status"
                )

        if "active" in statuses:
            return "Active"

        return self.select_best_value(
            records,
            "status"
        )

    def merge_duplicate_group(
        self,
        connection,
        group
    ):
        cursor = connection.cursor()

        keep_record = group[
            "keep_record"
        ]

        all_records = [
            keep_record,
            *group["remove_records"]
        ]

        category = self.select_best_value(
            all_records,
            "category"
        )

        city = self.select_best_value(
            all_records,
            "city"
        )

        state = self.select_best_value(
            all_records,
            "state"
        )

        phone = self.select_best_value(
            all_records,
            "phone"
        )

        website = self.select_best_value(
            all_records,
            "website"
        )

        email = self.select_best_value(
            all_records,
            "email"
        )

        facebook_url = (
            self.select_best_value(
                all_records,
                "facebook_url"
            )
        )

        instagram_url = (
            self.select_best_value(
                all_records,
                "instagram_url"
            )
        )

        tiktok_url = (
            self.select_best_value(
                all_records,
                "tiktok_url"
            )
        )

        linkedin_url = (
            self.select_best_value(
                all_records,
                "linkedin_url"
            )
        )

        youtube_url = (
            self.select_best_value(
                all_records,
                "youtube_url"
            )
        )

        contact_page_url = (
            self.select_best_value(
                all_records,
                "contact_page_url"
            )
        )

        contact_form_detected = (
            self.select_contact_form_value(
                all_records
            )
        )

        last_enriched_at = (
            self.select_best_value(
                all_records,
                "last_enriched_at"
            )
        )

        status = self.select_best_status(
            all_records
        )

        cursor.execute(
            """
            UPDATE businesses
            SET
                category = ?,
                city = ?,
                state = ?,
                phone = ?,
                website = ?,
                email = ?,
                facebook_url = ?,
                instagram_url = ?,
                tiktok_url = ?,
                linkedin_url = ?,
                youtube_url = ?,
                contact_page_url = ?,
                contact_form_detected = ?,
                last_enriched_at = ?,
                status = ?
            WHERE id = ?
            """,
            (
                category,
                city,
                state,
                phone,
                website,
                email,
                facebook_url,
                instagram_url,
                tiktok_url,
                linkedin_url,
                youtube_url,
                contact_page_url,
                contact_form_detected,
                last_enriched_at,
                status,
                keep_record["id"]
            )
        )

        remove_ids = [
            record["id"]
            for record in group[
                "remove_records"
            ]
        ]

        if remove_ids:
            placeholders = ",".join(
                "?"
                for _ in remove_ids
            )

            cursor.execute(
                f"""
                DELETE FROM businesses
                WHERE id IN ({placeholders})
                """,
                remove_ids
            )

        return {
            "kept_id": (
                keep_record["id"]
            ),
            "removed_ids": (
                remove_ids
            )
        }

    def deduplicate_businesses(self):
        duplicate_groups = (
            self.get_duplicate_groups()
        )

        if not duplicate_groups:
            return {
                "groups_processed": 0,
                "records_removed": 0,
                "records_remaining": (
                    self.get_business_count()
                )
            }

        connection = self.connect()

        groups_processed = 0
        records_removed = 0

        try:
            connection.execute(
                "BEGIN"
            )

            for group in duplicate_groups:
                result = (
                    self.merge_duplicate_group(
                        connection,
                        group
                    )
                )

                groups_processed += 1

                records_removed += len(
                    result["removed_ids"]
                )

            connection.commit()

        except Exception:
            connection.rollback()
            connection.close()

            raise

        connection.close()

        return {
            "groups_processed": (
                groups_processed
            ),
            "records_removed": (
                records_removed
            ),
            "records_remaining": (
                self.get_business_count()
            )
        }