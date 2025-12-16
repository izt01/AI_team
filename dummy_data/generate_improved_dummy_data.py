"""
改良版ダミーデータ生成スクリプト
既存のテーブル構造に合わせて1万件のデータを生成
"""

import psycopg2
import json
import random
from datetime import datetime, timedelta
import uuid

# データベース接続
conn = psycopg2.connect(
    host="localhost", 
    port=5432, 
    dbname="jobmatch",
    user="devuser", 
    password="devpass"
)
cur = conn.cursor()

print("=" * 60)
print("改良版ダミーデータ生成スクリプト - 最終版")
print("=" * 60)

# ==========================================
# 1. ユーザー情報（personal_date）: 1000人
# ==========================================
print("\n[1/8] Generating personal_date (1000 users)...")

cur.execute("SELECT COALESCE(MAX(user_id), 0) FROM personal_date")
max_user_id = cur.fetchone()[0]
print(f"  Current max user_id: {max_user_id}")

cur.execute("SELECT COUNT(*) FROM personal_date")
existing_users = cur.fetchone()[0]

target_users = 1000
users_to_create = target_users - existing_users

if users_to_create <= 0:
    print(f"  ✓ Already have {existing_users} users, skipping...")
else:
    print(f"  Creating {users_to_create} new users (starting from user_id={max_user_id + 1})...")
    
    names = ['山田', '佐藤', '鈴木', '高橋', '田中', '伊藤', '渡辺', '中村', '小林', '加藤']
    first_names = ['太郎', '花子', '一郎', '美咲', '健太', 'あかり', '大輔', '優子', '誠', '由美']
    
    for i in range(1, users_to_create + 1):
        new_user_id = max_user_id + i
        email = f'user{new_user_id}@example.com'
        password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lW8J4eG3M9Yi'
        name = f"{names[i % 10]}{first_names[i % 10]}{new_user_id}"
        birth_day = datetime(1980, 1, 1) + timedelta(days=i * 10)
        phone = f"090-{1000 + (i % 9000):04d}-{1000 + (i % 9000):04d}"
        address = f"{['東京都渋谷区', '大阪府大阪市', '神奈川県横浜市', '愛知県名古屋市', '福岡県福岡市'][i % 5]}{i % 100}番地"
        created = datetime.now() - timedelta(days=i)
        
        try:
            cur.execute("""
                INSERT INTO personal_date (user_id, email, password_hash, user_name, birth_day, phone_number, address, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (new_user_id, email, password_hash, name, birth_day, phone, address, created, created))
            
            if i % 100 == 0:
                print(f"  [{i}/{users_to_create}] Created (user_id={new_user_id})")
                conn.commit()
        except Exception as e:
            print(f"  Error creating user {new_user_id}: {e}")
            conn.rollback()
    
    conn.commit()
    print(f"  ✓ Created {users_to_create} users")

# ==========================================
# 2. ユーザープロフィール（user_profile）
# ==========================================
print("\n[2/8] Generating user_profile...")

cur.execute("""
    SELECT pd.user_id 
    FROM personal_date pd
    LEFT JOIN user_profile up ON pd.user_id = up.user_id
    WHERE up.user_id IS NULL
    ORDER BY pd.user_id
""")
users_without_profile = [row[0] for row in cur.fetchall()]

if not users_without_profile:
    print(f"  ✓ All users already have profiles, skipping...")
else:
    print(f"  Creating profiles for {len(users_without_profile)} users...")
    
    jobs = ['エンジニア', 'デザイナー', '営業', 'マーケティング', 'コンサルタント', 
            '事務', '企画', '人事', '経理', 'カスタマーサポート']
    locations = ['東京都', '大阪府', '神奈川県', '愛知県', '福岡県']
    
    for i, user_id in enumerate(users_without_profile, 1):
        job = jobs[i % 10]
        location = locations[i % 5]
        salary = 300 + (i % 8) * 100
        created = datetime.now() - timedelta(days=i)
        
        try:
            cur.execute("""
                INSERT INTO user_profile (user_id, job_title, location_prefecture, salary_min, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, job, location, salary, created, created))
            
            if i % 100 == 0:
                print(f"  [{i}/{len(users_without_profile)}] Created")
                conn.commit()
        except Exception as e:
            print(f"  Error creating profile for user {user_id}: {e}")
            conn.rollback()
    
    conn.commit()
    print(f"  ✓ Created {len(users_without_profile)} profiles")

