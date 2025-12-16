# check_questions.py
import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="jobmatch",
    user="devuser", password="devpass"
)
cur = conn.cursor()

cur.execute("SELECT id, question_key, question_text FROM dynamic_questions")
questions = cur.fetchall()

print("Current questions:")
for q in questions:
    print(f"  ID: {q[0]}, Key: {q[1]}, Text: {q[2]}")

cur.close()
conn.close()