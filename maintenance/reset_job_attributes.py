# reset_job_attributes.py
import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="jobmatch",
    user="devuser", password="devpass"
)
cur = conn.cursor()

print("=== Resetting job_attributes table ===")

# テーブルを削除して再作成
cur.execute("DROP TABLE IF EXISTS job_attributes CASCADE")
print("✓ Dropped old table")

cur.execute("""
    CREATE TABLE job_attributes (
        id SERIAL PRIMARY KEY,
        job_id UUID NOT NULL REFERENCES company_profile(id) ON DELETE CASCADE,
        company_culture JSONB,
        work_flexibility JSONB,
        career_path JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(job_id)
    )
""")
print("✓ Created new table")

cur.execute("CREATE INDEX idx_job_attributes_job_id ON job_attributes(job_id)")
print("✓ Created index")

conn.commit()
cur.close()
conn.close()

print("\n=== Done! ===")
print("Now run: python app.py")