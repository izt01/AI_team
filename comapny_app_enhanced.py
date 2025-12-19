"""
企業向けアプリケーション（スカウト機能追加版）
- 求人登録
- スカウト候補者検索
- スカウトメッセージ送信
- スカウト履歴管理
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from db_config import get_db_conn
from company_scout_system import (
    UserProfileAnalyzer,
    ScoutSearchEngine,
    ScoutMessageManager,
    get_top_candidates_for_job
)

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
    if 'company_id' in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

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
            return redirect(url_for("dashboard"))
        else:
            # ログイン失敗
            return render_template("company_login.html", error="メールアドレスまたはパスワードが違います")

    return render_template("company_login.html")

@company_app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- ダッシュボード ---
@company_app.route("/dashboard")
def dashboard():
    """企業ダッシュボード"""
    if 'company_id' not in session:
        return redirect(url_for("login"))
    
    company_id = session['company_id']
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 企業情報
    cur.execute("SELECT * FROM company_date WHERE company_id = %s", (company_id,))
    company = cur.fetchone()
    
    # 求人数
    cur.execute("SELECT COUNT(*) as count FROM company_profile WHERE company_id = %s", (company_id,))
    job_count = cur.fetchone()['count']
    
    # スカウト送信数（今月）
    cur.execute("""
        SELECT COUNT(*) as count FROM scout_messages 
        WHERE company_id = %s 
        AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
    """, (company_id,))
    scout_count = cur.fetchone()['count']
    
    # スカウト返信率
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN status = 'replied' THEN 1 END) as replied
        FROM scout_messages 
        WHERE company_id = %s
    """, (company_id,))
    scout_stats = cur.fetchone()
    
    reply_rate = 0
    if scout_stats['total'] > 0:
        reply_rate = (scout_stats['replied'] / scout_stats['total']) * 100
    
    cur.close()
    conn.close()
    
    return render_template("company_dashboard.html",
                         company=company,
                         job_count=job_count,
                         scout_count=scout_count,
                         reply_rate=reply_rate)

# --- 企業登録 ---
@company_app.route("/company/register", methods=["GET", "POST"])
def company_register():
    if request.method == "POST":
        company_name = request.form["company_name"]
        email = request.form["email_address"]
        password = generate_password_hash(request.form["password"])

        conn = get_db_conn()
        cur = conn.cursor()
        
        company_id = str(uuid.uuid4())
        
        cur.execute("""
            INSERT INTO company_date (
                id, company_id, email, password, company_name,
                address, phone_number, website_url, 
                industry, company_size, established_year,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (email) DO NOTHING
        """, (
            str(uuid.uuid4()), company_id, email, password, company_name,
            request.form.get("address", ""),
            request.form.get("phone_number", ""),
            request.form.get("website_url", ""),
            request.form.get("industry", ""),
            request.form.get("company_size", ""),
            request.form.get("established_year")
        ))
        conn.commit()
        cur.close()
        conn.close()

        session["company_email"] = email
        session["company_id"] = company_id
        return redirect(url_for("dashboard"))

    return render_template("company_register.html")

# --- 求人登録 ---
@company_app.route("/job/new", methods=["GET", "POST"])
def job_new():
    if 'company_id' not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        company_id = session['company_id']
        job_title = request.form["job_title"]
        job_description = request.form.get("job_description", "")
        location_prefecture = request.form.get("location_prefecture", "")
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

        # エンベディング生成用テキスト
        profile_text = " ".join([
            job_title, 
            job_description,
            location_prefecture,
            str(salary_min), 
            str(salary_max), 
            intent_labels or ""
        ])
        embedding = get_embedding(profile_text)

        conn = get_db_conn()
        cur = conn.cursor()
        
        job_id = str(uuid.uuid4())
        
        cur.execute("""
            INSERT INTO company_profile (
                id, company_id, job_title, job_description, location_prefecture,
                salary_min, salary_max, intent_labels, embedding, 
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            job_id, company_id, job_title, job_description, location_prefecture,
            salary_min, salary_max, intent_labels, embedding
        ))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("job_detail", job_id=job_id))

    return render_template("job_form.html")

# --- 求人一覧 ---
@company_app.route("/jobs")
def job_list():
    if 'company_id' not in session:
        return redirect(url_for("login"))
    
    company_id = session['company_id']
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT id, job_title, location_prefecture, salary_min, salary_max, 
               intent_labels, created_at,
               click_count, favorite_count, apply_count
        FROM company_profile 
        WHERE company_id = %s
        ORDER BY created_at DESC
    """, (company_id,))
    jobs = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template("job_list.html", jobs=jobs)

