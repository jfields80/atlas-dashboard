import sqlite3

from config import DATABASE


def main():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            business_name,
            status
        FROM businesses
        ORDER BY id
        """
    )

    rows = cursor.fetchall()
    connection.close()

    print()
    print("ALL BUSINESS RECORDS")
    print("====================")

    for row in rows:
        print(
            f"ID {row[0]} | "
            f"{row[1]} | "
            f"{row[2]}"
        )

    print()
    print(f"TOTAL RECORDS: {len(rows)}")


if __name__ == "__main__":
    main()