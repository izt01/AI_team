import psycopg2
from psycopg2.extras import execute_values
import random
from datetime import datetime, timedelta
from faker import Faker
from werkzeug.security import generate_password_hash
import json

# Faker初期化（日本語データ生成用）
fake = Faker('ja_JP')

# DB接続
def get_db_conn():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="jobmatch",
        user="devuser",
        password="devpass"
    )

# ==========================================
# 1. user_interactions テーブル（1万件）
# ==========================================
def insert_user_interactions(conn, num_records=10000):
    print(f"user_interactions に {num_records} 件挿入中...")
    cur = conn.cursor()
    
    # 既存のuser_idを取得
    cur.execute("SELECT user_id FROM personal_date LIMIT 100")
    user_ids = [row[0] for row in cur.fetchall()]
    
    if not user_ids:
        print("⚠️ personal_dateにユーザーが存在しません。先にユーザーを作成してください。")
        return
    
    # job_idは1〜1000の範囲と仮定
    job_ids = list(range(1, 1001))
    interaction_types = ['click', 'favorite', 'apply', 'view', 'chat_mention']
    
    data = []
    for _ in range(num_records):
        user_id = random.choice(user_ids)
        job_id = random.choice(job_ids)
        interaction_type = random.choice(interaction_types)
        interaction_value = round(random.uniform(5.0, 300.0), 2) if interaction_type == 'view' else 0.0
        metadata = json.dumps({
            "device": random.choice(["mobile", "desktop", "tablet"]),
            "source": random.choice(["search", "recommendation", "direct"])
        })
        created_at = fake.date_time_between(start_date='-1y', end_date='now')
        
        data.append((user_id, job_id, interaction_type, interaction_value, metadata, created_at))
    
    execute_values(
        cur,
        """INSERT INTO user_interactions (user_id, job_id, interaction_type, interaction_value, metadata, created_at)
           VALUES %s""",
        data
    )
    conn.commit()
    print(f"✅ user_interactions に {num_records} 件挿入完了")

# ==========================================
# 2. chat_history テーブル（1万件）
# ==========================================
def insert_chat_history(conn, num_records=10000):
    print(f"chat_history に {num_records} 件挿入中...")
    cur = conn.cursor()
    
    cur.execute("SELECT user_id FROM personal_date LIMIT 100")
    user_ids = [row[0] for row in cur.fetchall()]
    
    if not user_ids:
        print("⚠️ personal_dateにユーザーが存在しません")
        return
    
    message_types = ['user', 'bot']
    user_messages = [
        "リモートワーク希望です", "年収600万以上がいいです", "東京で働きたい",
        "フレックスタイム制度はありますか？", "スキルアップできる環境がいいです",
        "副業可能ですか？", "残業は少なめがいいです", "研修制度が充実している会社がいいです"
    ]
    bot_messages = [
        "承知しました。リモートワーク可能な求人を検索します。",
        "年収600万以上の求人が50件見つかりました。",
        "東京都内の求人を表示します。",
        "フレックスタイム制度がある求人は30件です。"
    ]
    
    data = []
    session_id = None
    for i in range(num_records):
        if i % 10 == 0:  # 10件ごとに新しいセッション
            session_id = fake.uuid4()
        
        user_id = random.choice(user_ids)
        message_type = random.choice(message_types)
        message_text = random.choice(user_messages if message_type == 'user' else bot_messages)
        extracted_intent = json.dumps({
            "intent": random.choice(["search", "filter", "question", "feedback"]),
            "entities": {"salary": 600, "location": "東京"}
        }) if message_type == 'user' else None
        created_at = fake.date_time_between(start_date='-6m', end_date='now')
        
        data.append((user_id, message_type, message_text, extracted_intent, session_id, created_at))
    
    execute_values(
        cur,
        """INSERT INTO chat_history (user_id, message_type, message_text, extracted_intent, session_id, created_at)
           VALUES %s""",
        data
    )
    conn.commit()
    print(f"✅ chat_history に {num_records} 件挿入完了")

