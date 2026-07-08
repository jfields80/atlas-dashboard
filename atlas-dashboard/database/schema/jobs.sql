CREATE TABLE IF NOT EXISTS jobs (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    project_id INTEGER,

    employee TEXT,

    job_type TEXT,

    status TEXT,

    progress INTEGER,

    started TEXT,

    finished TEXT

);