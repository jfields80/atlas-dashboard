import sqlite3
from datetime import datetime

DATABASE = "atlas.db"


def create_categories_table(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,

        description TEXT,

        parent_id INTEGER,

        industry TEXT,

        icon TEXT,

        active INTEGER DEFAULT 1,

        created_at TEXT,
        updated_at TEXT

    )
    """)


def seed_categories(cursor):

    cursor.execute("SELECT COUNT(*) FROM categories")

    if cursor.fetchone()[0] > 0:
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    categories = [

        (
            "Florists",
            "florists",
            "Flower Shops",
            None,
            "Retail",
            "",
            1,
            now,
            now
        ),

        (
            "Hotels",
            "hotels",
            "Hotels",
            None,
            "Hospitality",
            "",
            1,
            now,
            now
        ),

        (
            "Electricians",
            "electricians",
            "Electrical Contractors",
            None,
            "Trades",
            "",
            1,
            now,
            now
        ),

        (
            "Dentists",
            "dentists",
            "Dental Offices",
            None,
            "Healthcare",
            "",
            1,
            now,
            now
        ),

        (
            "Restaurants",
            "restaurants",
            "Restaurants",
            None,
            "Food",
            "",
            1,
            now,
            now
        )

    ]

    cursor.executemany(
        """
        INSERT INTO categories
        (
            name,
            slug,
            description,
            parent_id,
            industry,
            icon,
            active,
            created_at,
            updated_at
        )

        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        categories
    )


def main():

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    create_categories_table(cursor)

    seed_categories(cursor)

    connection.commit()

    connection.close()

    print()
    print("===================================")
    print(" Atlas Database Initialized")
    print(" Categories Table Created")
    print(" Starter Categories Loaded")
    print("===================================")
    print()


if __name__ == "__main__":
    main()