# ==========================================
# 3. 企業情報（company_date）
# ==========================================
print("\n[3/8] Generating company_date...")

cur.execute("SELECT COUNT(*) FROM company_date")
existing_companies = cur.fetchone()[0]

target_companies = 500
companies_to_create = target_companies - existing_companies

if companies_to_create <= 0:
    print(f"  ✓ Already have {existing_companies} companies, skipping...")
else:
    print(f"  Creating {companies_to_create} companies...")
    
    company_types = [
        'テクノロジー', 'クリエイティブ', 'マーケティング', 'コンサルティング', 'エンタープライズ',
        'イノベーション', 'ソリューションズ', 'デジタル', 'グローバル', 'システムズ',
        'プラットフォーム', 'アドバンス', 'インテグレート', 'ビジネス', 'パートナーズ',
        'ファイナンス', 'メディア', 'ネットワーク', 'エージェンシー', 'サービス'
    ]
    
    for i in range(1, companies_to_create + 1):
        company_id = str(uuid.uuid4())
        company_name = f"株式会社{company_types[i % 20]}{existing_companies + i}"
        email = f'company{existing_companies + i}@example.com'
        password = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lW8J4eG3M9Yi'
        address = f"{['東京都港区', '大阪府大阪市', '神奈川県横浜市', '愛知県名古屋市', '福岡県福岡市'][i % 5]}{i % 100}番地"
        phone = f"03-{1000 + (i % 9000):04d}-{1000 + (i % 9000):04d}"
        website = f'https://example{existing_companies + i}.com'
        created = datetime.now() - timedelta(days=i)
        
        try:
            cur.execute("""
                INSERT INTO company_date (company_id, email, password, company_name, address, phone_number, website_url, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (company_id, email, password, company_name, address, phone, website, created, created))
            
            if i % 50 == 0:
                print(f"  [{i}/{companies_to_create}] Created")
                conn.commit()
        except Exception as e:
            print(f"  Error creating company: {e}")
            conn.rollback()
    
    conn.commit()
    print(f"  ✓ Created {companies_to_create} companies")

# ==========================================
# 4. 求人情報（company_profile）
# ==========================================
print("\n[4/8] Generating company_profile...")

cur.execute("SELECT COUNT(*) FROM company_profile")
existing_jobs = cur.fetchone()[0]

target_jobs = 10000
jobs_to_create = target_jobs - existing_jobs

if jobs_to_create <= 0:
    print(f"  ✓ Already have {existing_jobs} jobs, skipping...")
else:
    print(f"  Creating {jobs_to_create} jobs...")
    
    cur.execute("SELECT company_id FROM company_date")
    company_ids = [row[0] for row in cur.fetchall()]
    
    if not company_ids:
        print("  ⚠ No companies found! Skipping job creation.")
    else:
        print(f"  Found {len(company_ids)} companies")
        
        jobs = [
            'エンジニア', 'デザイナー', '営業', 'マーケティング', 'コンサルタント',
            '事務', '企画', '人事', '経理', 'カスタマーサポート',
            'プロジェクトマネージャー', 'データアナリスト', 'Webディレクター', '法務', '広報'
        ]
        locations = [
            '東京都', '大阪府', '神奈川県', '愛知県', '福岡県',
            '北海道', '宮城県', '広島県', '京都府', '兵庫県'
        ]
        
        for i in range(1, jobs_to_create + 1):
            job_id = str(uuid.uuid4())
            company_id = company_ids[i % len(company_ids)]
            job = jobs[i % 15]
            location = locations[i % 10]
            salary_min = 300 + (i % 8) * 100
            salary_max = salary_min + 200 + (i % 3) * 100
            created = datetime.now() - timedelta(days=i % 365)
            
            try:
                cur.execute("""
                    INSERT INTO company_profile (id, company_id, job_title, location_prefecture, salary_min, salary_max, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (job_id, company_id, job, location, salary_min, salary_max, created, created))
                
                if i % 500 == 0:
                    print(f"  [{i}/{jobs_to_create}] Created")
                    conn.commit()
            except Exception as e:
                if i <= 5:
                    print(f"  Error creating job: {e}")
                conn.rollback()
        
        conn.commit()
        print(f"  ✓ Created {jobs_to_create} jobs")

# ==========================================
# 5. 求人属性（job_attributes）★修正版★
# ==========================================
print("\n[5/8] Generating job_attributes...")

cur.execute("SELECT id FROM company_profile")
job_ids = [row[0] for row in cur.fetchall()]

print(f"  Updating attributes for {len(job_ids)} jobs...")

# テーブルのカラムを確認
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'job_attributes'
    ORDER BY ordinal_position
""")
columns = [row[0] for row in cur.fetchall()]
print(f"  Available columns: {', '.join(columns)}")

# カラムの有無を確認
has_extracted_at = 'extracted_at' in columns
has_updated_at = 'updated_at' in columns

for i, job_id in enumerate(job_ids, 1):
    work_flexibility = {
        "remote": random.choice([True, True, False, False, False]),
        "flex_time": random.choice([True, True, False, False]),
        "side_job": random.choice([True, False, False, False]),
        "overtime": random.choice(["low", "medium", "medium", "high"])
    }
    
    company_culture = {
        "type": random.choice(["startup", "venture", "mid-size", "large-enterprise"]),
        "atmosphere": random.choice(["flat", "hierarchical", "challenging", "stable"]),
        "size": random.choice(["small", "medium", "medium", "large", "large"])
    }
    
    career_path = {
        "growth_opportunities": random.choice([True, True, False]),
        "training": random.choice([True, True, False]),
        "promotion_speed": random.choice(["fast", "normal", "normal", "slow"]),
        "skill_support": random.choice([True, True, False])
    }
    
    try:
        # カラムの有無に応じてクエリを動的に生成
        if has_extracted_at and has_updated_at:
            sql = """
                INSERT INTO job_attributes (job_id, company_culture, work_flexibility, career_path, extracted_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (job_id) 
                DO UPDATE SET 
                    company_culture = EXCLUDED.company_culture,
                    work_flexibility = EXCLUDED.work_flexibility,
                    career_path = EXCLUDED.career_path,
                    updated_at = NOW()
            """
        elif has_updated_at:
            sql = """
                INSERT INTO job_attributes (job_id, company_culture, work_flexibility, career_path, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (job_id) 
                DO UPDATE SET 
                    company_culture = EXCLUDED.company_culture,
                    work_flexibility = EXCLUDED.work_flexibility,
                    career_path = EXCLUDED.career_path,
                    updated_at = NOW()
            """
        else:
            sql = """
                INSERT INTO job_attributes (job_id, company_culture, work_flexibility, career_path)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (job_id) 
                DO UPDATE SET 
                    company_culture = EXCLUDED.company_culture,
                    work_flexibility = EXCLUDED.work_flexibility,
                    career_path = EXCLUDED.career_path
            """
        
        cur.execute(sql, (
            str(job_id),
            json.dumps(company_culture),
            json.dumps(work_flexibility),
            json.dumps(career_path)
        ))
        
        if i % 500 == 0:
            print(f"  [{i}/{len(job_ids)}] Updated")
            conn.commit()
    except Exception as e:
        if i <= 5:
            print(f"  Error at job {i}: {e}")
        conn.rollback()

conn.commit()
print(f"  ✓ Updated all job attributes")

# ==========================================
# 6. ユーザー行動履歴（user_interactions）: 5000件
# ==========================================
print("\n[6/8] Generating user_interactions (5000 interactions)...")

cur.execute("SELECT COUNT(*) FROM user_interactions")
existing_interactions = cur.fetchone()[0]

if existing_interactions >= 5000:
    print(f"  ✓ Already have {existing_interactions} interactions, skipping...")
else:
    # ランダムな求人IDを取得
    cur.execute("SELECT id FROM company_profile ORDER BY RANDOM() LIMIT 5000")
    random_job_ids = [row[0] for row in cur.fetchall()]
    
    interaction_types = ['click', 'view', 'view', 'favorite', 'apply']
    
    for i in range(existing_interactions + 1, 5001):
        user_id = 1 + (i % 1000)
        job_id = random_job_ids[i % len(random_job_ids)]
        interaction = interaction_types[i % 5]
        value = random.randint(30, 300) if interaction == 'view' else 0
        created = datetime.now() - timedelta(hours=i)
        
        cur.execute("""
            INSERT INTO user_interactions (user_id, job_id, interaction_type, interaction_value, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, str(job_id), interaction, value, created))
        
        if i % 500 == 0:
            print(f"  [{i}/5000] Created")
            conn.commit()
    
    conn.commit()
    print(f"  ✓ Created {5000 - existing_interactions} interactions")

# ==========================================
# 7. チャット履歴（chat_history）: 3000件
# ==========================================
print("\n[7/8] Generating chat_history (3000 messages)...")

cur.execute("SELECT COUNT(*) FROM chat_history")
existing_chats = cur.fetchone()[0]

if existing_chats >= 3000:
    print(f"  ✓ Already have {existing_chats} messages, skipping...")
else:
    user_messages = [
        'はい、リモート勤務できる職場がいいです',
        'フレックスタイムは特に興味ないです',
        '大企業を希望します',
        '残業は少なめがいいです',
        '研修制度は重要だと思います',
        'はい、成長機会を重視します',
        '副業は可能な方がいいです',
        '昇進スピードは特に気にしません',
        '活気のある職場がいいです',
        'チームワークを大切にする文化がいいです'
    ]
    
    bot_messages = [
        'リモートワーク可能な求人を希望しますか？',
        'フレックスタイム制度を希望しますか？',
        '企業規模の希望はありますか？',
        '残業時間について希望はありますか？',
        '研修・スキルアップ支援を重視しますか？',
        'キャリア成長の機会を重視しますか？',
        '副業可能な求人を希望しますか？',
        '昇進スピードを重視しますか？',
        '組織の雰囲気はどのようなものが良いですか？',
        '該当求人数は50件です。'
    ]
    
    for i in range(existing_chats + 1, 3001):
        user_id = 1 + (i % 1000)
        session_id = f'session_{user_id}_{i % 10}'
        msg_type = 'user' if i % 2 == 0 else 'bot'
        message = user_messages[i % 10] if msg_type == 'user' else bot_messages[i % 10]
        created = datetime.now() - timedelta(hours=i)
        
        cur.execute("""
            INSERT INTO chat_history (user_id, message_type, message_text, session_id, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, msg_type, message, session_id, created))
        
        if i % 300 == 0:
            print(f"  [{i}/3000] Created")
            conn.commit()
    
    conn.commit()
    print(f"  ✓ Created {3000 - existing_chats} messages")

# ==========================================
# 8. ユーザーの質問回答（user_question_responses）
# ==========================================
print("\n[8/8] Generating user_question_responses (2000 responses)...")

# まず、dynamic_questionsの質問数を確認
cur.execute("SELECT COUNT(*) FROM dynamic_questions")
question_count = cur.fetchone()[0]

if question_count == 0:
    print("  ⚠ No questions found in dynamic_questions table!")
    print("  Creating default questions first...")
    
    # デフォルト質問を作成
    default_questions = [
        ('remote', 'リモートワーク可能な求人を希望しますか？', '働き方の柔軟性', 'boolean'),
        ('flex_time', 'フレックスタイム制度を希望しますか？', '働き方の柔軟性', 'boolean'),
        ('side_job', '副業可能な求人を希望しますか？', '働き方の柔軟性', 'boolean'),
        ('overtime', '残業時間について希望はありますか？', '働き方の柔軟性', 'choice'),
        ('company_type', '企業規模の希望はありますか？', '企業文化・雰囲気', 'choice'),
        ('atmosphere', '組織の雰囲気はどのようなものが良いですか？', '企業文化・雰囲気', 'choice'),
        ('growth', 'キャリア成長の機会を重視しますか？', 'キャリアパス', 'boolean'),
        ('training', '研修・スキルアップ支援を重視しますか？', 'キャリアパス', 'boolean'),
        ('promotion', '昇進スピードを重視しますか？', 'キャリアパス', 'choice'),
    ]
    
    for q_key, q_text, category, q_type in default_questions:
        try:
            cur.execute("""
                INSERT INTO dynamic_questions (question_key, question_text, category, question_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (question_key) DO NOTHING
            """, (q_key, q_text, category, q_type))
        except Exception as e:
            print(f"  Error inserting question: {e}")
    
    conn.commit()
    
    # 再度質問数を確認
    cur.execute("SELECT COUNT(*) FROM dynamic_questions")
    question_count = cur.fetchone()[0]
    print(f"  ✓ Created {question_count} questions")

# 利用可能な質問IDを取得
cur.execute("SELECT id FROM dynamic_questions ORDER BY id")
available_question_ids = [row[0] for row in cur.fetchall()]

if not available_question_ids:
    print("  ⚠ Still no questions available, skipping responses...")
else:
    print(f"  Found {len(available_question_ids)} questions")
    
    cur.execute("SELECT COUNT(*) FROM user_question_responses")
    existing_responses = cur.fetchone()[0]
    
    target_responses = 2000
    responses_to_create = target_responses - existing_responses
    
    if responses_to_create <= 0:
        print(f"  ✓ Already have {existing_responses} responses, skipping...")
    else:
        print(f"  Creating {responses_to_create} responses...")
        
        cur.execute("SELECT user_id FROM personal_date")
        user_ids = [row[0] for row in cur.fetchall()]
        
        responses = [
            ('はい、リモート勤務できる職場がいいです', 'はい'),
            ('フレックスタイムは特に興味ないです', 'いいえ'),
            ('大企業を希望します', '大企業'),
            ('残業は少なめがいいです', '少なめ'),
            ('研修制度は重要だと思います', 'はい'),
            ('はい、成長機会を重視します', 'はい'),
            ('副業は可能な方がいいです', 'はい'),
            ('昇進スピードは特に気にしません', 'いいえ'),
            ('活気のある職場がいいです', '活気'),
            ('チームワークを大切にする文化がいいです', 'チームワーク')
        ]
        
        created_count = 0
        attempts = 0
        max_attempts = responses_to_create * 3
        
        while created_count < responses_to_create and attempts < max_attempts:
            attempts += 1
            user_id = random.choice(user_ids)
            question_id = random.choice(available_question_ids)  # 利用可能な質問IDから選択
            response, normalized = responses[attempts % len(responses)]
            confidence = 0.7 + (attempts % 30) / 100.0
            created = datetime.now() - timedelta(hours=attempts % (24 * 30))
            
            try:
                cur.execute("""
                    INSERT INTO user_question_responses (user_id, question_id, response_text, normalized_response, confidence_score, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, question_id, response, normalized, confidence, created))
                created_count += 1
                
                if created_count % 200 == 0:
                    print(f"  [{created_count}/{responses_to_create}] Created")
                    conn.commit()
            except:
                pass  # Unique constraint violation - skip
        
        conn.commit()
        print(f"  ✓ Created {created_count} responses")

# ==========================================
# 統計情報を表示
# ==========================================
print("\n" + "=" * 60)
print("データ生成完了！")
print("=" * 60)

cur.execute("SELECT COUNT(*) FROM personal_date")
print(f"ユーザー: {cur.fetchone()[0]:,}件")

cur.execute("SELECT COUNT(*) FROM user_profile")
print(f"ユーザープロフィール: {cur.fetchone()[0]:,}件")

cur.execute("SELECT COUNT(*) FROM company_date")
print(f"企業: {cur.fetchone()[0]:,}件")

cur.execute("SELECT COUNT(*) FROM company_profile")
print(f"求人: {cur.fetchone()[0]:,}件")

cur.execute("SELECT COUNT(*) FROM job_attributes")
print(f"求人属性: {cur.fetchone()[0]:,}件")

cur.execute("SELECT COUNT(*) FROM user_interactions")
print(f"ユーザー行動: {cur.fetchone()[0]:,}件")

cur.execute("SELECT COUNT(*) FROM chat_history")
print(f"チャット履歴: {cur.fetchone()[0]:,}件")

cur.execute("SELECT COUNT(*) FROM user_question_responses")
print(f"質問回答: {cur.fetchone()[0]:,}件")

# 求人属性の統計
cur.execute("""
    SELECT 
        SUM(CASE WHEN (work_flexibility->>'remote')::boolean = true THEN 1 ELSE 0 END) as remote_count,
        SUM(CASE WHEN (work_flexibility->>'flex_time')::boolean = true THEN 1 ELSE 0 END) as flex_count,
        SUM(CASE WHEN company_culture->>'size' = 'large' THEN 1 ELSE 0 END) as large_count,
        COUNT(*) as total
    FROM job_attributes
""")
stats = cur.fetchone()
print(f"\n求人属性の統計:")
print(f"  リモート可: {stats[0]:,}/{stats[3]:,} ({stats[0]*100//stats[3]}%)")
print(f"  フレックス可: {stats[1]:,}/{stats[3]:,} ({stats[1]*100//stats[3]}%)")
print(f"  大企業: {stats[2]:,}/{stats[3]:,} ({stats[2]*100//stats[3]}%)")

cur.close()
conn.close()

print("\n✓ All done!")