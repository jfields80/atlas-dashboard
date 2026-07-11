"""Tests for routes/analytics.py's SQL-identifier safety (AES-REVIEW-001A #5).

Focused on the table-name allowlist introduced to close the f-string
SQL-identifier-interpolation shape in ``get_table_count``/
``get_status_count``. Not a broad Flask-route test — these two functions
take a plain sqlite3 cursor and are exercised directly against an in-memory
database.
"""

from __future__ import annotations

import sqlite3

import pytest

from routes.analytics import (
    _ALLOWED_TABLE_NAMES,
    _validate_table_name,
    get_status_count,
    get_table_count,
)


@pytest.fixture()
def cursor():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE projects (id INTEGER, status TEXT)")
    conn.execute(
        "INSERT INTO projects (id, status) VALUES (1, 'active'), "
        "(2, 'planning'), (3, 'active')"
    )
    try:
        yield conn.cursor()
    finally:
        conn.close()


class TestTableNameAllowlist:
    def test_every_call_site_table_is_allowlisted(self):
        # projects/businesses/categories/jobs are the exact literals the
        # analytics() view passes; every one must be authorized.
        assert {"projects", "businesses", "categories", "jobs"} <= (
            _ALLOWED_TABLE_NAMES
        )

    def test_validate_table_name_accepts_allowlisted(self):
        for name in _ALLOWED_TABLE_NAMES:
            _validate_table_name(name)  # must not raise

    def test_validate_table_name_rejects_unauthorized(self):
        with pytest.raises(ValueError):
            _validate_table_name("sqlite_master")

    def test_validate_table_name_rejects_injection_shaped_input(self):
        with pytest.raises(ValueError):
            _validate_table_name("projects; DROP TABLE projects;--")


class TestQuerySemanticsUnchanged:
    def test_get_table_count_returns_real_count(self, cursor):
        assert get_table_count(cursor, "projects") == 3

    def test_get_status_count_returns_real_count(self, cursor):
        assert get_status_count(cursor, "projects", "active") == 2
        assert get_status_count(cursor, "projects", "planning") == 1

    def test_get_status_count_is_case_insensitive(self, cursor):
        assert get_status_count(cursor, "projects", "ACTIVE") == 2

    def test_unauthorized_table_name_returns_zero_not_raises(self, cursor):
        # get_table_count/get_status_count swallow errors (existing
        # behavior); an unauthorized name must fail closed (0), never
        # execute against the database.
        assert get_table_count(cursor, "sqlite_master") == 0
        assert get_status_count(cursor, "sqlite_master", "active") == 0

    def test_injection_shaped_table_name_never_reaches_execute(self, cursor):
        assert get_table_count(cursor, "projects; DROP TABLE projects;--") == 0
        # Prove the table survived — the allowlist rejected the payload
        # before it ever reached cursor.execute().
        assert get_table_count(cursor, "projects") == 3
