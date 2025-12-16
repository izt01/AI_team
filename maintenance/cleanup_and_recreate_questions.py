# cleanup_and_recreate_questions.py
import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="jobmatch",
    user="devuser", password="devpass"
)
cur = conn.cursor()

# 1. 既存の質問への回答を削除（外部キー制約のため）
cur.execute("DELETE FROM user_question_responses")
print("✓ Deleted old responses")

# 2. 既存の質問を削除
cur.execute("DELETE FROM dynamic_questions")
print("✓ Deleted old questions")

# 3. 正しい質問を挿入
initial_questions = [
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

for q_key, q_text, category, q_type in initial_questions:
    cur.execute("""
        INSERT INTO dynamic_questions (question_key, question_text, category, question_type)
        VALUES (%s, %s, %s, %s)
    """, (q_key, q_text, category, q_type))
    print(f"✓ Inserted: {q_key} - {q_text}")

conn.commit()

# 4. 確認
cur.execute("SELECT id, question_key, question_text FROM dynamic_questions ORDER BY id")
questions = cur.fetchall()

print("\n=== Final Questions ===")
for q in questions:
    print(f"  ID: {q[0]}, Key: {q[1]}, Text: {q[2]}")

cur.close()
conn.close()

print("\n✓ Questions cleaned up and recreated successfully!")