# ==========================================
# 3. user_question_responses テーブル（5000件）
# ==========================================
def insert_user_question_responses(conn, num_records=5000):
    print(f"user_question_responses に {num_records} 件挿入中...")
    cur = conn.cursor()
    
    cur.execute("SELECT user_id FROM personal_date LIMIT 100")
    user_ids = [row[0] for row in cur.fetchall()]
    
    cur.execute("SELECT id FROM dynamic_questions")
    question_ids = [row[0] for row in cur.fetchall()]
    
    if not user_ids:
        print("⚠️ personal_dateにデータがありません")
        return
    
    if not question_ids:
        print("⚠️ dynamic_questionsにデータがありません。schema_extension.sqlを実行してください。")
        return
    
    # 最大挿入可能件数を計算（ユーザー数 × 質問数）
    max_possible = len(user_ids) * len(question_ids)
    actual_records = min(num_records, max_possible)
    
    if actual_records < num_records:
        print(f"⚠️ ユーザー数と質問数の制約により、{actual_records}件のみ挿入します")
    
    responses = ["はい", "いいえ", "リモートワーク希望", "フレックス希望", "副業可能がいい", "大企業", "ベンチャー"]
    normalized = ["yes", "no", "remote", "flex", "side_job", "large", "startup"]
    
    # すべての組み合わせを生成
    all_combinations = [(u, q) for u in user_ids for q in question_ids]
    random.shuffle(all_combinations)
    
    data = []
    for i, (user_id, question_id) in enumerate(all_combinations[:actual_records]):
        response_text = random.choice(responses)
        normalized_response = random.choice(normalized)
        confidence_score = round(random.uniform(0.7, 1.0), 2)
        created_at = fake.date_time_between(start_date='-6m', end_date='now')
        
        data.append((user_id, question_id, response_text, normalized_response, confidence_score, created_at))
        
        # 進捗表示
        if (i + 1) % 1000 == 0:
            print(f"  {i + 1}/{actual_records} 件準備完了...")
    
    execute_values(
        cur,
        """INSERT INTO user_question_responses (user_id, question_id, response_text, normalized_response, confidence_score, created_at)
           VALUES %s ON CONFLICT (user_id, question_id) DO NOTHING""",
        data
    )
    conn.commit()
    print(f"✅ user_question_responses に {actual_records} 件挿入完了")

# ==========================================
# 4. job_attributes テーブル（1000件）
# ==========================================
def insert_job_attributes(conn, num_records=1000):
    print(f"job_attributes に {num_records} 件挿入中...")
    cur = conn.cursor()
    
    data = []
    for job_id in range(1, num_records + 1):
        company_culture = json.dumps({
            "type": random.choice(["startup", "enterprise", "midsize"]),
            "atmosphere": random.choice(["flat", "hierarchical", "creative"]),
            "size": random.choice(["small", "medium", "large"])
        })
        work_flexibility = json.dumps({
            "remote": random.choice([True, False]),
            "flex_time": random.choice([True, False]),
            "side_job": random.choice([True, False])
        })
        career_path = json.dumps({
            "growth_opportunities": random.choice([True, False]),
            "training": random.choice([True, False]),
            "promotion_speed": random.choice(["fast", "medium", "slow"])
        })
        
        data.append((job_id, company_culture, work_flexibility, career_path))
    
    execute_values(
        cur,
        """INSERT INTO job_attributes (job_id, company_culture, work_flexibility, career_path)
           VALUES %s ON CONFLICT (job_id) DO NOTHING""",
        data
    )
    conn.commit()
    print(f"✅ job_attributes に {num_records} 件挿入完了")

# ==========================================
# 5. user_preferences テーブル（100件）
# ==========================================
def insert_user_preferences(conn, num_records=100):
    print(f"user_preferences に {num_records} 件挿入中...")
    cur = conn.cursor()
    
    cur.execute("SELECT user_id FROM personal_date LIMIT 100")
    user_ids = [row[0] for row in cur.fetchall()]
    
    if not user_ids:
        print("⚠️ personal_dateにユーザーが存在しません")
        return
    
    data = []
    for user_id in user_ids[:num_records]:
        # ダミーのベクトル（1536次元）
        preference_vector = [random.uniform(-1, 1) for _ in range(1536)]
        company_culture_pref = json.dumps({
            "preferred_type": random.choice(["startup", "enterprise"]),
            "atmosphere": random.choice(["flat", "creative"])
        })
        work_flexibility_pref = json.dumps({
            "remote": random.choice([True, False]),
            "flex_time": random.choice([True, False])
        })
        career_path_pref = json.dumps({
            "growth": random.choice([True, False]),
            "training": random.choice([True, False])
        })
        preference_text = fake.text(max_nb_chars=200)
        
        data.append((user_id, preference_vector, company_culture_pref, work_flexibility_pref, career_path_pref, preference_text))
    
    execute_values(
        cur,
        """INSERT INTO user_preferences (user_id, preference_vector, company_culture_pref, work_flexibility_pref, career_path_pref, preference_text)
           VALUES %s ON CONFLICT (user_id) DO NOTHING""",
        data
    )
    conn.commit()
    print(f"✅ user_preferences に {num_records} 件挿入完了")

