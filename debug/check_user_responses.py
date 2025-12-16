# check_user_responses.py
import psycopg2

# 最新のユーザーIDを取得
conn = psycopg2.connect(
    host="localhost", port=5432, dbname="jobmatch",
    user="devuser", password="devpass"
)
cur = conn.cursor()

# 最新のユーザー
cur.execute("SELECT user_id, user_name FROM personal_date ORDER BY created_at DESC LIMIT 1")
user = cur.fetchone()

if user:
    user_id = user[0]
    print(f"Checking responses for user_id: {user_id} ({user[1]})")
    
    # 回答履歴を取得
    cur.execute("""
        SELECT dq.question_key, dq.question_text, uqr.response_text, uqr.normalized_response
        FROM user_question_responses uqr
        JOIN dynamic_questions dq ON uqr.question_id = dq.id
        WHERE uqr.user_id = %s
        ORDER BY uqr.created_at
    """, (user_id,))
    
    responses = cur.fetchall()
    
    if responses:
        print(f"\nTotal responses: {len(responses)}")
        for r in responses:
            print(f"\n  Question Key: {r[0]}")
            print(f"  Question: {r[1]}")
            print(f"  User Answer: {r[2]}")
            print(f"  Normalized: {r[3]}")
    else:
        print("No responses found")
else:
    print("No users found")

cur.close()
conn.close()