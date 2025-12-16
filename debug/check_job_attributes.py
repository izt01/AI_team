# check_job_attributes.py
import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="jobmatch",
    user="devuser", password="devpass"
)
cur = conn.cursor()

# job_attributesのデータ数
cur.execute("SELECT COUNT(*) FROM job_attributes")
print(f"Total job_attributes: {cur.fetchone()[0]}")

# サンプルデータを確認
cur.execute("""
    SELECT ja.job_id, ja.work_flexibility, ja.company_culture, ja.career_path
    FROM job_attributes ja
    LIMIT 5
""")

print("\nSample data:")
for row in cur.fetchall():
    print(f"Job ID: {row[0]}")
    print(f"  Work Flexibility: {row[1]}")
    print(f"  Company Culture: {row[2]}")
    print(f"  Career Path: {row[3]}")
    print()

cur.close()
conn.close()