# ==========================================
# 6. ml_model_scores テーブル（1万件）
# ==========================================
def insert_ml_model_scores(conn, num_records=10000):
    print(f"ml_model_scores に {num_records} 件挿入中...")
    cur = conn.cursor()
    
    cur.execute("SELECT user_id FROM personal_date LIMIT 100")
    user_ids = [row[0] for row in cur.fetchall()]
    
    if not user_ids:
        print("⚠️ personal_dateにユーザーが存在しません")
        return
    
    job_ids = list(range(1, 1001))
    model_versions = ["v1.0", "v1.1", "v2.0"]
    
    data = []
    used_pairs = set()
    
    while len(data) < num_records:
        user_id = random.choice(user_ids)
        job_id = random.choice(job_ids)
        model_version = random.choice(model_versions)
        triple = (user_id, job_id, model_version)
        
        if triple in used_pairs:
            continue
        used_pairs.add(triple)
        
        score = round(random.uniform(0.0, 1.0), 3)
        feature_importance = json.dumps({
            "salary_match": round(random.uniform(0, 1), 2),
            "location_match": round(random.uniform(0, 1), 2),
            "skill_match": round(random.uniform(0, 1), 2)
        })
        created_at = fake.date_time_between(start_date='-3m', end_date='now')
        
        data.append((user_id, job_id, score, model_version, feature_importance, created_at))
    
    execute_values(
        cur,
        """INSERT INTO ml_model_scores (user_id, job_id, score, model_version, feature_importance, created_at)
           VALUES %s ON CONFLICT (user_id, job_id, model_version) DO NOTHING""",
        data
    )
    conn.commit()
    print(f"✅ ml_model_scores に {num_records} 件挿入完了")

# ==========================================
# 0-1. company_dateにダミー企業を作成
# ==========================================
def insert_dummy_companies(conn, num_companies=100):
    print(f"company_date に {num_companies} 件のダミー企業を挿入中...")
    cur = conn.cursor()
    
    # 既存企業数を確認
    cur.execute("SELECT COUNT(*) FROM company_date")
    existing_count = cur.fetchone()[0]
    
    if existing_count >= num_companies:
        print(f"✅ 既に {existing_count} 件の企業が存在します。スキップします。")
        return
    
    company_types = ["株式会社", "合同会社", "有限会社"]
    company_names = [
        "テクノロジー", "ソリューションズ", "システムズ", "エンジニアリング",
        "コンサルティング", "マーケティング", "デザイン", "クリエイト",
        "イノベーション", "ストラテジー", "グローバル", "アドバンス"
    ]
    
    data = []
    for i in range(num_companies):
        email = f"company{i+1}@example.jp"
        password_hash = generate_password_hash("company123")
        company_name = f"{random.choice(company_types)}{random.choice(company_names)}{random.choice(company_names)}"
        address = fake.address()
        phone_number = fake.phone_number()
        website_url = f"https://www.company{i+1}.co.jp"
        
        data.append((email, password_hash, company_name, address, phone_number, website_url))
    
    execute_values(
        cur,
        """INSERT INTO company_date (email, password, company_name, address, phone_number, website_url, created_at, updated_at)
           VALUES %s""",
        [(d[0], d[1], d[2], d[3], d[4], d[5], datetime.now(), datetime.now()) for d in data]
    )
    conn.commit()
    print(f"✅ company_date に {num_companies} 件のダミー企業を挿入完了")