# --- 求人詳細 ---
@company_app.route("/job/<job_id>")
def job_detail(job_id):
    if 'company_id' not in session:
        return redirect(url_for("login"))
    
    company_id = session['company_id']
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM company_profile 
        WHERE id = %s AND company_id = %s
    """, (job_id, company_id))
    job = cur.fetchone()
    cur.close()
    conn.close()
    
    if not job:
        return "求人が見つかりません", 404
    
    # company情報を作成
    company = {
        'company_name': job.get('company_name', '企業名非公開'),
        'company_id': job.get('company_id'),
        'industry': job.get('industry'),
        'company_size': job.get('company_size'),
        'website': job.get('website')
    }
    
    # jobとcompanyの両方を渡す
    return render_template("job_detail.html", job=job, company=company)

# --- スカウト候補者検索 ---
@company_app.route("/job/<job_id>/scout_search")
def scout_search(job_id):
    """スカウト候補者検索画面"""
    if 'company_id' not in session:
        return redirect(url_for("login"))
    
    company_id = session['company_id']
    
    # 求人情報を取得
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT cp.*, cd.company_name 
        FROM company_profile cp
        JOIN company_date cd ON cp.company_id = cd.company_id
        WHERE cp.id = %s AND cp.company_id = %s
    """, (job_id, company_id))
    job = cur.fetchone()
    cur.close()
    conn.close()
    
    if not job:
        return "求人が見つかりません", 404
    
    return render_template("scout_search.html", job=job)

# --- スカウト候補者検索API ---
@company_app.route("/api/job/<job_id>/candidates", methods=["POST"])
def api_search_candidates(job_id):
    """スカウト候補者を検索（API）"""
    if 'company_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    company_id = session['company_id']
    
    # フィルター条件を取得
    filters = request.json.get('filters', {})
    top_k = request.json.get('top_k', 20)
    
    # 候補者を検索
    candidates = ScoutSearchEngine.search_candidates(
        company_id=company_id,
        job_id=job_id,
        filters=filters,
        top_k=top_k
    )
    
    return jsonify({
        "status": "success",
        "count": len(candidates),
        "candidates": candidates
    })

# --- スカウトメッセージ送信 ---
@company_app.route("/api/scout/send", methods=["POST"])
def api_send_scout():
    """スカウトメッセージを送信（API）"""
    if 'company_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    company_id = session['company_id']
    job_id = request.json.get('job_id')
    user_id = request.json.get('user_id')
    message_text = request.json.get('message_text')
    auto_generated = request.json.get('auto_generated', False)
    
    if not all([job_id, user_id, message_text]):
        return jsonify({"error": "Missing required fields"}), 400
    
    success = ScoutMessageManager.send_scout_message(
        company_id=company_id,
        job_id=job_id,
        user_id=user_id,
        message_text=message_text,
        auto_generated=auto_generated
    )
    
    if success:
        return jsonify({"status": "success", "message": "スカウトを送信しました"})
    else:
        return jsonify({"error": "Failed to send scout"}), 500

