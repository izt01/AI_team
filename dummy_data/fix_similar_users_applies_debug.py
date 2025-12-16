"""
類似ユーザー（1000番台）に応募データを追加（デバッグ版）
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import random
from datetime import datetime, timedelta

conn = psycopg2.connect(
    host="localhost", 
    port=5432, 
    dbname="jobmatch",
    user="devuser", 
    password="devpass"
)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 60)
print("類似ユーザー（1000番台）に応募データを追加（デバッグ版）")
print("=" * 60)

# 1000番台のユーザーを全て取得
print("\n[1] Getting users with ID >= 1000...")

cur.execute("""
    SELECT user_id 
    FROM personal_date 
    WHERE user_id >= 1000
    ORDER BY user_id
""")
target_users = [row['user_id'] for row in cur.fetchall()]

print(f"  Found {len(target_users)} users (IDs: {target_users[0]}-{target_users[-1]})")

# 求人IDを取得
cur.execute("SELECT id FROM company_profile LIMIT 100")
job_ids = [row['id'] for row in cur.fetchall()]

print(f"  Available jobs: {len(job_ids):,} (using first 100 for testing)")

# テスト：最初の1ユーザーだけ詳しくデバッグ
test_user_id = target_users[0]
print(f"\n[2] Testing with user {test_user_id}...")

# 既存の応募数を確認
cur.execute("""
    SELECT COUNT(*) as count
    FROM user_interactions
    WHERE user_id = %s AND interaction_type = 'apply'
""", (test_user_id,))

existing_count = cur.fetchone()['count']
print(f"  Existing applies: {existing_count}")

# 既に応募済みの求人を確認
cur.execute("""
    SELECT job_id
    FROM user_interactions
    WHERE user_id = %s AND interaction_type = 'apply'
    LIMIT 5
""", (test_user_id,))

existing_jobs = [row['job_id'] for row in cur.fetchall()]
if existing_jobs:
    print(f"  Already applied to: {existing_jobs[:5]}")
else:
    print(f"  No existing applies")

# 10回試行して詳細を確認
print(f"\n[3] Attempting to insert 10 applies...")
success_count = 0
error_count = 0
error_messages = []

for i in range(10):
    job_id = random.choice(job_ids)
    created_at = datetime.now() - timedelta(days=random.randint(1, 365))
    
    try:
        cur.execute("""
            INSERT INTO user_interactions (user_id, job_id, interaction_type, interaction_value, created_at)
            VALUES (%s, %s, 'apply', 0, %s)
        """, (test_user_id, str(job_id), created_at))
        
        conn.commit()
        success_count += 1
        print(f"  [{i+1}] ✓ Success: job_id={str(job_id)[:8]}...")
        
    except Exception as e:
        error_count += 1
        error_msg = str(e)
        if error_msg not in error_messages:
            error_messages.append(error_msg)
        print(f"  [{i+1}] ✗ Error: {str(e)[:60]}...")
        conn.rollback()

print(f"\n  Results: {success_count} success, {error_count} errors")

if error_messages:
    print(f"\n  Error types:")
    for err in error_messages:
        print(f"    - {err[:100]}")

# 最終確認
cur.execute("""
    SELECT COUNT(*) as count
    FROM user_interactions
    WHERE user_id = %s AND interaction_type = 'apply'
""", (test_user_id,))

final_count = cur.fetchone()['count']
print(f"\n  Final apply count for user {test_user_id}: {final_count}")

# テーブル構造を確認
print(f"\n[4] Checking table structure...")

cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'user_interactions'
    ORDER BY ordinal_position
""")

columns = cur.fetchall()
print(f"  user_interactions columns:")
for col in columns:
    print(f"    - {col['column_name']:20s} {col['data_type']:15s} {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}")

# 制約を確認
print(f"\n[5] Checking constraints...")

cur.execute("""
    SELECT constraint_name, constraint_type
    FROM information_schema.table_constraints
    WHERE table_name = 'user_interactions'
""")

constraints = cur.fetchall()
if constraints:
    print(f"  Constraints on user_interactions:")
    for const in constraints:
        print(f"    - {const['constraint_name']:40s} ({const['constraint_type']})")
else:
    print(f"  No constraints found")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("✓ Debug completed!")
print("=" * 60)