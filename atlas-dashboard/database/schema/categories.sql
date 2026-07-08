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

);