# ==========================================
# 0-2. company_profileに求人情報を作成（1万件）
# ==========================================
def insert_company_profiles(conn, num_jobs=10000):
    print(f"company_profile に {num_jobs} 件の求人を挿入中...")
    cur = conn.cursor()
    
    # 既存の企業IDを取得
    cur.execute("SELECT company_id FROM company_date")
    company_ids = [row[0] for row in cur.fetchall()]
    
    if not company_ids:
        print("⚠️ company_dateに企業が存在しません。先に企業を作成してください。")
        return
    
    # 求人データのマスタ
    job_titles = [
        "Webエンジニア", "フロントエンドエンジニア", "バックエンドエンジニア",
        "データサイエンティスト", "AIエンジニア", "インフラエンジニア",
        "営業", "マーケター", "デザイナー", "プロダクトマネージャー",
        "人事", "経理", "法務", "カスタマーサポート"
    ]
    
    prefectures = [
        "東京都", "神奈川県", "大阪府", "愛知県", "福岡県",
        "北海道", "宮城県", "埼玉県", "千葉県", "兵庫県","静岡県"
    ]
    
    intent_labels_list = [
        "リモート可,フレックス,副業OK",
        "残業少なめ,土日祝休み,完全週休2日",
        "研修充実,キャリアアップ,資格取得支援",
        "フラットな組織,裁量大,スタートアップ",
        "大企業,安定,福利厚生充実",
        "静かな職場,集中できる環境,私服OK"
    ]
    
    data = []
    for i in range(num_jobs):
        company_id = random.choice(company_ids)
        job_title = random.choice(job_titles)
        location_prefecture = random.choice(prefectures)
        salary_min = random.choice([300, 350, 400, 450, 500, 550, 600])
        salary_max = salary_min + random.choice([100, 150, 200, 250, 300])
        intent_labels = random.choice(intent_labels_list)
        
        # ダミーのembeddingベクトル（768次元）
        embedding_vector = [random.uniform(-1, 1) for _ in range(768)]
        
        data.append((
            company_id, job_title, location_prefecture,
            salary_min, salary_max, intent_labels, embedding_vector
        ))
        
        # 進捗表示
        if (i + 1) % 2000 == 0:
            print(f"  {i + 1}/{num_jobs} 件準備完了...")
    
    execute_values(
        cur,
        """INSERT INTO company_profile 
           (company_id, job_title, location_prefecture, salary_min, salary_max, intent_labels, embedding, created_at, updated_at)
           VALUES %s""",
        [(d[0], d[1], d[2], d[3], d[4], d[5], d[6], datetime.now(), datetime.now()) for d in data]
    )
    conn.commit()
    print(f"✅ company_profile に {num_jobs} 件の求人を挿入完了")

# ==========================================
# 0. personal_dateにダミーユーザーを作成（必要な場合）
# ==========================================
def insert_dummy_users(conn, num_users=50):
    print(f"personal_date に {num_users} 件のダミーユーザーを挿入中...")
    cur = conn.cursor()
    
    # 既存ユーザー数を確認
    cur.execute("SELECT COUNT(*) FROM personal_date")
    existing_count = cur.fetchone()[0]
    
    if existing_count >= num_users:
        print(f"✅ 既に {existing_count} 件のユーザーが存在します。スキップします。")
        return
    
    from werkzeug.security import generate_password_hash
    
    data = []
    for i in range(num_users):
        email = fake.email()
        password_hash = generate_password_hash("password123")
        user_name = fake.name()
        birth_day = fake.date_of_birth(minimum_age=20, maximum_age=65)
        phone_number = fake.phone_number()
        address = fake.address()
        
        data.append((email, password_hash, user_name, birth_day, phone_number, address))
    
    execute_values(
        cur,
        """INSERT INTO personal_date (email, password_hash, user_name, birth_day, phone_number, address, created_at, updated_at)
           VALUES %s""",
        [(d[0], d[1], d[2], d[3], d[4], d[5], datetime.now(), datetime.now()) for d in data]
    )
    conn.commit()
    print(f"✅ personal_date に {num_users} 件のダミーユーザーを挿入完了")

# ==========================================
# メイン実行
# ==========================================
def main():
    print("=" * 50)
    print("ダミーデータ生成開始")
    print("=" * 50)
    
    conn = get_db_conn()
    
    try:
        # まず企業とユーザーを作成
        insert_dummy_companies(conn, 100)
        insert_dummy_users(conn, 50)
        
        # 企業の求人情報を作成（1万件）
        insert_company_profiles(conn, 10000)
        
        # その他のテーブル
        insert_user_interactions(conn, 10000)
        insert_chat_history(conn, 10000)
        insert_user_question_responses(conn, 5000)
        insert_job_attributes(conn, 1000)
        insert_user_preferences(conn, 100)
        insert_ml_model_scores(conn, 10000)
        
        print("=" * 50)
        print("✅ すべてのダミーデータ生成完了！")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()