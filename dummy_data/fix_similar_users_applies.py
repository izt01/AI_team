"""
類似ユーザー（1000番台）に確実に応募データを追加
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
print("類似ユーザー（1000番台）に応募データを追加")
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
cur.execute("SELECT id FROM company_profile")
job_ids = [row['id'] for row in cur.fetchall()]

print(f"  Available jobs: {len(job_ids):,}")

# 各ユーザーに10〜20件の応募データを追加
print(f"\n[2] Adding apply data for {len(target_users)} users...")

total_created = 0

for user_id in target_users:
    # 既存の応募数を確認
    cur.execute("""
        SELECT COUNT(*) as count
        FROM user_interactions
        WHERE user_id = %s AND interaction_type = 'apply'
    """, (user_id,))
    
    existing_count = cur.fetchone()['count']
    
    # 目標：各ユーザー15件の応募
    target_count = 15
    to_create = target_count - existing_count
    
    if to_create <= 0:
        print(f"  User {user_id}: Already has {existing_count} applies ✓")
        continue
    
    created = 0
    attempts = 0
    max_attempts = to_create * 3
    
    while created < to_create and attempts < max_attempts:
        attempts += 1
        
        # ランダムに求人を選択
        job_id = random.choice(job_ids)
        created_at = datetime.now() - timedelta(days=random.randint(1, 365))
        
        try:
            cur.execute("""
                INSERT INTO user_interactions (user_id, job_id, interaction_type, interaction_value, created_at)
                VALUES (%s, %s, 'apply', 0, %s)
            """, (user_id, str(job_id), created_at))
            
            created += 1
            total_created += 1
            
        except:
            # 重複エラーは無視
            pass
    
    conn.commit()
    print(f"  User {user_id}: Created {created} applies (total: {existing_count + created})")

print(f"\n✓ Total created: {total_created} applies")

# 確認
print("\n[3] Verification...")

for user_id in target_users[:10]:
    cur.execute("""
        SELECT COUNT(*) as count
        FROM user_interactions
        WHERE user_id = %s AND interaction_type = 'apply'
    """, (user_id,))
    
    count = cur.fetchone()['count']
    print(f"  User {user_id}: {count} applies")

if len(target_users) > 10:
    print(f"  ... and {len(target_users) - 10} more users")

# 応募された求人のサンプルを表示
print("\n[4] Sample applied jobs from these users...")

cur.execute("""
    SELECT 
        ui.user_id,
        cp.job_title,
        cd.company_name
    FROM user_interactions ui
    JOIN company_profile cp ON ui.job_id::text = cp.id::text
    JOIN company_date cd ON cp.company_id = cd.company_id
    WHERE ui.user_id >= 1000
      AND ui.interaction_type = 'apply'
    ORDER BY RANDOM()
    LIMIT 5
""")

samples = cur.fetchall()
for sample in samples:
    company_short = sample['company_name'][:25]
    print(f"  User {sample['user_id']}: {company_short} / {sample['job_title']}")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("✓ Apply data addition completed!")
print("=" * 60)