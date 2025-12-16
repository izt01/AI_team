"""
user_interactions テーブルに応募データを追加
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
print("応募データ生成スクリプト")
print("=" * 60)

# 1. 既存のユーザーと求人を取得
print("\n[1] Getting users and jobs...")

cur.execute("SELECT user_id FROM personal_date")
user_ids = [row['user_id'] for row in cur.fetchall()]

cur.execute("SELECT id FROM company_profile")
job_ids = [row['id'] for row in cur.fetchall()]

print(f"  Users: {len(user_ids)}")
print(f"  Jobs: {len(job_ids)}")

# 2. 既存の応募データを確認
cur.execute("SELECT COUNT(*) FROM user_interactions WHERE interaction_type = 'apply'")
existing_applies = cur.fetchone()['count']
print(f"  Existing applies: {existing_applies}")

# 3. 応募データを生成
print("\n[2] Generating apply interactions...")

target_applies = 2000  # 目標：2000件の応募データ
applies_to_create = target_applies - existing_applies

if applies_to_create <= 0:
    print(f"  ✓ Already have {existing_applies} applies, skipping...")
else:
    print(f"  Creating {applies_to_create} apply interactions...")
    
    created_count = 0
    attempts = 0
    max_attempts = applies_to_create * 3
    
    while created_count < applies_to_create and attempts < max_attempts:
        attempts += 1
        
        # ランダムにユーザーと求人を選択
        user_id = random.choice(user_ids)
        job_id = random.choice(job_ids)
        created_at = datetime.now() - timedelta(days=random.randint(1, 365))
        
        try:
            cur.execute("""
                INSERT INTO user_interactions (user_id, job_id, interaction_type, interaction_value, created_at)
                VALUES (%s, %s, 'apply', 0, %s)
            """, (user_id, str(job_id), created_at))
            
            created_count += 1
            
            if created_count % 200 == 0:
                print(f"  [{created_count}/{applies_to_create}] Created")
                conn.commit()
                
        except Exception as e:
            # 重複エラーは無視（同じユーザーが同じ求人に複数回応募しない）
            pass
    
    conn.commit()
    print(f"  ✓ Created {created_count} apply interactions")

# 4. その他のインタラクションも追加（view, click, favorite）
print("\n[3] Generating other interactions...")

other_interactions = [
    ('view', 3000),
    ('click', 2000),
    ('favorite', 1000)
]

for interaction_type, target_count in other_interactions:
    cur.execute(f"SELECT COUNT(*) FROM user_interactions WHERE interaction_type = '{interaction_type}'")
    existing_count = cur.fetchone()['count']
    
    to_create = target_count - existing_count
    
    if to_create <= 0:
        print(f"  ✓ {interaction_type}: Already have {existing_count}")
        continue
    
    print(f"  Creating {to_create} {interaction_type} interactions...")
    
    created = 0
    attempts = 0
    max_attempts = to_create * 3
    
    while created < to_create and attempts < max_attempts:
        attempts += 1
        
        user_id = random.choice(user_ids)
        job_id = random.choice(job_ids)
        value = random.randint(30, 300) if interaction_type == 'view' else 0
        created_at = datetime.now() - timedelta(days=random.randint(1, 365))
        
        try:
            cur.execute("""
                INSERT INTO user_interactions (user_id, job_id, interaction_type, interaction_value, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, str(job_id), interaction_type, value, created_at))
            
            created += 1
            
            if created % 500 == 0:
                conn.commit()
                
        except:
            pass
    
    conn.commit()
    print(f"  ✓ Created {created} {interaction_type} interactions")

# 5. 統計を表示
print("\n" + "=" * 60)
print("統計情報")
print("=" * 60)

cur.execute("""
    SELECT 
        interaction_type,
        COUNT(*) as count
    FROM user_interactions
    GROUP BY interaction_type
    ORDER BY count DESC
""")

stats = cur.fetchall()
for stat in stats:
    print(f"  {stat['interaction_type']}: {stat['count']:,}")

# 応募が多いユーザーTop 5
print("\n応募が多いユーザー Top 5:")
cur.execute("""
    SELECT 
        user_id,
        COUNT(*) as apply_count
    FROM user_interactions
    WHERE interaction_type = 'apply'
    GROUP BY user_id
    ORDER BY apply_count DESC
    LIMIT 5
""")

top_users = cur.fetchall()
for i, user in enumerate(top_users, 1):
    print(f"  {i}. User {user['user_id']}: {user['apply_count']} applies")

# 応募が多い求人Top 5
print("\n応募が多い求人 Top 5:")
cur.execute("""
    SELECT 
        ui.job_id,
        cp.job_title,
        cd.company_name,
        COUNT(*) as apply_count
    FROM user_interactions ui
    JOIN company_profile cp ON ui.job_id::text = cp.id::text
    JOIN company_date cd ON cp.company_id = cd.company_id
    WHERE ui.interaction_type = 'apply'
    GROUP BY ui.job_id, cp.job_title, cd.company_name
    ORDER BY apply_count DESC
    LIMIT 5
""")

top_jobs = cur.fetchall()
for i, job in enumerate(top_jobs, 1):
    print(f"  {i}. {job['company_name']} / {job['job_title']}: {job['apply_count']} applies")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("✓ Apply data generation completed!")
print("=" * 60)