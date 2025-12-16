"""
シーケンスを修正するスクリプト
"""

import psycopg2

conn = psycopg2.connect(
    host="localhost", 
    port=5432, 
    dbname="jobmatch",
    user="devuser", 
    password="devpass"
)
cur = conn.cursor()

print("=" * 60)
print("シーケンス修正スクリプト")
print("=" * 60)

# personal_date のシーケンスをリセット
print("\n[1] Fixing personal_date sequence...")
cur.execute("SELECT MAX(user_id) FROM personal_date")
max_user_id = cur.fetchone()[0]
print(f"  Current max user_id: {max_user_id}")

cur.execute("""
    SELECT setval(
        pg_get_serial_sequence('personal_date', 'user_id'),
        %s
    )
""", (max_user_id,))

cur.execute("SELECT last_value FROM personal_date_user_id_seq")
new_seq_value = cur.fetchone()[0]
print(f"  ✓ Sequence reset to: {new_seq_value}")
print(f"  Next user_id will be: {new_seq_value + 1}")

conn.commit()

# 他のテーブルも同様に修正（必要に応じて）
print("\n✓ All sequences fixed!")

cur.close()
conn.close()