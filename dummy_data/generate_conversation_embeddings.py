"""
user_conversation_embeddings テーブルにダミーデータを生成
エンベディングベクトルと会話サマリーを含む
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import random
from datetime import datetime, timedelta

# データベース接続
conn = psycopg2.connect(
    host="localhost", 
    port=5432, 
    dbname="jobmatch",
    user="devuser", 
    password="devpass"
)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 60)
print("user_conversation_embeddings ダミーデータ生成")
print("=" * 60)

# 1. 既存ユーザーを取得
print("\n[1] Getting existing users...")
cur.execute("SELECT user_id FROM personal_date ORDER BY user_id")
user_ids = [row['user_id'] for row in cur.fetchall()]

if not user_ids:
    print("  ⚠ No users found!")
    cur.close()
    conn.close()
    exit()

print(f"  Found {len(user_ids)} users")

# 2. 既存のエンベディングデータを確認
cur.execute("SELECT COUNT(*) FROM user_conversation_embeddings")
existing_count = cur.fetchone()['count']
print(f"  Existing embeddings: {existing_count}")

# 3. ダミーエンベディングと会話サマリーを生成
print("\n[2] Generating dummy embeddings...")

# 職種のバリエーション
jobs = ['エンジニア', 'デザイナー', '営業', 'マーケティング', 'コンサルタント', 
        '事務', '企画', '人事', '経理', 'カスタマーサポート',
        'プロジェクトマネージャー', 'データアナリスト', 'Webディレクター', '法務', '広報']

locations = ['東京都', '大阪府', '神奈川県', '愛知県', '福岡県',
             '北海道', '宮城県', '広島県', '京都府', '兵庫県']

# 回答のバリエーション
responses_pool = {
    'remote': [
        'はい、リモート勤務できる職場がいいです',
        'リモートワークは必須です',
        'フルリモート希望です',
        'リモートワークできる方がいいですが、必須ではないです',
        'いいえ、オフィス勤務を希望します'
    ],
    'flex_time': [
        'はい、フレックスタイムを希望します',
        'フレックス制度は魅力的です',
        'いいえ、特に必要ないです',
        'フレックスタイムは特に興味ないです'
    ],
    'company_type': [
        '大企業を希望します',
        'ベンチャー企業がいいです',
        'スタートアップに興味があります',
        '中堅企業を希望します',
        '企業規模は特にこだわりません'
    ],
    'overtime': [
        '残業は少なめがいいです',
        '残業はほとんどない職場がいいです',
        '多少の残業は問題ありません',
        '残業時間は特に気にしません'
    ],
    'growth': [
        'はい、成長機会を重視します',
        'キャリアアップできる環境がいいです',
        '成長機会は非常に重要です',
        'いいえ、特に重視しません'
    ],
    'training': [
        '研修制度は重要だと思います',
        'スキルアップ支援は必須です',
        '研修制度は充実している方がいいです',
        '研修制度は特に気にしません'
    ],
    'atmosphere': [
        '活気のある職場がいいです',
        'チームワークを大切にする文化がいいです',
        'フラットな組織がいいです',
        'チャレンジングな環境を希望します',
        '落ち着いた雰囲気の職場がいいです'
    ]
}

created_count = 0
skipped_count = 0

for i, user_id in enumerate(user_ids, 1):
    try:
        # ユーザープロファイルを取得
        cur.execute("""
            SELECT job_title, location_prefecture, salary_min
            FROM user_profile
            WHERE user_id = %s
        """, (user_id,))
        
        profile = cur.fetchone()
        
        if not profile:
            # プロファイルがない場合はランダムに生成
            job_title = random.choice(jobs)
            location = random.choice(locations)
            salary = random.randint(300, 1000)
        else:
            job_title = profile['job_title'] or random.choice(jobs)
            location = profile['location_prefecture'] or random.choice(locations)
            salary = profile['salary_min'] or random.randint(300, 1000)
        
        # 会話サマリーを生成
        conversation_text = f"""
職種: {job_title}
勤務地: {location}
希望年収: {salary}万円以上

【希望条件】
"""
        
        # ランダムに3〜7個の質問回答を生成
        num_responses = random.randint(3, 7)
        selected_questions = random.sample(list(responses_pool.keys()), min(num_responses, len(responses_pool)))
        
        for question_key in selected_questions:
            response = random.choice(responses_pool[question_key])
            conversation_text += f"- {response}\n"
        
        # ダミーエンベディングベクトルを生成（1536次元）
        # 実際のエンベディングではなく、ランダムな値で近似
        # 類似度計算のため、ある程度パターンを持たせる
        base_vector = [random.gauss(0, 0.1) for _ in range(1536)]
        
        # 職種や条件に応じて少しバイアスをかける（類似性を作るため）
        job_index = jobs.index(job_title) if job_title in jobs else 0
        for j in range(job_index * 100, (job_index + 1) * 100):
            if j < 1536:
                base_vector[j] += random.gauss(0.3, 0.05)
        
        # リモートワーク希望者は特定の次元を高くする
        if any('リモート' in q or 'remote' in q.lower() for q in conversation_text.split('\n')):
            for j in range(1400, 1450):
                base_vector[j] += 0.5
        
        # 大企業希望者は特定の次元を高くする
        if '大企業' in conversation_text:
            for j in range(1450, 1500):
                base_vector[j] += 0.5
        
        embedding_json = json.dumps(base_vector)
        
        # データベースに挿入
        cur.execute("""
            INSERT INTO user_conversation_embeddings (user_id, embedding_vector, conversation_summary, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                embedding_vector = EXCLUDED.embedding_vector,
                conversation_summary = EXCLUDED.conversation_summary,
                updated_at = NOW()
        """, (user_id, embedding_json, conversation_text[:500]))
        
        created_count += 1
        
        if created_count % 100 == 0:
            print(f"  [{created_count}/{len(user_ids)}] Created")
            conn.commit()
            
    except Exception as e:
        skipped_count += 1
        if skipped_count <= 5:
            print(f"  Error for user {user_id}: {e}")

conn.commit()

print(f"\n✓ Created/Updated {created_count} embeddings")
print(f"  Skipped: {skipped_count}")

# 統計を表示
print("\n[3] Statistics...")

cur.execute("""
    SELECT COUNT(*) as total
    FROM user_conversation_embeddings
""")
total = cur.fetchone()['total']
print(f"  Total embeddings: {total:,}")

# サンプルを表示
print("\n[4] Sample data...")
cur.execute("""
    SELECT user_id, LEFT(conversation_summary, 100) as summary
    FROM user_conversation_embeddings
    ORDER BY RANDOM()
    LIMIT 3
""")

samples = cur.fetchall()
for i, sample in enumerate(samples, 1):
    print(f"\n  Sample {i} (user_id={sample['user_id']}):")
    print(f"  {sample['summary']}...")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("✓ Dummy embeddings generation completed!")
print("=" * 60)