"""
進化型AI求人マッチングシステム v3.0 - ダミーデータ生成スクリプト

各テーブルに約1万件ずつダミーデータを投入

実行方法:
    python generate_evolved_dummy_data.py

生成されるデータ:
    1. personal_date: 10,000件（ユーザー）
    2. user_profile: 10,000件（ユーザープロファイル）
    3. company_date: 1,000件（企業）
    4. company_profile: 10,000件（求人）
    5. chat_history: 50,000件（チャット履歴）
    6. user_interactions: 30,000件（ユーザー行動）
    7. conversation_turns: 50,000件（会話ターン）
    8. user_insights: 10,000件（蓄積情報）
    9. conversation_sessions: 10,000件（セッション）
    10. score_history: 100,000件（スコア履歴）
"""

import random
import uuid
from datetime import datetime, timedelta
from faker import Faker
from werkzeug.security import generate_password_hash
import json
from db_config import get_db_conn

# Faker初期化
fake = Faker('ja_JP')
Faker.seed(42)
random.seed(42)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# マスターデータ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

JOB_TITLES = [
    'Webデザイナー', 'UIデザイナー', 'UXデザイナー', 'グラフィックデザイナー',
    'フロントエンドエンジニア', 'バックエンドエンジニア', 'フルスタックエンジニア',
    'データサイエンティスト', 'データアナリスト', 'プロジェクトマネージャー',
    'プロダクトマネージャー', 'マーケティング担当', '営業', '人事',
    'カスタマーサポート', 'システムエンジニア', 'インフラエンジニア',
    'セキュリティエンジニア', 'QAエンジニア', 'DevOpsエンジニア'
]

PREFECTURES = [
    '東京都', '神奈川県', '大阪府', '愛知県', '福岡県', '北海道', '宮城県',
    '埼玉県', '千葉県', '兵庫県', '京都府', '広島県', '静岡県', '茨城県',
    '新潟県', '長野県', '岐阜県', '栃木県', '群馬県', '岡山県'
]

COMPANY_TYPES = [
    'IT・Web', 'コンサルティング', '広告・メディア', '金融', '製造業',
    '小売・流通', '不動産', '教育', '医療・福祉', 'エンターテインメント'
]

REMOTE_WORK_OPTIONS = ['full', 'partial', 'none']

COMPANY_CULTURES = [
    'フラットな組織で風通しが良い',
    'スピード感を重視した意思決定',
    'チームワークを大切にする文化',
    '挑戦を歓迎する環境',
    '成長機会が豊富',
    '安定した大企業文化',
    'スタートアップの活気ある雰囲気',
    '専門性を高められる環境',
    'ワークライフバランス重視',
    'グローバルな環境'
]

WORK_FLEXIBILITY = [
    'フレックスタイム制度あり',
    '完全フレックス',
    '裁量労働制',
    '固定時間制',
    'コアタイムあり',
    '自由な働き方',
    '時短勤務可',
    'リモート中心'
]

KEYWORDS = [
    'React', 'Vue.js', 'Angular', 'TypeScript', 'JavaScript',
    'Python', 'Java', 'Go', 'Ruby', 'PHP',
    'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes',
    'リモート', 'フレックス', '副業OK', '研修充実', '英語',
    'スタートアップ', 'ベンチャー', '大手', '外資', '上場企業'
]

PAIN_POINTS = [
    '通勤時間が長い',
    '残業が多い',
    '給与が低い',
    'キャリアアップできない',
    'スキルが伸びない',
    '人間関係が悪い',
    '評価制度が不明瞭',
    '新しい技術に触れられない',
    'ワークライフバランスが悪い',
    '裁量がない'
]

END_REASONS = ['high_match', 'score_converged', 'user_requested', 'max_turns']


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ヘルパー関数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def random_date(start_days_ago=365, end_days_ago=0):
    """ランダムな日付を生成"""
    start = datetime.now() - timedelta(days=start_days_ago)
    end = datetime.now() - timedelta(days=end_days_ago)
    return start + (end - start) * random.random()


def generate_extracted_info():
    """AI抽出情報を生成"""
    return {
        "explicit_preferences": {
            "remote_work": random.choice(['強く希望', '希望', '不要', None]),
            "learning_interest": random.choice(KEYWORDS[:10] + [None]),
            "work_life_balance": random.choice(['重視', '普通', None]),
            "career_goal": random.choice([
                'スキルアップ', 'マネジメント', '起業準備', '安定', None
            ])
        },
        "implicit_values": {
            "work_life_balance_priority": random.randint(1, 5),
            "career_growth_priority": random.randint(1, 5),
            "salary_priority": random.randint(1, 5),
            "stability_priority": random.randint(1, 5)
        },
        "pain_points": random.sample(PAIN_POINTS, random.randint(0, 3)),
        "keywords": random.sample(KEYWORDS, random.randint(1, 5)),
        "confidence": round(random.uniform(0.5, 1.0), 2)
    }


