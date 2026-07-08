import sqlite3

from urllib.parse import urlsplit

from config import DATABASE


class BusinessRepository:

    ENRICHMENT_FIELDS = (
        "email",
        "facebook_url",
        "instagram_url",
        "tiktok_url",
        "linkedin_url",
        "youtube_url",
        "contact_page_url",
        "contact_form_detected",
        "last_enriched_at"
    )

    def __init__(self):
        self.database = DATABASE

    def connect(self):
        connection = sqlite3.connect(
            self.database
        )

        connection.row_factory = (
            sqlite3.Row
        )

        return connection

    @staticmethod
    def clean_text(value):
        if value is None:
            return ""

        return " ".join(
            str(value)
            .strip()
            .split()
        )

    @classmethod
    def normalize_text(
        cls,
        value
    ):
        return (
            cls.clean_text(value)
            .casefold()
        )

    @classmethod
    def normalize_business_name(
        cls,
        value
    ):
        name = cls.normalize_text(
            value
        )

        replacements = {
            "&": "and",
            "’": "'"
        }

        for old_value, new_value in (
            replacements.items()
        ):
            name = name.replace(
                old_value,
                new_value
            )

        allowed_characters = []

        for character in name:
            if (
                character.isalnum()
                or character.isspace()
            ):
                allowed_characters.append(
                    character
                )

        return " ".join(
            "".join(
                allowed_characters
            ).split()
        )

    @classmethod
    def normalize_phone(
        cls,
        value
    ):
        cleaned_phone = cls.clean_text(
            value
        )

        digits = "".join(
            character
            for character in cleaned_phone
            if character.isdigit()
        )

        if len(digits) > 10:
            digits = digits[-10:]

        return digits

    @classmethod
    def normalize_website(
        cls,
        value
    ):
        website = cls.clean_text(
            value
        ).lower()

        if not website:
            return ""

        if not website.startswith(
            (
                "http://",
                "https://"
            )
        ):
            website = (
                f"https://{website}"
            )

        try:
            parsed = urlsplit(
                website
            )

        except ValueError:
            return ""

        hostname = (
            parsed.hostname
            or ""
        ).lower()

        if hostname.startswith(
            "www."
        ):
            hostname = hostname[4:]

        path = (
            parsed.path
            or ""
        ).rstrip("/")

        if path == "/":
            path = ""

        return (
            f"{hostname}{path}"
            if hostname
            else ""
        )

    @classmethod
    def normalize_email(
        cls,
        value
    ):
        return cls.clean_text(
            value
        ).lower()

    @classmethod
    def normalize_flag(
        cls,
        value
    ):
        if value in (
            1,
            True,
            "1",
            "true",
            "True",
            "yes",
            "Yes"
        ):
            return 1

        return 0

    @classmethod
    def normalize_location(
        cls,
        city,
        state
    ):
        return (
            cls.normalize_text(city),
            cls.normalize_text(state)
        )

    @classmethod
    def names_match(
        cls,
        first_name,
        second_name
    ):
        return (
            cls.normalize_business_name(
                first_name
            )
            ==
            cls.normalize_business_name(
                second_name
            )
        )

    def find_existing(
        self,
        cursor,
        project_id,
        business_name,
        city,
        state,
        phone="",
        website=""
    ):
        normalized_name = (
            self.normalize_business_name(
                business_name
            )
        )

        (
            normalized_city,
            normalized_state
        ) = self.normalize_location(
            city,
            state
        )

        normalized_phone = (
            self.normalize_phone(
                phone
            )
        )

        normalized_website = (
            self.normalize_website(
                website
            )
        )

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
            WHERE project_id = ?
            ORDER BY id
            """,
            (project_id,)
        )

        records = cursor.fetchall()

        for record in records:
            record_name = (
                self.normalize_business_name(
                    record[
                        "business_name"
                    ]
                )
            )

            (
                record_city,
                record_state
            ) = self.normalize_location(
                record["city"],
                record["state"]
            )

            same_name = (
                normalized_name
                and record_name
                and normalized_name
                == record_name
            )

            same_location = (
                normalized_city
                == record_city
                and normalized_state
                == record_state
            )

            if (
                same_name
                and same_location
            ):
                return record

            record_phone = (
                self.normalize_phone(
                    record["phone"]
                )
            )

            if (
                normalized_phone
                and record_phone
                and normalized_phone
                == record_phone
            ):
                return record

            record_website = (
                self.normalize_website(
                    record["website"]
                )
            )

            if (
                normalized_website
                and record_website
                and normalized_website
                == record_website
            ):
                return record

        return None

    @classmethod
    def choose_best_value(
        cls,
        existing_value,
        incoming_value
    ):
        existing = cls.clean_text(
            existing_value
        )

        incoming = cls.clean_text(
            incoming_value
        )

        if not existing:
            return incoming

        if not incoming:
            return existing

        if len(incoming) > len(existing):
            return incoming

        return existing

    @classmethod
    def choose_best_phone(
        cls,
        existing_value,
        incoming_value
    ):
        existing = cls.clean_text(
            existing_value
        )

        incoming = cls.clean_text(
            incoming_value
        )

        existing_normalized = (
            cls.normalize_phone(
                existing
            )
        )

        incoming_normalized = (
            cls.normalize_phone(
                incoming
            )
        )

        if not existing_normalized:
            return incoming

        if not incoming_normalized:
            return existing

        if (
            len(incoming_normalized)
            >
            len(existing_normalized)
        ):
            return incoming

        return existing

    @classmethod
    def choose_best_website(
        cls,
        existing_value,
        incoming_value
    ):
        existing = cls.clean_text(
            existing_value
        )

        incoming = cls.clean_text(
            incoming_value
        )

        existing_normalized = (
            cls.normalize_website(
                existing
            )
        )

        incoming_normalized = (
            cls.normalize_website(
                incoming
            )
        )

        if not existing_normalized:
            return incoming

        if not incoming_normalized:
            return existing

        if (
            len(incoming_normalized)
            >
            len(existing_normalized)
        ):
            return incoming

        return existing

    @classmethod
    def choose_best_email(
        cls,
        existing_value,
        incoming_value
    ):
        existing = cls.normalize_email(
            existing_value
        )

        incoming = cls.normalize_email(
            incoming_value
        )

        if not existing:
            return incoming

        if not incoming:
            return existing

        return existing

    @classmethod
    def choose_contact_form_flag(
        cls,
        existing_value,
        incoming_value
    ):
        return max(
            cls.normalize_flag(
                existing_value
            ),
            cls.normalize_flag(
                incoming_value
            )
        )

    @classmethod
    def status_score(
        cls,
        status
    ):
        normalized_status = (
            cls.normalize_text(
                status
            )
        )

        if normalized_status == (
            "verified"
        ):
            return 100

        if normalized_status == (
            "active"
        ):
            return 90

        if normalized_status.startswith(
            "found via google"
        ):
            return 70

        if normalized_status.startswith(
            "found via"
        ):
            return 60

        if normalized_status == (
            "found"
        ):
            return 50

        if normalized_status in {
            "pending",
            "review",
            "needs review"
        }:
            return 30

        if normalized_status == (
            "inactive"
        ):
            return 10

        return 0

    @classmethod
    def choose_best_status(
        cls,
        existing_status,
        incoming_status
    ):
        existing = cls.clean_text(
            existing_status
        )

        incoming = cls.clean_text(
            incoming_status
        )

        existing_score = (
            cls.status_score(
                existing
            )
        )

        incoming_score = (
            cls.status_score(
                incoming
            )
        )

        if incoming_score > existing_score:
            return incoming

        if existing:
            return existing

        return incoming

    @staticmethod
    def record_changed(
        existing,
        merged_values
    ):
        fields = (
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
            "contact_form_detected",
            "last_enriched_at",
            "status"
        )

        for field_name in fields:
            existing_value = (
                str(
                    existing[
                        field_name
                    ]
                    or ""
                ).strip()
            )

            merged_value = (
                str(
                    merged_values[
                        field_name
                    ]
                    or ""
                ).strip()
            )

            if (
                existing_value
                != merged_value
            ):
                return True

        return False

    def save(
        self,
        business
    ):
        project_id = int(
            business["project_id"]
        )

        business_name = (
            self.clean_text(
                business.get(
                    "business_name"
                )
            )
            or
            self.clean_text(
                business.get(
                    "name"
                )
            )
        )

        category = self.clean_text(
            business.get(
                "category"
            )
        )

        city = self.clean_text(
            business.get(
                "city"
            )
        )

        state = self.clean_text(
            business.get(
                "state"
            )
        )

        phone = self.clean_text(
            business.get(
                "phone"
            )
        )

        website = self.clean_text(
            business.get(
                "website"
            )
        )

        email = self.normalize_email(
            business.get(
                "email"
            )
        )

        facebook_url = self.clean_text(
            business.get(
                "facebook_url"
            )
        )

        instagram_url = self.clean_text(
            business.get(
                "instagram_url"
            )
        )

        tiktok_url = self.clean_text(
            business.get(
                "tiktok_url"
            )
        )

        linkedin_url = self.clean_text(
            business.get(
                "linkedin_url"
            )
        )

        youtube_url = self.clean_text(
            business.get(
                "youtube_url"
            )
        )

        contact_page_url = (
            self.clean_text(
                business.get(
                    "contact_page_url"
                )
            )
        )

        contact_form_detected = (
            self.normalize_flag(
                business.get(
                    "contact_form_detected"
                )
            )
        )

        last_enriched_at = (
            self.clean_text(
                business.get(
                    "last_enriched_at"
                )
            )
        )

        status = self.clean_text(
            business.get(
                "status"
            )
        )

        if not business_name:
            return {
                "action": "skipped",
                "reason": (
                    "Business name is required."
                ),
                "business_id": None
            }

        connection = self.connect()
        cursor = connection.cursor()

        try:
            existing = self.find_existing(
                cursor=cursor,
                project_id=project_id,
                business_name=business_name,
                city=city,
                state=state,
                phone=phone,
                website=website
            )

            if existing is None:
                cursor.execute(
                    """
                    INSERT INTO businesses
                    (
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
                    )
                    VALUES
                    (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
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
                    )
                )

                business_id = (
                    cursor.lastrowid
                )

                connection.commit()

                return {
                    "action": "inserted",
                    "business_id": (
                        business_id
                    )
                }

            merged_values = {
                "business_name": (
                    self.choose_best_value(
                        existing[
                            "business_name"
                        ],
                        business_name
                    )
                ),
                "category": (
                    self.choose_best_value(
                        existing[
                            "category"
                        ],
                        category
                    )
                ),
                "city": (
                    self.choose_best_value(
                        existing[
                            "city"
                        ],
                        city
                    )
                ),
                "state": (
                    self.choose_best_value(
                        existing[
                            "state"
                        ],
                        state
                    )
                ),
                "phone": (
                    self.choose_best_phone(
                        existing[
                            "phone"
                        ],
                        phone
                    )
                ),
                "website": (
                    self.choose_best_website(
                        existing[
                            "website"
                        ],
                        website
                    )
                ),
                "email": (
                    self.choose_best_email(
                        existing[
                            "email"
                        ],
                        email
                    )
                ),
                "facebook_url": (
                    self.choose_best_value(
                        existing[
                            "facebook_url"
                        ],
                        facebook_url
                    )
                ),
                "instagram_url": (
                    self.choose_best_value(
                        existing[
                            "instagram_url"
                        ],
                        instagram_url
                    )
                ),
                "tiktok_url": (
                    self.choose_best_value(
                        existing[
                            "tiktok_url"
                        ],
                        tiktok_url
                    )
                ),
                "linkedin_url": (
                    self.choose_best_value(
                        existing[
                            "linkedin_url"
                        ],
                        linkedin_url
                    )
                ),
                "youtube_url": (
                    self.choose_best_value(
                        existing[
                            "youtube_url"
                        ],
                        youtube_url
                    )
                ),
                "contact_page_url": (
                    self.choose_best_value(
                        existing[
                            "contact_page_url"
                        ],
                        contact_page_url
                    )
                ),
                "contact_form_detected": (
                    self.choose_contact_form_flag(
                        existing[
                            "contact_form_detected"
                        ],
                        contact_form_detected
                    )
                ),
                "last_enriched_at": (
                    self.choose_best_value(
                        existing[
                            "last_enriched_at"
                        ],
                        last_enriched_at
                    )
                ),
                "status": (
                    self.choose_best_status(
                        existing[
                            "status"
                        ],
                        status
                    )
                )
            }

            if not self.record_changed(
                existing,
                merged_values
            ):
                return {
                    "action": "skipped",
                    "reason": (
                        "Existing record already "
                        "contains the same data."
                    ),
                    "business_id": (
                        existing["id"]
                    )
                }

            cursor.execute(
                """
                UPDATE businesses
                SET
                    business_name = ?,
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
                    merged_values[
                        "business_name"
                    ],
                    merged_values[
                        "category"
                    ],
                    merged_values[
                        "city"
                    ],
                    merged_values[
                        "state"
                    ],
                    merged_values[
                        "phone"
                    ],
                    merged_values[
                        "website"
                    ],
                    merged_values[
                        "email"
                    ],
                    merged_values[
                        "facebook_url"
                    ],
                    merged_values[
                        "instagram_url"
                    ],
                    merged_values[
                        "tiktok_url"
                    ],
                    merged_values[
                        "linkedin_url"
                    ],
                    merged_values[
                        "youtube_url"
                    ],
                    merged_values[
                        "contact_page_url"
                    ],
                    merged_values[
                        "contact_form_detected"
                    ],
                    merged_values[
                        "last_enriched_at"
                    ],
                    merged_values[
                        "status"
                    ],
                    existing["id"]
                )
            )

            connection.commit()

            return {
                "action": "updated",
                "business_id": (
                    existing["id"]
                )
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def get_all(self):
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
            ORDER BY business_name
            """
        )

        rows = cursor.fetchall()

        connection.close()

        return [
            tuple(row)
            for row in rows
        ]

    def get_by_project(
        self,
        project_id
    ):
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
            WHERE project_id = ?
            ORDER BY business_name
            """,
            (project_id,)
        )

        rows = cursor.fetchall()

        connection.close()

        return [
            tuple(row)
            for row in rows
        ]

    def delete_all(self):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM businesses
            """
        )

        connection.commit()
        connection.close()

    def count(self):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM businesses
            """
        )

        total = cursor.fetchone()[0]

        connection.close()

        return total