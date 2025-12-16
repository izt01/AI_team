from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2, uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import os
from dotenv import load_dotenv
from db_config import get_db_conn

# --- 環境変数読み込み ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

company_app = Flask(__name__)
company_app.secret_key = "company-secret"

# --- エンベディング生成 ---
def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

@company_app.route("/")
def index():
    # 最初のアクセスは企業登録画面へ
    return redirect(url_for("company_register"))

@company_app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email_address"]
        password = request.form["password"]

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT password, company_id FROM company_date WHERE email=%s", (email,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row and check_password_hash(row[0], password):
            # ログイン成功
            session["company_email"] = email
            session["company_id"] = row[1]
            return redirect(url_for("job_list"))
        else:
            # ログイン失敗
            return render_template("company_login.html", error="メールアドレスまたはパスワードが違います")

    return render_template("company_login.html")


# --- 企業登録 ---
@company_app.route("/company/register", methods=["GET", "POST"])
def company_register():
    if request.method == "POST":
        company_name = request.form["company_name"]
        email = request.form["email_address"]
        password = generate_password_hash(request.form["password"])

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO company_date (
                id, company_id, email, password, company_name,
                address, phone_number, website_url, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (email) DO NOTHING
        """, (
            str(uuid.uuid4()), str(uuid.uuid4()), email, password, company_name,
            request.form.get("address", ""),
            request.form.get("phone_number", ""),
            request.form.get("website_url", "")
        ))
        conn.commit()
        cur.close()
        conn.close()

        session["company_email"] = email
        return redirect(url_for("job_new"))

    return render_template("company_register.html")

# --- 求人登録 ---
@company_app.route("/job/new", methods=["GET", "POST"])
def job_new():
    if request.method == "POST":
        job_title = request.form["job_title"]
        salary_min = int(request.form["salary_min"])
        salary_max = int(request.form["salary_max"])

        # 任意項目を intent_labels にまとめる
        labels = []
        bonus = request.form.get("bonus", "")
        overtime = request.form.get("overtime", "")
        atmosphere = request.form.get("workplace_atmosphere", "")
        if bonus: labels.append(bonus)
        if overtime: labels.append(overtime)
        if atmosphere: labels.append(atmosphere)
        intent_labels = ",".join(labels) if labels else None

        profile_text = " ".join([job_title, str(salary_min), str(salary_max), intent_labels or ""])
        embedding = get_embedding(profile_text)

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO company_profile (
                id, company_id, job_title, salary_min, salary_max,
                intent_labels, embedding, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            str(uuid.uuid4()), str(uuid.uuid4()), job_title, salary_min, salary_max,
            intent_labels, embedding
        ))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("job_list"))

    return render_template("job_form.html")

# --- 求人一覧 ---
@company_app.route("/jobs")
def job_list():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, job_title, salary_min, salary_max, intent_labels FROM company_profile")
    jobs = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("job_list.html", jobs=jobs)

# --- 求人詳細 ---
@company_app.route("/job/<uuid:job_id>")
def job_detail(job_id):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM company_profile WHERE id=%s", (str(job_id),))
    job = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("job_detail.html", job=job)

# --- メイン起動 ---
if __name__ == "__main__":
    company_app.run(debug=True, port=5001)