def generate_insights():
    """蓄積された情報を生成"""
    extracted = generate_extracted_info()
    # 複数ターン分を統合したイメージ
    extracted['pain_points'] = random.sample(PAIN_POINTS, random.randint(1, 5))
    extracted['keywords'] = random.sample(KEYWORDS, random.randint(3, 8))
    return extracted


def generate_score_details():
    """スコア詳細を生成"""
    details = []
    if random.random() > 0.3:
        details.append(('リモートワーク可', 20))
    if random.random() > 0.5:
        details.append((f'{random.choice(KEYWORDS[:10])}使用', 15))
    if random.random() > 0.4:
        details.append(('柔軟な働き方', 10))
    if random.random() > 0.6:
        details.append(('成長環境', 8))
    return details


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# データ生成関数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_users(n=10000):
    """ユーザーデータ生成"""
    print(f"\n{'='*70}")
    print(f"1. Generating {n:,} users (personal_date + user_profile)...")
    print(f"{'='*70}")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    # personal_date
    users = []
    profiles = []
    
    for i in range(1, n + 1):
        email = f"user{i}@example.com"
        password_hash = generate_password_hash("password123")
        name = fake.name()
        birth_day = fake.date_of_birth(minimum_age=22, maximum_age=60)
        phone = fake.phone_number()
        address = fake.address().replace('\n', ' ')
        
        users.append((
            i, email, password_hash, name,
            birth_day, phone, address,
            random_date(365, 0), random_date(365, 0)
        ))
        
        # user_profile
        job_title = random.choice(JOB_TITLES)
        location = random.choice(PREFECTURES)
        salary_min = random.randint(300, 800)
        
        profiles.append((
            i, job_title, location, salary_min,
            random_date(365, 0), random_date(365, 0)
        ))
        
        if (i % 1000) == 0:
            print(f"  Progress: {i:,}/{n:,} users...")
    
    # バルクインサート
    cur.executemany("""
        INSERT INTO personal_date (
            user_id, email, password_hash, user_name,
            birth_day, phone_number, address,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """, users)
    
    cur.executemany("""
        INSERT INTO user_profile (
            user_id, job_title, location_prefecture, salary_min,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """, profiles)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ Created {n:,} users")
    print(f"✅ Created {n:,} user profiles")