# --- スカウトメッセージ自動生成 ---
@company_app.route("/api/scout/generate_message", methods=["POST"])
def api_generate_scout_message():
    """スカウトメッセージを自動生成（API）"""
    if 'company_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    company_id = session['company_id']
    job_id = request.json.get('job_id')
    user_id = request.json.get('user_id')
    
    if not all([job_id, user_id]):
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 求人情報を取得
        cur.execute("""
            SELECT cp.*, cd.company_name 
            FROM company_profile cp
            JOIN company_date cd ON cp.company_id = cd.company_id
            WHERE cp.id = %s AND cp.company_id = %s
        """, (job_id, company_id))
        job_info = cur.fetchone()
        
        # ユーザー情報を取得
        cur.execute("""
            SELECT pd.user_id, pd.user_name,
                   up.job_title, up.location_prefecture, up.salary_min
            FROM personal_date pd
            JOIN user_profile up ON pd.user_id = up.user_id
            WHERE pd.user_id = %s
        """, (user_id,))
        user_profile = cur.fetchone()
        
        # 性格分析を取得
        cur.execute("""
            SELECT analysis_data
            FROM user_personality_analysis
            WHERE user_id = %s
        """, (user_id,))
        analysis_row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        user_analysis = {}
        if analysis_row and analysis_row['analysis_data']:
            user_analysis = json.loads(analysis_row['analysis_data'])
        
        # メッセージ生成
        message = ScoutMessageManager.generate_scout_message(
            job_info=dict(job_info),
            user_profile=dict(user_profile),
            user_analysis=user_analysis
        )
        
        return jsonify({
            "status": "success",
            "message": message
        })
        
    except Exception as e:
        print(f"Error generating scout message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- スカウト履歴 ---
@company_app.route("/scouts")
def scout_history():
    """スカウト送信履歴"""
    if 'company_id' not in session:
        return redirect(url_for("login"))
    
    company_id = session['company_id']
    
    history = ScoutMessageManager.get_scout_history(company_id, limit=100)
    
    return render_template("scout_history.html", scouts=history)

# --- AIチャット検索 ---
@company_app.route("/scout/ai-search")
def scout_ai_search():
    """AIチャット形式のスカウト候補検索"""
    if 'company_id' not in session:
        return redirect(url_for("login"))
    
    return render_template("scout_ai_search.html")

@company_app.route("/scout/debug")
def scout_debug():
    """スカウト検索のデバッグページ"""
    if 'company_id' not in session:
        return redirect(url_for("login"))
    
    return render_template("scout_search_debug.html")

@company_app.route("/candidate/<int:user_id>")
def candidate_detail(user_id):
    """候補者の詳細ページ"""
    if 'company_id' not in session:
        return redirect(url_for("login"))
    
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 候補者の基本情報を取得
        cur.execute("""
            SELECT 
                pd.user_id,
                pd.user_name,
                pd.email,
                up.job_title,
                up.location_prefecture,
                up.salary_min,
                upa.analysis_data
            FROM personal_date pd
            LEFT JOIN user_profile up ON pd.user_id = up.user_id
            LEFT JOIN user_personality_analysis upa ON pd.user_id = upa.user_id
            WHERE pd.user_id = %s
        """, (user_id,))
        
        candidate = cur.fetchone()
        
        if not candidate:
            cur.close()
            conn.close()
            return "候補者が見つかりません", 404
        
        # 分析データを展開
        analysis_data = candidate.get('analysis_data') or {}
        career_orientation = analysis_data.get('career_orientation')
        
        # マッチングスコアを計算（簡易版）
        match_score = 50
        if analysis_data.get('personality_traits'):
            match_score += len(analysis_data['personality_traits']) * 5
        if career_orientation:
            match_score += 10
        match_score = min(match_score, 99)
        
        # 検索履歴を取得
        cur.execute("""
            SELECT 
                search_keywords,
                job_id,
                searched_at,
                'search' as action_type
            FROM search_history
            WHERE user_id = %s
            ORDER BY searched_at DESC
            LIMIT 20
        """, (user_id,))
        
        search_history = cur.fetchall()
        
        # 検索キーワードの傾向を分析
        keyword_counts = {}
        for history in search_history:
            if history.get('search_keywords'):
                keywords = history['search_keywords'].split(',')
                for keyword in keywords:
                    keyword = keyword.strip()
                    if keyword:
                        keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # 上位5つのキーワード
        search_trends = [
            {'keyword': k, 'count': v} 
            for k, v in sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        # チャット履歴を取得
        cur.execute("""
            SELECT 
                user_message,
                ai_response,
                created_at
            FROM chat_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (user_id,))
        
        chat_history = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # テンプレートに渡すデータ
        candidate_data = {
            'user_id': candidate['user_id'],
            'user_name': candidate['user_name'],
            'email': candidate['email'],
            'job_title': candidate['job_title'],
            'location_prefecture': candidate['location_prefecture'],
            'salary_min': candidate['salary_min'],
            'match_score': match_score,
            'career_orientation': career_orientation,
            'analysis_data': analysis_data
        }
        
        return render_template(
            "candidate_detail.html",
            candidate=candidate_data,
            search_history=search_history,
            search_trends=search_trends,
            chat_history=chat_history
        )
        
    except Exception as e:
        print(f"Error in candidate_detail: {e}")
        import traceback
        traceback.print_exc()
        return f"エラーが発生しました: {str(e)}", 500

@company_app.route("/api/scout/chat", methods=["POST"])
def api_scout_chat():
    """AIチャットでスカウト条件を解釈"""
    if 'company_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.json
        user_message = data.get("message", "")
        context = data.get("context", [])
        
        # 会話履歴を構築
        messages = [
            {
                "role": "system",
                "content": """あなたは企業の採用担当者を支援するAIアシスタントです。
                
採用担当者から希望する人材の条件を聞き出し、以下の情報を抽出してください：

1. 職種・スキル（job_title）
2. 勤務地（location）
3. 性格特性（personality_traits）- 例: 協調性が高い、計画的、柔軟性がある
4. キャリア志向（career_orientation）- 例: 安定志向、挑戦志向、バランス志向
5. 希望年収範囲（salary_range）
6. その他の条件

会話を通じて自然に情報を聞き出してください。
十分な情報が集まったら、JSONフォーマットで条件をまとめてください。

会話例：
ユーザー: エンジニアを探しています
AI: どのようなエンジニアをお探しですか？フロントエンド、バックエンド、フルスタックなど具体的に教えてください。

ユーザー: フルスタックエンジニアで、チャレンジ精神のある人
AI: 素晴らしいですね！勤務地や年収の希望はありますか？

必ず親しみやすく、丁寧な口調で対応してください。"""
            }
        ]
        
        # コンテキストを追加
        for msg in context:
            messages.append(msg)
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # OpenAI API呼び出し
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        ai_response = response.choices[0].message.content
        
        # コンテキストを更新
        context.append({"role": "user", "content": user_message})
        context.append({"role": "assistant", "content": ai_response})
        
        # 条件が十分に集まったかチェック
        extraction_prompt = f"""以下の会話から、スカウト候補者の検索条件を抽出してください。

会話履歴:
{json.dumps(context, ensure_ascii=False)}

以下のJSON形式で出力してください（情報がない項目はnullにしてください）:
{{
    "job_title": "職種名",
    "location": "勤務地",
    "personality_traits": ["性格特性1", "性格特性2"],
    "career_orientation": "キャリア志向",
    "salary_min": 最低年収（数値）,
    "ready_to_search": true/false（検索可能な情報が揃っているか）
}}"""
        
        extraction_response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0.3,
            max_tokens=300
        )
        
        # JSON抽出
        try:
            extracted_text = extraction_response.choices[0].message.content
            # JSONブロックを抽出
            if "```json" in extracted_text:
                json_text = extracted_text.split("```json")[1].split("```")[0].strip()
            elif "```" in extracted_text:
                json_text = extracted_text.split("```")[1].split("```")[0].strip()
            else:
                json_text = extracted_text.strip()
            
            conditions = json.loads(json_text)
        except:
            conditions = {"ready_to_search": False}
        
        # 🔥 変更: 常に候補者を検索（ready_to_searchに関係なく）
        candidates = []
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 基本的な検索クエリ（全ユーザーを対象）
        query = """
            SELECT 
                pd.user_id,
                pd.user_name,
                up.job_title,
                up.location_prefecture,
                up.salary_min,
                upa.analysis_data
            FROM personal_date pd
            LEFT JOIN user_profile up ON pd.user_id = up.user_id
            LEFT JOIN user_personality_analysis upa ON pd.user_id = upa.user_id
            WHERE upa.analysis_data IS NOT NULL
        """
        
        params = []
        
        # 職種フィルター（条件があれば追加）
        if conditions.get("job_title"):
            query += " AND up.job_title ILIKE %s"
            params.append(f"%{conditions['job_title']}%")
        
        # 勤務地フィルター（条件があれば追加）
        if conditions.get("location"):
            query += " AND up.location_prefecture ILIKE %s"
            params.append(f"%{conditions['location']}%")
        
        # より多くの候補者を取得してスコアリング
        query += " LIMIT 50"
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        # 候補者をスコアリング
        for row in results:
            analysis = row['analysis_data'] if row['analysis_data'] else {}
            
            # マッチングスコア計算
            score = 40  # ベーススコア（少し低めに設定）
            match_reasons = []  # マッチ理由を記録
            
            # 職種マッチング（+15点）
            if conditions.get("job_title") and row.get("job_title"):
                if conditions["job_title"].lower() in row["job_title"].lower():
                    score += 15
                    match_reasons.append(f"職種が一致（{row['job_title']}）")
            
            # 勤務地マッチング（+10点）
            if conditions.get("location") and row.get("location_prefecture"):
                if conditions["location"].lower() in row["location_prefecture"].lower():
                    score += 10
                    match_reasons.append(f"勤務地が希望に合致（{row['location_prefecture']}）")
            
            # 性格特性マッチング（+10点 x マッチ数）
            if conditions.get("personality_traits"):
                user_traits = analysis.get("personality_traits", [])
                matching_traits = [t for t in conditions["personality_traits"] if any(t in ut for ut in user_traits)]
                if matching_traits:
                    score += len(matching_traits) * 10
                    match_reasons.append(f"性格特性が一致（{', '.join(matching_traits)}）")
            
            # キャリア志向マッチング（+20点）
            if conditions.get("career_orientation"):
                if analysis.get("career_orientation") == conditions["career_orientation"]:
                    score += 20
                    match_reasons.append(f"キャリア志向が一致（{conditions['career_orientation']}）")
            
            # 年収マッチング（+10点）
            if conditions.get("salary_min") and row.get("salary_min"):
                if row["salary_min"] >= conditions["salary_min"] * 0.8:
                    score += 10
                    match_reasons.append(f"希望年収範囲内（{row['salary_min']}万円）")
            
            # 条件が少ない場合のボーナス要因
            if not conditions.get("job_title") and not conditions.get("personality_traits"):
                # 一般的に良い特性にボーナス
                user_traits = analysis.get("personality_traits", [])
                positive_traits = ["協調性が高い", "責任感が強い", "コミュニケーション能力が高い", "積極的"]
                for trait in positive_traits:
                    if any(trait in ut for ut in user_traits):
                        score += 3
                        if not match_reasons:
                            match_reasons.append(f"優れた特性（{trait}）")
            
            score = min(score, 99)
            
            # マッチ理由がない場合のデフォルト
            if not match_reasons:
                match_reasons.append("幅広い適性があります")
            
            candidates.append({
                "user_id": row["user_id"],
                "user_name": row["user_name"],
                "job_title": row["job_title"],
                "location_prefecture": row["location_prefecture"],
                "match_score": score,
                "personality_traits": analysis.get("personality_traits", []),
                "career_orientation": analysis.get("career_orientation"),
                "summary": analysis.get("summary", ""),
                "match_reasons": match_reasons  # マッチ理由を追加
            })
        
        # スコアでソート
        candidates.sort(key=lambda x: x["match_score"], reverse=True)
        
        # 🔥 変更: 必ず上位2件を返す
        candidates = candidates[:2] if len(candidates) >= 2 else candidates
        
        cur.close()
        conn.close()
        
        return jsonify({
            "response": ai_response,
            "context": context,
            "candidates": candidates,
            "conditions": conditions
        })
        
    except Exception as e:
        print(f"Error in scout chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- ユーザー分析バッチ実行 ---
@company_app.route("/admin/analyze_all_users", methods=["POST"])
def admin_analyze_all_users():
    """全ユーザーの性格分析を実行（管理者用）"""
    if 'company_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM personal_date")
        user_ids = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        # バックグラウンドで実行
        import threading
        
        def analyze_users():
            for user_id in user_ids:
                try:
                    UserProfileAnalyzer.analyze_user_personality(user_id)
                    print(f"Analyzed user {user_id}")
                except Exception as e:
                    print(f"Failed to analyze user {user_id}: {e}")
        
        threading.Thread(target=analyze_users, daemon=True).start()
        
        return jsonify({
            "status": "success",
            "message": f"{len(user_ids)}人のユーザー分析を開始しました"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- メイン起動 ---
if __name__ == "__main__":
    company_app.run(debug=True, port=5001)