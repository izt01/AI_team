# debug_filtering.py
import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="jobmatch",
    user="devuser", password="devpass"
)
cur = conn.cursor()

# フィルターなし
cur.execute("""
    SELECT COUNT(*)
    FROM company_profile cp
    JOIN company_date cd ON cp.company_id = cd.company_id
    LEFT JOIN job_attributes ja ON cp.id::text = ja.job_id::text
    WHERE cp.job_title ILIKE %s 
      AND cp.location_prefecture ILIKE %s 
      AND cp.salary_min >= %s
""", ('%デザイナー%', '%東京都%', 300))

count_no_filter = cur.fetchone()[0]
print(f"Without filters: {count_no_filter} jobs")

# リモート=trueのフィルター
cur.execute("""
    SELECT COUNT(*)
    FROM company_profile cp
    JOIN company_date cd ON cp.company_id = cd.company_id
    LEFT JOIN job_attributes ja ON cp.id::text = ja.job_id::text
    WHERE cp.job_title ILIKE %s 
      AND cp.location_prefecture ILIKE %s 
      AND cp.salary_min >= %s
      AND ja.work_flexibility->>'remote' = 'true'
""", ('%デザイナー%', '%東京都%', 300))

count_remote = cur.fetchone()[0]
print(f"With remote=true: {count_remote} jobs")

# リモート=true + フレックス=true
cur.execute("""
    SELECT COUNT(*)
    FROM company_profile cp
    JOIN company_date cd ON cp.company_id = cd.company_id
    LEFT JOIN job_attributes ja ON cp.id::text = ja.job_id::text
    WHERE cp.job_title ILIKE %s 
      AND cp.location_prefecture ILIKE %s 
      AND cp.salary_min >= %s
      AND ja.work_flexibility->>'remote' = 'true'
      AND ja.work_flexibility->>'flex_time' = 'true'
""", ('%デザイナー%', '%東京都%', 300))

count_both = cur.fetchone()[0]
print(f"With remote=true AND flex_time=true: {count_both} jobs")

# サンプルデータを確認
cur.execute("""
    SELECT cp.id, cp.job_title, ja.work_flexibility
    FROM company_profile cp
    JOIN company_date cd ON cp.company_id = cd.company_id
    LEFT JOIN job_attributes ja ON cp.id::text = ja.job_id::text
    WHERE cp.job_title ILIKE %s 
      AND cp.location_prefecture ILIKE %s 
      AND cp.salary_min >= %s
      AND ja.work_flexibility->>'remote' = 'true'
      AND ja.work_flexibility->>'flex_time' = 'true'
    LIMIT 3
""", ('%デザイナー%', '%東京都%', 300))

print("\nSample filtered jobs:")
for row in cur.fetchall():
    print(f"  {row[1]}: {row[2]}")

cur.close()
conn.close()