def generate_companies_and_jobs(n_companies=1000, n_jobs=10000):
    """企業と求人データ生成"""
    print(f"\n{'='*70}")
    print(f"2. Generating {n_companies:,} companies and {n_jobs:,} jobs...")
    print(f"{'='*70}")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    # 企業データ
    companies = []
    company_ids = []
    
    for i in range(n_companies):
        record_id = str(uuid.uuid4())
        company_id = 10000 + i
        company_name = f"株式会社{fake.company()}"
        industry = random.choice(COMPANY_TYPES)
        
        companies.append((
            record_id, company_id, company_name, industry,
            random_date(1825, 0), random_date(365, 0)
        ))
        company_ids.append(company_id)
        
        if ((i + 1) % 200) == 0:
            print(f"  Progress: {i+1:,}/{n_companies:,} companies...")
    
    cur.executemany("""
        INSERT INTO company_date (
            id, company_id, company_name, industry,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, companies)
    
    print(f"✅ Created {n_companies:,} companies")
    
    # 求人データ
    jobs = []
    
    for i in range(n_jobs):
        company_id = random.choice(company_ids)
        job_title = random.choice(JOB_TITLES)
        location = random.choice(PREFECTURES)
        salary_min = random.randint(300, 800)
        salary_max = salary_min + random.randint(100, 400)
        remote_work = random.choice(REMOTE_WORK_OPTIONS)
        company_culture = random.choice(COMPANY_CULTURES)
        work_flexibility = random.choice(WORK_FLEXIBILITY)
        
        # job_summary
        tech_stack = random.sample(KEYWORDS[:15], random.randint(2, 5))
        job_summary = f"{job_title}を募集。{', '.join(tech_stack)}を使用した開発。"
        
        jobs.append((
            company_id, job_title, location,
            salary_min, salary_max,
            job_summary, remote_work,
            company_culture, work_flexibility,
            random_date(365, 0)
        ))
        
        if ((i + 1) % 2000) == 0:
            print(f"  Progress: {i+1:,}/{n_jobs:,} jobs...")
    
    cur.executemany("""
        INSERT INTO company_profile (
            company_id, job_title, location_prefecture,
            salary_min, salary_max,
            job_summary, remote_work,
            company_culture, work_flexibility,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, jobs)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ Created {n_jobs:,} jobs")


def generate_chat_history(n=50000):
    """チャット履歴生成"""
    print(f"\n{'='*70}")
    print(f"3. Generating {n:,} chat messages...")
    print(f"{'='*70}")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    messages = []
    
    for i in range(n):
        user_id = random.randint(1, 10000)
        session_id = str(uuid.uuid4())
        sender = random.choice(['user', 'bot'])
        
        if sender == 'user':
            message = random.choice([
                'リモートワークを希望します',
                '年収アップを目指しています',
                'Reactを使いたいです',
                'ワークライフバランスを重視します',
                'スキルアップできる環境を探しています'
            ])
        else:
            message = random.choice([
                '理想の働き方について教えてください',
                'その理由を詳しく聞かせていただけますか？',
                '最も重視する条件は何ですか？',
                'キャリアの目標について教えてください'
            ])
        
        extracted_intent = generate_extracted_info() if sender == 'user' else None
        
        messages.append((
            user_id, session_id, sender, message,
            json.dumps(extracted_intent, ensure_ascii=False) if extracted_intent else None,
            random_date(180, 0)
        ))
        
        if ((i + 1) % 10000) == 0:
            print(f"  Progress: {i+1:,}/{n:,} messages...")
    
    cur.executemany("""
        INSERT INTO chat_history (
            user_id, session_id, sender, message,
            extracted_intent, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, messages)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ Created {n:,} chat messages")


def generate_user_interactions(n=30000):
    """ユーザー行動履歴生成"""
    print(f"\n{'='*70}")
    print(f"4. Generating {n:,} user interactions...")
    print(f"{'='*70}")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    # 求人IDを取得
    cur.execute("SELECT id FROM company_profile LIMIT 10000")
    job_ids = [str(row[0]) for row in cur.fetchall()]
    
    interactions = []
    interaction_types = ['click', 'view', 'favorite', 'apply']
    
    for i in range(n):
        user_id = random.randint(1, 10000)
        job_id = random.choice(job_ids)
        interaction_type = random.choice(interaction_types)
        interaction_value = random.uniform(10, 300) if interaction_type == 'view' else 0
        
        interactions.append((
            user_id, job_id, interaction_type,
            interaction_value, None,
            random_date(180, 0)
        ))
        
        if ((i + 1) % 5000) == 0:
            print(f"  Progress: {i+1:,}/{n:,} interactions...")
    
    cur.executemany("""
        INSERT INTO user_interactions (
            user_id, job_id, interaction_type,
            interaction_value, metadata, created_at
        )
        VALUES (%s, %s::uuid, %s, %s, %s, %s)
    """, interactions)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ Created {n:,} user interactions")


def generate_conversation_data(n_sessions=10000):
    """会話データ生成（conversation_turns, user_insights, conversation_sessions）"""
    print(f"\n{'='*70}")
    print(f"5. Generating conversation data for {n_sessions:,} sessions...")
    print(f"{'='*70}")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    turns_data = []
    insights_data = []
    sessions_data = []
    
    for i in range(n_sessions):
        user_id = random.randint(1, 10000)
        session_id = str(uuid.uuid4())
        total_turns = random.randint(2, 10)
        
        # 各ターンのデータ
        for turn in range(1, total_turns + 1):
            user_message = f"ユーザーメッセージ{turn}"
            bot_message = f"ボットメッセージ{turn}"
            extracted_info = generate_extracted_info()
            top_score = random.uniform(0, 100)
            top_match_percentage = random.uniform(50, 100)
            candidate_count = random.randint(10, 100)
            
            turns_data.append((
                user_id, session_id, turn,
                user_message, bot_message,
                json.dumps(extracted_info, ensure_ascii=False),
                top_score, top_match_percentage, candidate_count,
                random_date(180, 0)
            ))
        
        # user_insights
        insights = generate_insights()
        insights_data.append((
            user_id, session_id,
            json.dumps(insights, ensure_ascii=False),
            random_date(180, 0), random_date(180, 0)
        ))
        
        # conversation_sessions
        end_reason = random.choice(END_REASONS)
        final_match_percentage = random.uniform(70, 100)
        presented_jobs = [str(uuid.uuid4()) for _ in range(5)]
        
        sessions_data.append((
            user_id, session_id, total_turns,
            end_reason, final_match_percentage,
            json.dumps(presented_jobs),
            random_date(180, 0)
        ))
        
        if ((i + 1) % 2000) == 0:
            print(f"  Progress: {i+1:,}/{n_sessions:,} sessions...")
    
    # conversation_turns
    print(f"  Inserting {len(turns_data):,} conversation turns...")
    cur.executemany("""
        INSERT INTO conversation_turns (
            user_id, session_id, turn_number,
            user_message, bot_message, extracted_info,
            top_score, top_match_percentage, candidate_count,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, turns_data)
    
    # user_insights
    print(f"  Inserting {len(insights_data):,} user insights...")
    cur.executemany("""
        INSERT INTO user_insights (
            user_id, session_id, insights,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, session_id) DO NOTHING
    """, insights_data)
    
    # conversation_sessions
    print(f"  Inserting {len(sessions_data):,} conversation sessions...")
    cur.executemany("""
        INSERT INTO conversation_sessions (
            user_id, session_id, total_turns,
            end_reason, final_match_percentage,
            presented_jobs, ended_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (session_id) DO NOTHING
    """, sessions_data)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ Created {len(turns_data):,} conversation turns")
    print(f"✅ Created {len(insights_data):,} user insights")
    print(f"✅ Created {len(sessions_data):,} conversation sessions")


def generate_score_history(n=100000):
    """スコア履歴生成"""
    print(f"\n{'='*70}")
    print(f"6. Generating {n:,} score history records...")
    print(f"{'='*70}")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    # セッションIDを取得
    cur.execute("SELECT session_id FROM conversation_sessions LIMIT 10000")
    session_ids = [row[0] for row in cur.fetchall()]
    
    # 求人IDを取得
    cur.execute("SELECT id FROM company_profile LIMIT 10000")
    job_ids = [str(row[0]) for row in cur.fetchall()]
    
    scores = []
    
    for i in range(n):
        user_id = random.randint(1, 10000)
        session_id = random.choice(session_ids)
        turn_number = random.randint(1, 10)
        job_id = random.choice(job_ids)
        score = random.uniform(0, 100)
        match_percentage = random.uniform(50, 100)
        score_details = generate_score_details()
        
        scores.append((
            user_id, session_id, turn_number,
            job_id, score, match_percentage,
            json.dumps(score_details, ensure_ascii=False),
            random_date(180, 0)
        ))
        
        if ((i + 1) % 20000) == 0:
            print(f"  Progress: {i+1:,}/{n:,} records...")
    
    cur.executemany("""
        INSERT INTO score_history (
            user_id, session_id, turn_number,
            job_id, score, match_percentage,
            score_details, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, scores)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ Created {n:,} score history records")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン実行
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """メイン処理"""
    print("\n" + "="*70)
    print("🚀 進化型AI求人マッチングシステム v3.0")
    print("   ダミーデータ生成スクリプト")
    print("="*70)
    print("\n⚠️  警告: このスクリプトは大量のデータを生成します")
    print("   実行時間: 約5-10分")
    print("   データベースの空き容量を確認してください")
    print("\n" + "="*70)
    
    response = input("\n続行しますか？ (yes/no): ")
    if response.lower() != 'yes':
        print("\n中断しました")
        return
    
    start_time = datetime.now()
    
    try:
        # 1. ユーザーデータ
        generate_users(n=10000)
        
        # 2. 企業・求人データ
        generate_companies_and_jobs(n_companies=1000, n_jobs=10000)
        
        # 3. チャット履歴
        generate_chat_history(n=50000)
        
        # 4. ユーザー行動
        generate_user_interactions(n=30000)
        
        # 5. 会話データ
        generate_conversation_data(n_sessions=10000)
        
        # 6. スコア履歴
        generate_score_history(n=100000)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "="*70)
        print("✅ すべてのダミーデータ生成が完了しました！")
        print("="*70)
        print(f"\n📊 生成されたデータ:")
        print(f"   - ユーザー: 10,000件")
        print(f"   - ユーザープロファイル: 10,000件")
        print(f"   - 企業: 1,000件")
        print(f"   - 求人: 10,000件")
        print(f"   - チャット履歴: 50,000件")
        print(f"   - ユーザー行動: 30,000件")
        print(f"   - 会話ターン: 約50,000件")
        print(f"   - ユーザー情報蓄積: 10,000件")
        print(f"   - 会話セッション: 10,000件")
        print(f"   - スコア履歴: 100,000件")
        print(f"\n⏱️  実行時間: {duration}")
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()