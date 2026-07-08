CREATE TABLE IF NOT EXISTS projects (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    project_name TEXT NOT NULL,

    category_id INTEGER,

    location TEXT,

    status TEXT,

    created_at TEXT,

    updated_at TEXT

);