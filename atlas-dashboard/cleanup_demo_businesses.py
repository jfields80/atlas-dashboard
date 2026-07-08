import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from config import DATABASE


def main():
    database_path = Path(DATABASE)

    backup_folder = Path(r"C:\Atlas\backups")
    backup_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_path = backup_folder / (
        f"atlas_before_hotel_cleanup_{timestamp}.db"
    )

    shutil.copy2(
        database_path,
        backup_path
    )

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            business_name,
            status
        FROM businesses
        WHERE id IN (1, 2, 3, 13)
        ORDER BY id
        """
    )

    records = cursor.fetchall()

    print()
    print("OLD HOTEL RECORDS TO DELETE")
    print("===========================")

    for record in records:
        print(
            f"ID {record[0]} | "
            f"{record[1]} | "
            f"{record[2]}"
        )

    print()
    print(f"Total hotel records found: {len(records)}")

    if not records:
        print("No matching hotel records were found.")
        connection.close()
        return

    cursor.execute(
        """
        DELETE FROM businesses
        WHERE id IN (1, 2, 3, 13)
        """
    )

    deleted_count = cursor.rowcount

    connection.commit()
    connection.close()

    print()
    print(f"Deleted hotel records: {deleted_count}")
    print(f"Backup created: {backup_path}")


if __name__ == "__main__":
    main()