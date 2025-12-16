"""
不足しているユーザーを作成
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import random

conn = psycopg2.connect(
    host="localhost", 
    port=5432, 
    dbname="jobmatch",
    user="devuser", 
    password="devpass"
)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 60)
print("不足しているユーザーを作成")
print("=" * 60)

# 必要なユーザーIDリスト
required_user_ids = list(range(1, 1023))  # 1〜1022

# 既存のユーザーIDを取得
cur.execute("SELECT user_id FROM personal_date")
existing_user_ids = set([row['user_id'] for row in cur.fetchall()])

print(f"\n[1] Checking users...")
print(f"  Required: {len(required_user_ids)} users (1-1022)")
print(f"  Existing: {len(existing_user_ids)} users")

# 不足しているユーザーIDを特定
missing_user_ids = [uid for uid in required_user_ids if uid not in existing_user_ids]

if not missing_user_ids:
    print(f"  ✓ All users exist!")
else:
    print(f"  Missing: {len(missing_user_ids)} users")
    print(f"  IDs: {missing_user_ids[:20]}{'...' if len(missing_user_ids) > 20 else ''}")
    
    print(f"\n[2] Creating {len(missing_user_ids)} users...")
    
    names = ['山田', '佐藤', '鈴木', '高橋', '田中', '伊藤', '渡辺', '中村', '小林', '加藤']
    first_names = ['太郎', '花子', '一郎', '美咲', '健太', 'あかり', '大輔', '優子', '誠', '由美']
    
    for i, user_id in enumerate(missing_user_ids, 1):
        email = f'user{user_id}@example.com'
        password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lW8J4eG3M9Yi'
        name = f"{names[user_id % 10]}{first_names[user_id % 10]}{user_id}"
        birth_day = datetime(1980, 1, 1) + timedelta(days=user_id * 10)
        phone = f"090-{1000 + (user_id % 9000):04d}-{1000 + (user_id % 9000):04d}"
        address = f"{['東京都渋谷区', '大阪府大阪市', '神奈川県横浜市', '愛知県名古屋市', '福岡県福岡市'][user_id % 5]}{user_id % 100}番地"
        created = datetime.now() - timedelta(days=i)
        
        try:
            # personal_date に挿入
            cur.execute("""
                INSERT INTO personal_date (user_id, email, password_hash, user_name, birth_day, phone_number, address, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, email, password_hash, name, birth_day, phone, address, created, created))
            
            # user_profile に挿入
            jobs = ['エンジニア', 'デザイナー', '営業', 'マーケティング', 'コンサルタント', 
                    '事務', '企画', '人事', '経理', 'カスタマーサポート']
            locations = ['東京都', '大阪府', '神奈川県', '愛知県', '福岡県']
            
            job = jobs[user_id % 10]
            location = locations[user_id % 5]
            salary = 300 + (user_id % 8) * 100
            
            cur.execute("""
                INSERT INTO user_profile (user_id, job_title, location_prefecture, salary_min, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, job, location, salary, created, created))
            
            if i % 100 == 0:
                print(f"  [{i}/{len(missing_user_ids)}] Created user {user_id}")
                conn.commit()
                
        except Exception as e:
            print(f"  Error creating user {user_id}: {e}")
            conn.rollback()
    
    conn.commit()
    print(f"  ✓ Created {len(missing_user_ids)} users")

# 確認
cur.execute("SELECT COUNT(*) FROM personal_date")
total_users = cur.fetchone()['count']

print(f"\n[3] Verification...")
print(f"  Total users: {total_users}")

# 特定のユーザーを確認
cur.execute("""
    SELECT user_id 
    FROM personal_date 
    WHERE user_id IN (1018, 1019, 1021, 1017, 165)
    ORDER BY user_id
""")
found_users = [row['user_id'] for row in cur.fetchall()]
print(f"  Found users (1018, 1019, 1021, 1017, 165): {found_users}")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("✓ User creation completed!")
print("=" * 60)