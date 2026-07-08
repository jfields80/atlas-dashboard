import sqlite3
from datetime import datetime


class CategoryRepository:

    def __init__(self, database="atlas.db"):
        self.database = database

    def get_connection(self):
        return sqlite3.connect(self.database)

    def create(
        self,
        name,
        slug,
        description="",
        parent_id=None,
        industry="",
        icon="",
        active=1
    ):
        connection = self.get_connection()
        cursor = connection.cursor()

        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
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
            VALUES
            (?,?,?,?,?,?,?,?,?)
            """,
            (
                name,
                slug,
                description,
                parent_id,
                industry,
                icon,
                active,
                created,
                created
            )
        )

        connection.commit()

        category_id = cursor.lastrowid

        connection.close()

        return category_id

    def get_all(self):
        connection = self.get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                name,
                slug,
                description,
                industry,
                active
            FROM categories
            ORDER BY name
            """
        )

        rows = cursor.fetchall()

        connection.close()

        return rows

    def get(self, category_id):
        connection = self.get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM categories
            WHERE id=?
            """,
            (category_id,)
        )

        row = cursor.fetchone()

        connection.close()

        return row

    def update(
        self,
        category_id,
        name,
        slug,
        description,
        parent_id,
        industry,
        icon,
        active
    ):
        connection = self.get_connection()
        cursor = connection.cursor()

        updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            """
            UPDATE categories
            SET
                name=?,
                slug=?,
                description=?,
                parent_id=?,
                industry=?,
                icon=?,
                active=?,
                updated_at=?
            WHERE id=?
            """,
            (
                name,
                slug,
                description,
                parent_id,
                industry,
                icon,
                active,
                updated,
                category_id
            )
        )

        connection.commit()
        connection.close()

    def delete(self, category_id):
        connection = self.get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM categories
            WHERE id=?
            """,
            (category_id,)
        )

        connection.commit()
        connection.close()