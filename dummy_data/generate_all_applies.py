"""
全ユーザーに応募データを大量追加（目標：10,000件）
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
print("全ユーザーに応募データを大量追加")
print("=" * 60)

# 1. 既存のユーザーと求人を取得
print("\n[1] Getting users and jobs...")

cur.execute("SELECT user_id FROM personal_date ORDER BY user_id")
user_ids = [row['user_id'] for row in cur.fetchall()]

cur.execute("SELECT id FROM company_profile ORDER BY RANDOM()")
job_ids = [row['id'] for row in cur.fetchall()]

print(f"  Users: {len(user_ids):,}")
print(f"  Jobs: {len(job_ids):,}")

# 2. 既存の応募データを確認
cur.execute("SELECT COUNT(*) FROM user_interactions WHERE interaction_type = 'apply'")
existing_applies = cur.fetchone()['count']

print(f"  Existing applies: {existing_applies:,}")

# 3. 目標件数を設定
target_total_applies = 10000
applies_to_create = target_total_applies - existing_applies

if applies_to_create <= 0:
    print(f"  ✓ Already have {existing_applies:,} applies (target: {target_total_applies:,})")
    print("  Nothing to do.")
else:
    print(f"  Target: {target_total_applies:,} applies")
    print(f"  To create: {applies_to_create:,} applies")
    
    # 4. 応募データを生成
    print(f"\n[2] Generating {applies_to_create:,} apply interactions...")
    
    created_count = 0
    attempts = 0
    max_attempts = applies_to_create * 2  # 重複を考慮して2倍試行
    
    # バッチ処理用のリスト
    batch = []
    batch_size = 1000
    
    while created_count < applies_to_create and attempts < max_attempts:
        attempts += 1
        
        # ランダムにユーザーと求人を選択
        user_id = random.choice(user_ids)
        job_id = random.choice(job_ids)
        created_at = datetime.now() - timedelta(days=random.randint(1, 730))  # 過去2年間
        
        batch.append((user_id, str(job_id), created_at))
        
        # バッチが溜まったら一括挿入
        if len(batch) >= batch_size:
            inserted = 0
            for user_id, job_id, created_at in batch:
                try:
                    cur.execute("""
                        INSERT INTO user_interactions (user_id, job_id, interaction_type, interaction_value, created_at)
                        VALUES (%s, %s, 'apply', 0, %s)
                    """, (user_id, job_id, created_at))
                    inserted += 1
                except:
                    # 重複エラーは無視
                    pass
            
            conn.commit()
            created_count += inserted
            batch = []
            
            # 進捗表示
            progress = (created_count / applies_to_create) * 100
            print(f"  [{created_count:,}/{applies_to_create:,}] {progress:.1f}% - Attempts: {attempts:,}")
    
    # 残りのバッチを処理
    if batch:
        inserted = 0
        for user_id, job_id, created_at in batch:
            try:
                cur.execute("""
                    INSERT INTO user_interactions (user_id, job_id, interaction_type, interaction_value, created_at)
                    VALUES (%s, %s, 'apply', 0, %s)
                """, (user_id, job_id, created_at))
                inserted += 1
            except:
                pass
        
        conn.commit()
        created_count += inserted
    
    print(f"\n  ✓ Created {created_count:,} apply interactions")
    print(f"  Attempts: {attempts:,}")
    print(f"  Success rate: {(created_count/attempts)*100:.1f}%")

# 5. その他のインタラクションも追加（オプション）
print("\n[3] Generating other interactions...")

other_interactions = [
    ('view', 5000),
    ('click', 3000),
    ('favorite', 2000)
]

for interaction_type, target_count in other_interactions:
    cur.execute(f"""
        SELECT COUNT(*) FROM user_interactions 
        WHERE interaction_type = '{interaction_type}'
    """)
    existing_count = cur.fetchone()['count']
    
    to_create = target_count - existing_count
    
    if to_create <= 0:
        print(f"  ✓ {interaction_type}: Already have {existing_count:,} (target: {target_count:,})")
        continue
    
    print(f"  Creating {to_create:,} {interaction_type} interactions...")
    
    created = 0
    batch = []
    batch_size = 1000
    
    for _ in range(to_create * 2):  # 重複を考慮
        if created >= to_create:
            break
        
        user_id = random.choice(user_ids)
        job_id = random.choice(job_ids)
        value = random.randint(30, 300) if interaction_type == 'view' else 0
        created_at = datetime.now() - timedelta(days=random.randint(1, 365))
        
        batch.append((user_id, str(job_id), interaction_type, value, created_at))
        
        if len(batch) >= batch_size:
            inserted = 0
            for u_id, j_id, i_type, val, c_at in batch:
                try:
                    cur.execute("""
                        INSERT INTO user_interactions (user_id, job_id, interaction_type, interaction_value, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (u_id, j_id, i_type, val, c_at))
                    inserted += 1
                except:
                    pass
            
            conn.commit()
            created += inserted
            batch = []
            
            if created % 500 == 0:
                print(f"    [{created:,}/{to_create:,}] {(created/to_create)*100:.1f}%")
    
    # 残りのバッチを処理
    if batch:
        inserted = 0
        for u_id, j_id, i_type, val, c_at in batch:
            try:
                cur.execute("""
                    INSERT INTO user_interactions (user_id, job_id, interaction_type, interaction_value, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (u_id, j_id, i_type, val, c_at))
                inserted += 1
            except:
                pass
        
        conn.commit()
        created += inserted
    
    print(f"    ✓ Created {created:,} {interaction_type} interactions")

# 6. 統計を表示
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
print("\nインタラクション種別:")
for stat in stats:
    print(f"  {stat['interaction_type']:15s}: {stat['count']:>7,}")

# 総数
cur.execute("SELECT COUNT(*) as total FROM user_interactions")
total = cur.fetchone()['total']
print(f"\n  {'合計':15s}: {total:>7,}")

# 応募が多いユーザーTop 10
print("\n応募が多いユーザー Top 10:")
cur.execute("""
    SELECT 
        user_id,
        COUNT(*) as apply_count
    FROM user_interactions
    WHERE interaction_type = 'apply'
    GROUP BY user_id
    ORDER BY apply_count DESC
    LIMIT 10
""")

top_users = cur.fetchall()
for i, user in enumerate(top_users, 1):
    print(f"  {i:2d}. User {user['user_id']:4d}: {user['apply_count']:3d} applies")

# 応募が多い求人Top 10
print("\n応募が多い求人 Top 10:")
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
    LIMIT 10
""")

top_jobs = cur.fetchall()
for i, job in enumerate(top_jobs, 1):
    company_short = job['company_name'][:20] + '...' if len(job['company_name']) > 20 else job['company_name']
    print(f"  {i:2d}. {company_short:25s} / {job['job_title']:15s}: {job['apply_count']:3d} applies")

# ユーザーあたりの平均応募数
cur.execute("""
    SELECT AVG(apply_count) as avg_applies
    FROM (
        SELECT user_id, COUNT(*) as apply_count
        FROM user_interactions
        WHERE interaction_type = 'apply'
        GROUP BY user_id
    ) sub
""")
avg_applies = cur.fetchone()['avg_applies']
print(f"\nユーザーあたりの平均応募数: {avg_applies:.2f}")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("✓ All apply data generation completed!")
print("=" * 60)