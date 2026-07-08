import sqlite3
from datetime import datetime

from config import DATABASE


class JobManager:

    def __init__(self):
        self.database = DATABASE

    def connect(self):
        return sqlite3.connect(self.database)

    def create_job(self, project_id, employee, job_type):

        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs(

            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            employee TEXT,
            job_type TEXT,
            status TEXT,
            started TEXT,
            finished TEXT,
            progress INTEGER

        )
        """)

        started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        INSERT INTO jobs(

            project_id,
            employee,
            job_type,
            status,
            started,
            finished,
            progress

        )

        VALUES(?,?,?,?,?,?,?)
        """, (

            project_id,
            employee,
            job_type,
            "Running",
            started,
            "",
            0

        ))

        job_id = cursor.lastrowid

        connection.commit()
        connection.close()

        print(f"[JOB CREATED] #{job_id}")

        return job_id

    def update_progress(self, job_id, progress):

        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute("""
        UPDATE jobs
        SET progress=?
        WHERE id=?
        """, (

            progress,
            job_id

        ))

        connection.commit()
        connection.close()

        print(f"[JOB {job_id}] Progress {progress}%")

    def complete_job(self, job_id):

        connection = self.connect()
        cursor = connection.cursor()

        finished = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        UPDATE jobs

        SET

            status=?,
            progress=?,
            finished=?

        WHERE id=?
        """, (

            "Complete",
            100,
            finished,
            job_id

        ))

        connection.commit()
        connection.close()

        print(f"[JOB COMPLETE] #{job_id}")