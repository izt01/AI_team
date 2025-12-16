# create_filtered_jobs_table.py
import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="jobmatch",
    user="devuser", password="devpass"
)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS user_filtered_jobs (
        id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        session_id VARCHAR(255) NOT NULL,
        job_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES personal_date(user_id) ON DELETE CASCADE
    )
""")

cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_user_filtered_jobs_user_session 
    ON user_filtered_jobs(user_id, session_id)
""")

conn.commit()
cur.close()
conn.close()

print("✓ Table created successfully")