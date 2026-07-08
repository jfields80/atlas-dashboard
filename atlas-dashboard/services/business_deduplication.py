import shutil
from datetime import datetime
from pathlib import Path

from config import DATABASE
from services.database import Database


class BusinessDeduplicationService:

    def __init__(self):
        self.database = Database()
        self.database_path = Path(DATABASE)

        self.backup_directory = (
            self.database_path.parent
            / "backups"
        )

    def get_merge_preview(self):
        duplicate_groups = (
            self.database.get_duplicate_groups()
        )

        duplicate_summary = (
            self.database.get_duplicate_summary()
        )

        return {
            "groups": duplicate_groups,
            "summary": duplicate_summary
        }

    def create_backup(self):
        if not self.database_path.exists():
            raise FileNotFoundError(
                f"Atlas database was not found: "
                f"{self.database_path}"
            )

        self.backup_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup_filename = (
            f"atlas_before_deduplication_"
            f"{timestamp}.db"
        )

        backup_path = (
            self.backup_directory
            / backup_filename
        )

        shutil.copy2(
            self.database_path,
            backup_path
        )

        return {
            "filename": backup_filename,
            "path": str(backup_path),
            "created_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }

    def execute_merge(self):
        preview = self.get_merge_preview()

        if (
            preview["summary"][
                "duplicate_record_count"
            ]
            == 0
        ):
            return {
                "success": True,
                "backup": None,
                "groups_processed": 0,
                "records_removed": 0,
                "records_remaining": (
                    preview["summary"][
                        "business_count"
                    ]
                ),
                "message": (
                    "No duplicate businesses "
                    "were detected."
                )
            }

        backup = self.create_backup()

        try:
            result = (
                self.database
                .deduplicate_businesses()
            )

            return {
                "success": True,
                "backup": backup,
                "groups_processed": (
                    result["groups_processed"]
                ),
                "records_removed": (
                    result["records_removed"]
                ),
                "records_remaining": (
                    result["records_remaining"]
                ),
                "message": (
                    "Duplicate businesses were "
                    "merged successfully."
                )
            }

        except Exception:
            self.restore_backup(
                backup["path"]
            )

            raise

    def restore_backup(self, backup_path):
        source_path = Path(backup_path)

        if not source_path.exists():
            raise FileNotFoundError(
                f"Backup database was not found: "
                f"{source_path}"
            )

        shutil.copy2(
            source_path,
            self.database_path
        )

    def get_recent_backups(self, limit=10):
        if not self.backup_directory.exists():
            return []

        backup_files = sorted(
            self.backup_directory.glob(
                "atlas_before_deduplication_*.db"
            ),
            key=lambda path: (
                path.stat().st_mtime
            ),
            reverse=True
        )

        backups = []

        for backup_path in backup_files[:limit]:
            modified_timestamp = (
                backup_path.stat().st_mtime
            )

            modified = datetime.fromtimestamp(
                modified_timestamp
            )

            backups.append(
                {
                    "filename": (
                        backup_path.name
                    ),
                    "path": str(
                        backup_path
                    ),
                    "created_at": (
                        modified.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    ),
                    "size_bytes": (
                        backup_path.stat().st_size
                    )
                }
            )

        return backups