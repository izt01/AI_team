# check_schema.py
import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="jobmatch",
    user="devuser", password="devpass"
)
cur = conn.cursor()

# company_profile.idの型を確認
print("=== company_profile.id の型 ===")
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'company_profile' AND column_name = 'id'
""")
result = cur.fetchone()
print(f"Column: {result[0]}, Type: {result[1]}")

# サンプルデータを確認
print("\n=== サンプルデータ ===")
cur.execute("SELECT id, job_title FROM company_profile LIMIT 3")
for row in cur.fetchall():
    print(f"ID: {row[0]} (型: {type(row[0]).__name__}), Job: {row[1]}")

# job_attributes.job_idの型を確認
print("\n=== job_attributes.job_id の型 ===")
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'job_attributes' AND column_name = 'job_id'
""")
result = cur.fetchone()
if result:
    print(f"Column: {result[0]}, Type: {result[1]}")
else:
    print("job_attributes テーブルが存在しないか、job_id カラムがありません")

cur.close()
conn.close()