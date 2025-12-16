# check_updated_attributes.py
import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="jobmatch",
    user="devuser", password="devpass"
)
cur = conn.cursor()

cur.execute("""
    SELECT 
        SUM(CASE WHEN work_flexibility->>'remote' = 'true' THEN 1 ELSE 0 END) as remote_count,
        SUM(CASE WHEN work_flexibility->>'flex_time' = 'true' THEN 1 ELSE 0 END) as flex_count,
        SUM(CASE WHEN work_flexibility->>'side_job' = 'true' THEN 1 ELSE 0 END) as side_job_count,
        SUM(CASE WHEN company_culture->>'size' = 'large' THEN 1 ELSE 0 END) as large_count,
        SUM(CASE WHEN career_path->>'training' = 'true' THEN 1 ELSE 0 END) as training_count,
        COUNT(*) as total
    FROM job_attributes
""")

stats = cur.fetchone()

print("✓ Job Attributes Statistics:")
print(f"  Total jobs: {stats[5]}")
print(f"  リモート可: {stats[0]} ({stats[0]*100//stats[5]}%)")
print(f"  フレックス可: {stats[1]} ({stats[1]*100//stats[5]}%)")
print(f"  副業可: {stats[2]} ({stats[2]*100//stats[5]}%)")
print(f"  大企業: {stats[3]} ({stats[3]*100//stats[5]}%)")
print(f"  研修あり: {stats[4]} ({stats[4]*100//stats[5]}%)")

# サンプルデータを確認
print("\nSample updated data:")
cur.execute("""
    SELECT ja.job_id, ja.work_flexibility, ja.company_culture
    FROM job_attributes ja
    LIMIT 3
""")

for row in cur.fetchall():
    print(f"\nJob ID: {row[0]}")
    print(f"  Work Flexibility: {row[1]}")
    print(f"  Company Culture: {row[2]}")

cur.close()
conn.close()