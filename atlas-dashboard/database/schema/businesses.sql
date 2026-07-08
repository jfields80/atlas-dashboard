CREATE TABLE IF NOT EXISTS businesses (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    project_id INTEGER,

    category_id INTEGER,

    business_name TEXT NOT NULL,

    address TEXT,

    city TEXT,

    state TEXT,

    zip TEXT,

    phone TEXT,

    website TEXT,

    email TEXT,

    latitude REAL,

    longitude REAL,

    source TEXT,

    status TEXT,

    created_at TEXT,

    updated_at TEXT

);