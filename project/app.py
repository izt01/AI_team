"""
AI求人マッチングシステム v2.0
- 動的質問生成（学習データ駆動）
- ハイブリッドレコメンデーション（協調フィルタリング + コンテンツベース）
- 多軸評価（企業文化、働き方、キャリアパス）
- ユーザー行動追跡（クリック、お気に入り、応募）
"""

from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import openai
import uuid
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# 新しいモジュールをインポート
from tracking import UserInteractionTracker, ChatHistoryManager, QuestionResponseManager
from multi_axis_evaluator import JobAttributeExtractor, UserPreferenceManager
from dynamic_questions import QuestionGenerator, QuestionSelector
from hybrid_recommender import HybridRecommender, MLModelScorer
from dynamic_question_generator_v2 import DynamicQuestionGenerator

app = Flask(__name__)
app.secret_key = "supersecretkey"

# OpenAI APIキーを環境変数から取得
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY が .env ファイルに設定されていません")

client = OpenAI(api_key=openai_api_key)

# 動的質問生成器の初期化
dynamic_question_gen = DynamicQuestionGenerator(client)

# --- DB接続 ---
def get_db_conn():
    return psycopg2.connect(
        host="localhost", port=5432, dbname="jobmatch",
        user="devuser", password="devpass"
    )


# --- セッションIDの生成 ---
def get_or_create_session_id():
    """チャットセッションIDを取得または生成"""
    if 'chat_session_id' not in session:
        session['chat_session_id'] = str(uuid.uuid4())
    return session['chat_session_id']


# --- トップページ ---
@app.route("/")
def index():
    return redirect(url_for("step1"))


# --- Step1: 個人情報登録 ---
@app.route("/step1", methods=["GET", "POST"])
def step1():
    if request.method == "POST":
        user_name = request.form["name"]
        email = request.form["email"]
        password_hash = generate_password_hash(request.form["password"])
        birth_day = request.form.get("birth_day")
        phone_number = request.form.get("phone_number")
        address = request.form.get("address")

        conn = get_db_conn()
        cur = conn.cursor()

        # ★★★ 最大user_id + 1を取得 ★★★
        cur.execute("SELECT COALESCE(MAX(user_id), 0) + 1 FROM personal_date")
        new_user_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO personal_date (user_id, email, password_hash, user_name, birth_day, phone_number, address, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (new_user_id, email, password_hash, user_name, birth_day, phone_number, address))

        cur.execute("""
            INSERT INTO user_profile (user_id, job_title, location_prefecture, salary_min, created_at, updated_at)
            VALUES (%s, '', '', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (new_user_id,))

        conn.commit()
        cur.close()
        conn.close()

        session["user_id"] = new_user_id
        return redirect(url_for("step2"))

    return render_template("form_step1.html")


# --- Step2: 希望条件入力 ---
@app.route("/step2", methods=["GET", "POST"])
def step2():
    if request.method == "POST":
        job_title = request.form.get("job_title")
        location_prefecture = request.form.get("location_prefecture")
        salary_min = request.form.get("salary_min")

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE user_profile
            SET job_title = %s,
                location_prefecture = %s,
                salary_min = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (job_title, location_prefecture, salary_min, session["user_id"]))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("chat_page"))

    return render_template("form_step2.html")


# --- ログイン ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form["identifier"]
        password = request.form["password"]

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id, email, password_hash FROM Personal_data WHERE email=%s OR user_name=%s",
                    (identifier, identifier))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            return redirect(url_for("chat_page"))
        else:
            return "ログイン失敗しました"

    return render_template("login.html")


# --- チャット画面 ---
@app.route("/chat")
def chat_page():
    """チャット画面"""
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user_id = session['user_id']
    session_id = get_or_create_session_id()

    # ★★★ 推薦を取得（1回だけ実行） ★★★
    # 上限なし：該当する全ての求人を取得
    recommendations = HybridRecommender.get_hybrid_recommendations(user_id, top_k=None, previous_job_ids=None)

    count = len(recommendations)
    print(f"Initial recommendations: {count} jobs")

    # ★★★ データベースに初回の結果を保存 ★★★
    initial_job_ids = [str(job['id']) for job in recommendations]
    save_filtered_job_ids_to_db(user_id, session_id, initial_job_ids)

    if count == 0:
        initial_message = "条件に合う求人が見つかりませんでした。条件を見直してください。"
    elif count <= 3:
        # ★★★ 3件以下なら最終段階（エンベディング + 類似ユーザー求人を含む） ★★★
        
        # ユーザーの会話履歴をエンベディング化
        update_user_conversation_embedding(user_id)
        
        # 絞り込んだ求人のIDを記録
        displayed_ids = [str(job['id']) for job in recommendations]
        
        # エンベディング検索で追加の2件を取得
        best_matches = find_best_matches_with_embeddings(
            user_id, 
            filtered_jobs=None,
            top_k=2,
            exclude_ids=displayed_ids
        )
        
        # 類似ユーザーの応募済み求人を1件取得
        similar_user_job = find_similar_user_applied_job(user_id)
        
        # 全求人を結合
        all_jobs = recommendations + best_matches
        if similar_user_job:
            all_jobs.append(similar_user_job)
        
        # GPT-4で説明文を生成
        explanation = generate_final_recommendation_with_gpt(user_id, all_jobs)
        
        # 絞り込んだ求人を整形
        filtered_details = []
        for i, job in enumerate(recommendations, 1):
            detail = (
                f"🎯 絞り込み候補{i}: {job['company_name']} / {job['job_title']}\n"
                f"📍 {job['location_prefecture']}\n"
                f"💰 年収: {job['salary_min']}万〜{job['salary_max']}万"
            )
            filtered_details.append(detail)
        
        # AI推薦を整形
        additional_details = []
        if best_matches and len(best_matches) > 0:
            for i, job in enumerate(best_matches, 1):
                detail = (
                    f"⭐ AIおすすめ{i}: {job['company_name']} / {job['job_title']}\n"
                    f"📍 {job['location_prefecture']}\n"
                    f"💰 年収: {job['salary_min']}万〜{job['salary_max']}万\n"
                    f"🎯 マッチ度: {job['similarity']:.1%}"
                )
                additional_details.append(detail)
        
        # 類似ユーザーの応募求人を整形
        similar_user_detail = None
        if similar_user_job:
            similar_text = generate_similar_user_recommendation_text(user_id, similar_user_job)
            similar_user_detail = (
                f"{similar_text}\n\n"
                f"💼 {similar_user_job['company_name']} / {similar_user_job['job_title']}\n"
                f"📍 {similar_user_job['location_prefecture']}\n"
                f"💰 年収: {similar_user_job['salary_min']}万〜{similar_user_job['salary_max']}万\n"
                f"👥 類似ユーザー {similar_user_job['apply_count']}人が応募"
            )
        
        # 最終メッセージを組み立て
        total_count = len(recommendations) + len(best_matches) + (1 if similar_user_job else 0)
        
        initial_message = f"{explanation}\n\n"
        initial_message += f"【絞り込んだ候補（{len(recommendations)}件）】\n\n"
        initial_message += "\n\n".join(filtered_details)
        
        if additional_details:
            initial_message += f"\n\n【AIが選んだ追加のおすすめ（{len(best_matches)}件）】\n\n"
            initial_message += "\n\n".join(additional_details)
        
        if similar_user_detail:
            initial_message += f"\n\n【類似ユーザーが応募した求人】\n\n"
            initial_message += similar_user_detail
        
        initial_message += f"\n\n✨ 合計 {total_count} 件の求人をご紹介しました。"
        
    else:
        # ★★★ 4件以上なら完全動的に質問を生成 ★★★
        next_question = dynamic_question_gen.generate_next_question(user_id, recommendations, "")
        
        if next_question:
            # セッションに質問情報を保存
            session['last_question_key'] = next_question['question_key']
            session['last_question_text'] = next_question['question_text']
            session['last_question_category'] = next_question.get('category', '働き方の柔軟性')
            
            initial_message = f"あなたにマッチする求人が {count} 件見つかりました。\n\n{next_question['question_text']}"
        else:
            initial_message = f"あなたにマッチする求人が {count} 件見つかりました。\n\n条件を追加してください。"

    # 初回メッセージをチャット履歴に保存
    ChatHistoryManager.save_message(user_id, 'bot', initial_message, session_id=session_id)

    return render_template('chat.html', initial_message=initial_message)

def generate_embedding(text: str) -> List[float]:
    """テキストをエンベディング化"""
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def find_best_matches_with_embeddings(user_id: int, filtered_jobs: List[Dict] = None, top_k: int = 2, exclude_ids: List[str] = None) -> List[Dict[str, Any]]:
    """
    エンベディング検索で最もマッチする求人を見つける
    
    Args:
        user_id: ユーザーID
        filtered_jobs: フィルタリング済みの求人リスト（Noneの場合は全求人から検索）
        top_k: 上位K件を返す（デフォルト2件）
        exclude_ids: 除外する求人IDのリスト
    
    Returns:
        マッチした求人のリスト
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # ユーザープロファイルを取得
        cur.execute("""
            SELECT job_title, location_prefecture, salary_min
            FROM user_profile
            WHERE user_id = %s
        """, (user_id,))
        
        profile = cur.fetchone()
        
        if not profile:
            cur.close()
            conn.close()
            return []
        
        # ユーザーの質問回答を取得
        cur.execute("""
            SELECT dq.question_text, uqr.response_text
            FROM user_question_responses uqr
            JOIN dynamic_questions dq ON uqr.question_id = dq.id
            WHERE uqr.user_id = %s
            ORDER BY uqr.created_at
        """, (user_id,))
        
        responses = cur.fetchall()
        
        # ユーザーの条件テキストを作成
        user_text = f"""
職種: {profile['job_title']}
勤務地: {profile['location_prefecture']}
希望年収: {profile['salary_min']}万円以上

【希望条件】
"""
        
        for resp in responses:
            user_text += f"- {resp['question_text']}: {resp['response_text']}\n"
        
        print(f"\n=== User Preference Text ===\n{user_text}\n")
        
        # ユーザーの条件をエンベディング化
        user_embedding = generate_embedding(user_text)
        
        if user_embedding is None:
            cur.close()
            conn.close()
            return []
        
        # ★★★ 全求人から検索（exclude_ids除外） ★★★
        exclude_clause = ""
        params = [f"%{profile['job_title']}%", f"%{profile['location_prefecture']}%", profile['salary_min']]
        
        if exclude_ids:
            exclude_clause = "AND cp.id::text != ALL(%s)"
            params.append(exclude_ids)
        
        cur.execute(f"""
            SELECT cp.id, cp.job_title, cp.location_prefecture,
                   cp.salary_min, cp.salary_max,
                   cd.company_name,
                   ja.company_culture, ja.work_flexibility, ja.career_path
            FROM company_profile cp
            JOIN company_date cd ON cp.company_id = cd.company_id
            LEFT JOIN job_attributes ja ON cp.id::text = ja.job_id::text
            WHERE cp.job_title ILIKE %s
              AND cp.location_prefecture ILIKE %s
              AND cp.salary_min >= %s
              {exclude_clause}
            LIMIT 100
        """, params)
        
        jobs = cur.fetchall()
        
        cur.close()
        conn.close()
        
        print(f"Found {len(jobs)} jobs for embedding comparison")
        
        if not jobs:
            return []
        
        # 各求人をテキスト化してエンベディング化
        job_similarities = []
        
        for job in jobs:
            # 求人テキストを作成
            job_text = f"""
職種: {job['job_title']}
企業: {job['company_name']}
勤務地: {job['location_prefecture']}
年収: {job['salary_min']}万〜{job['salary_max']}万円
"""
            
            if job.get('work_flexibility'):
                wf = job['work_flexibility']
                job_text += f"\n【働き方】\n"
                job_text += f"- リモートワーク: {'可能' if wf.get('remote') else '不可'}\n"
                job_text += f"- フレックスタイム: {'あり' if wf.get('flex_time') else 'なし'}\n"
                job_text += f"- 副業: {'可能' if wf.get('side_job') else '不可'}\n"
                job_text += f"- 残業: {wf.get('overtime', '不明')}\n"
            
            if job.get('company_culture'):
                cc = job['company_culture']
                job_text += f"\n【企業文化】\n"
                job_text += f"- 規模: {cc.get('size', '不明')}\n"
                job_text += f"- 雰囲気: {cc.get('atmosphere', '不明')}\n"
            
            if job.get('career_path'):
                cp_data = job['career_path']
                job_text += f"\n【キャリア】\n"
                job_text += f"- 成長機会: {'あり' if cp_data.get('growth_opportunities') else 'なし'}\n"
                job_text += f"- 研修: {'充実' if cp_data.get('training') else '少ない'}\n"
                job_text += f"- 昇進スピード: {cp_data.get('promotion_speed', '不明')}\n"
            
            # エンベディング化
            job_embedding = generate_embedding(job_text)
            
            if job_embedding is None:
                continue
            
            # コサイン類似度を計算
            similarity = cosine_similarity(
                [user_embedding],
                [job_embedding]
            )[0][0]
            
            job_similarities.append({
                'id': job['id'],
                'job_title': job['job_title'],
                'company_name': job['company_name'],
                'location_prefecture': job['location_prefecture'],
                'salary_min': job['salary_min'],
                'salary_max': job['salary_max'],
                'similarity': float(similarity)
            })
        
        # 類似度の高い順にソート
        job_similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        print(f"\n=== Top {top_k} Matches by Embedding ===")
        for i, job in enumerate(job_similarities[:top_k], 1):
            print(f"{i}. {job['job_title']} at {job['company_name']} - Similarity: {job['similarity']:.4f}")
        
        return job_similarities[:top_k]
        
    except Exception as e:
        print(f"Error finding best matches with embeddings: {e}")
        import traceback
        traceback.print_exc()
        return []


def generate_final_recommendation_with_gpt(user_id: int, matched_jobs: List[Dict]) -> str:
    """
    GPT-4で最終レコメンデーション文を生成
    
    Args:
        user_id: ユーザーID
        matched_jobs: マッチした求人リスト（絞り込み+AI推薦の全て）
    
    Returns:
        説明文
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # ユーザーの回答履歴を取得
        cur.execute("""
            SELECT dq.question_text, uqr.response_text
            FROM user_question_responses uqr
            JOIN dynamic_questions dq ON uqr.question_id = dq.id
            WHERE uqr.user_id = %s
            ORDER BY uqr.created_at
        """, (user_id,))
        
        responses = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # ユーザーの条件を整理
        conditions_text = "\n".join([
            f"- {resp['question_text']}: {resp['response_text']}"
            for resp in responses
        ])
        
        # 求人情報を整理
        jobs_text = ""
        for i, job in enumerate(matched_jobs, 1):
            jobs_text += f"\n{i}. {job['company_name']} / {job['job_title']}\n"
            jobs_text += f"   年収: {job['salary_min']}万〜{job['salary_max']}万\n"
            if 'similarity' in job:
                jobs_text += f"   マッチ度: {job['similarity']:.1%}\n"
        
        prompt = f"""
あなたは求人マッチングAIアシスタントです。ユーザーの希望条件に基づいて、最もマッチする求人を厳選しました。

【ユーザーの希望条件】
{conditions_text}

【厳選した求人】
{jobs_text}

【あなたのタスク】
上記の求人がなぜユーザーにマッチするのか、温かみのある文章で説明してください。

以下の要素を含めてください：
1. 導入文（「あなたの希望に最もマッチする求人を厳選しました」など）
2. 求人の魅力ポイント（ユーザーの条件との一致点）
3. 前向きな締めくくり

自然で親しみやすいトーンで、3〜5文程度で書いてください。
"""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=300
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating final recommendation: {e}")
        return "あなたの希望条件に最もマッチする求人を厳選しました。"
    
def save_filtered_job_ids_to_db(user_id: int, session_id: str, job_ids: List[str]):
    """フィルタリング結果をデータベースに保存"""
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        
        # 既存のデータを削除
        cur.execute("""
            DELETE FROM user_filtered_jobs
            WHERE user_id = %s AND session_id = %s
        """, (user_id, session_id))
        
        # 新しいデータを挿入（バッチ）
        if job_ids:
            values = [(user_id, session_id, job_id) for job_id in job_ids]
            cur.executemany("""
                INSERT INTO user_filtered_jobs (user_id, session_id, job_id)
                VALUES (%s, %s, %s)
            """, values)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✓ Saved {len(job_ids)} job IDs to database")
        
    except Exception as e:
        print(f"Error saving filtered job IDs: {e}")


def get_filtered_job_ids_from_db(user_id: int, session_id: str) -> List[str]:
    """データベースからフィルタリング結果を取得"""
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT job_id FROM user_filtered_jobs
            WHERE user_id = %s AND session_id = %s
            ORDER BY created_at
        """, (user_id, session_id))
        
        job_ids = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return job_ids
        
    except Exception as e:
        print(f"Error getting filtered job IDs: {e}")
        return []
    
def is_valid_answer_for_question(question_id: int, user_message: str) -> bool:
    """
    ユーザーの回答が質問に対して妥当かどうかを判定
    
    Args:
        question_id: 質問ID
        user_message: ユーザーのメッセージ
    
    Returns:
        妥当ならTrue、不適切ならFalse
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 質問を取得
        cur.execute("""
            SELECT question_key, question_text
            FROM dynamic_questions
            WHERE id = %s
        """, (question_id,))
        
        question = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not question:
            return True  # 質問が見つからない場合は通過
        
        # GPT-4で判定
        prompt = f"""
あなたは求人マッチングAIアシスタントです。以下の質問に対するユーザーの回答が、質問に答えているかどうかを判定してください。

【質問】
{question['question_text']}

【ユーザーの回答】
{user_message}

【判定基準】
- 質問に対して直接答えている場合: valid
- 質問とは関係ない話題（「他にオススメありますか？」「求人を見せて」など）: invalid
- 曖昧だが質問に関連している場合: valid

【出力形式】
以下のJSON形式で返してください：
{{
  "is_valid": true または false,
  "reason": "判定理由（簡潔に）"
}}
"""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # JSONを抽出
        import re
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(0)
        
        result = json.loads(result_text)
        
        is_valid = result.get('is_valid', True)
        reason = result.get('reason', '')
        
        print(f">>> Answer validation: {is_valid} - {reason}")
        
        return is_valid
        
    except Exception as e:
        print(f"Error validating answer: {e}")
        import traceback
        traceback.print_exc()
        return True  # エラー時は通過させる
    
def save_user_response_with_normalization(user_id: int, question_id: int, response_text: str) -> bool:
    """
    ユーザーの回答を正規化して保存
    
    Args:
        user_id: ユーザーID
        question_id: 質問ID
        response_text: 回答テキスト
    
    Returns:
        成功したかどうか
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 質問のキーを取得
        cur.execute("""
            SELECT question_key
            FROM dynamic_questions
            WHERE id = %s
        """, (question_id,))
        
        question = cur.fetchone()
        
        if not question:
            print(f"⚠ Question {question_id} not found")
            cur.close()
            conn.close()
            return False
        
        question_key = question['question_key']
        
        # GPT-4で正規化（意図抽出）
        normalized = normalize_response_with_gpt(question_key, response_text)
        
        # データベースに保存
        cur.execute("""
            INSERT INTO user_question_responses (user_id, question_id, response_text, normalized_response)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, question_id) 
            DO UPDATE SET 
                response_text = EXCLUDED.response_text,
                normalized_response = EXCLUDED.normalized_response,
                created_at = NOW()
        """, (user_id, question_id, response_text, normalized))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error saving user response: {e}")
        import traceback
        traceback.print_exc()
        return False


def normalize_response_with_gpt(question_key: str, response_text: str) -> str:
    """
    GPT-4で回答を正規化
    
    Args:
        question_key: 質問キー（remote, flex_time, など）
        response_text: ユーザーの回答テキスト
    
    Returns:
        正規化された回答
    """
    try:
        # 簡単なキーワードマッチで正規化
        text_lower = response_text.lower().strip()
        
        # ポジティブキーワード
        positive_keywords = [
            'はい', 'yes', 'する', '希望', 'いい', '良い', 'できる', 
            '可能', 'したい', 'ある', 'あり', '魅力的', '大切', '優先',
            '少なめ', '少ない', 'リモート', 'フレックス', '大企業', '大手',
            '活気', 'チャレンジ', '成長', '研修', '昇進', '多い', '興味'
        ]
        
        # ネガティブキーワード
        negative_keywords = [
            'いいえ', 'no', 'しない', '希望しない', '不要', 'なくても',
            '大丈夫', '考えない', '重視しない', 'できなくても', '特に', 
            'ない', 'ないです', '興味ない', '興味はない'
        ]
        
        is_positive = any(kw in text_lower for kw in positive_keywords)
        is_negative = any(kw in text_lower for kw in negative_keywords)
        
        # テキスト解釈が必要な項目
        text_keys = ['company_type', 'overtime', 'atmosphere', 'promotion']
        
        if question_key in text_keys:
            # テキストのまま返す
            return response_text
        else:
            # 真偽値として正規化
            if is_positive and not is_negative:
                return 'はい'
            elif is_negative:
                return 'いいえ'
            else:
                # どちらでもない場合はそのまま
                return response_text
        
    except Exception as e:
        print(f"Error normalizing response: {e}")
        return response_text

@app.route("/api/chat", methods=["POST"])
def chat_api():
    """チャットAPI - 自然な会話形式で質問生成（累積絞り込み版 + 回答検証付き）"""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    user_msg = request.json["message"]
    session_id = get_or_create_session_id()

    # チャット履歴を保存
    ChatHistoryManager.save_message(user_id, 'user', user_msg, session_id=session_id)

    # ★★★ 最後の質問に対する回答かチェック ★★★
    if 'last_question_key' in session:
        question_key = session['last_question_key']
        question_text = session.get('last_question_text', '')
        question_category = session.get('last_question_category', '働き方の柔軟性')
        
        print(f">>> Saving response for question_key: {question_key}")
        
        # ★★★ 動的質問の回答を保存 ★★★
        normalized = normalize_response_with_gpt(question_key, user_msg)
        success = dynamic_question_gen.save_question_and_response(
            user_id=user_id,
            question_key=question_key,
            question_text=question_text,
            category=question_category,
            response_text=user_msg,
            normalized_response=normalized
        )
        
        if success:
            print(f"✓ Dynamic question response saved successfully")
        else:
            print(f"⚠ Failed to save dynamic question response")
        
        # セッションから削除
        session.pop('last_question_key', None)
        session.pop('last_question_text', None)
        session.pop('last_question_category', None)
    else:
        print(f"⚠ No last_question_key in session")

    # ★★★ データベースから前回の結果IDリストを取得 ★★★
    previous_job_ids = get_filtered_job_ids_from_db(user_id, session_id)
    
    if previous_job_ids:
        print(f">>> Using previous results from DB: {len(previous_job_ids)} jobs")
    else:
        print(f">>> No previous results, searching from scratch")

    # 推薦を取得（上限なし）
    recommendations = HybridRecommender.get_hybrid_recommendations(
        user_id, 
        top_k=None,
        previous_job_ids=previous_job_ids
    )

    count = len(recommendations)
    print(f"\n>>> After filtering: {count} jobs remaining\n")

    # 今回の結果IDリストをデータベースに保存
    current_job_ids = [str(job['id']) for job in recommendations]
    save_filtered_job_ids_to_db(user_id, session_id, current_job_ids)

    if count == 0:
        reply_text = "該当する求人は 0 件です。条件を見直してください。"
        ChatHistoryManager.save_message(user_id, 'bot', reply_text, session_id=session_id)
        return jsonify({"reply": reply_text})

    # ★★★ 3件以下なら最終段階：絞り込んだ求人 + エンベディング検索 + 類似ユーザー応募求人 ★★★
    if count <= 3:
        print("\n=== Final Stage: Showing Filtered Jobs + Embedding Recommendations + Similar User Jobs ===")
        
        # ★★★ ユーザーの会話履歴をエンベディング化（保存） ★★★
        update_user_conversation_embedding(user_id)
        
        # 絞り込んだ求人のIDを記録
        displayed_ids = [str(job['id']) for job in recommendations]
        
        # エンベディング検索で追加の2件を取得（既に表示した求人を除外）
        best_matches = find_best_matches_with_embeddings(
            user_id, 
            filtered_jobs=None,  # 全求人から検索
            top_k=2,
            exclude_ids=displayed_ids  # 既に表示した求人を除外
        )
        
        # ★★★ 類似ユーザーの応募済み求人を1件取得 ★★★
        similar_user_job = find_similar_user_applied_job(user_id)
        
        # 絞り込んだ求人 + AI推薦 + 類似ユーザー求人を結合
        all_jobs = recommendations + best_matches
        if similar_user_job:
            all_jobs.append(similar_user_job)
        
        # GPT-4で説明文を生成
        explanation = generate_final_recommendation_with_gpt(user_id, all_jobs)
        
        # 絞り込んだ求人を整形
        filtered_job_texts = []
        for i, job in enumerate(recommendations, 1):
            detail = (
                f"🎯 絞り込み候補{i}: {job['company_name']} / {job['job_title']}\n"
                f"📍 {job['location_prefecture']}\n"
                f"💰 年収: {job['salary_min']}万〜{job['salary_max']}万"
            )
            filtered_job_texts.append(detail)
        
        # AI推薦を整形
        additional_job_texts = []
        if best_matches and len(best_matches) > 0:
            for i, job in enumerate(best_matches, 1):
                detail = (
                    f"⭐ AIおすすめ{i}: {job['company_name']} / {job['job_title']}\n"
                    f"📍 {job['location_prefecture']}\n"
                    f"💰 年収: {job['salary_min']}万〜{job['salary_max']}万\n"
                    f"🎯 マッチ度: {job['similarity']:.1%}"
                )
                additional_job_texts.append(detail)
        
        # ★★★ 類似ユーザーの応募求人を整形 ★★★
        similar_user_job_text = None
        if similar_user_job:
            similar_text = generate_similar_user_recommendation_text(user_id, similar_user_job)
            similar_user_job_text = (
                f"{similar_text}\n\n"
                f"💼 {similar_user_job['company_name']} / {similar_user_job['job_title']}\n"
                f"📍 {similar_user_job['location_prefecture']}\n"
                f"💰 年収: {similar_user_job['salary_min']}万〜{similar_user_job['salary_max']}万\n"
                f"👥 類似ユーザー {similar_user_job['apply_count']}人が応募"
            )
        
        # 最終的な表示
        total_count = len(recommendations) + len(best_matches) + (1 if similar_user_job else 0)
        
        reply_text = f"{explanation}\n\n"
        reply_text += f"【絞り込んだ候補（{len(recommendations)}件）】\n\n"
        reply_text += "\n\n".join(filtered_job_texts)
        
        if additional_job_texts:
            reply_text += f"\n\n【AIが選んだ追加のおすすめ（{len(best_matches)}件）】\n\n"
            reply_text += "\n\n".join(additional_job_texts)
        
        if similar_user_job_text:
            reply_text += f"\n\n【類似ユーザーが応募した求人】\n\n"
            reply_text += similar_user_job_text
        
        reply_text += f"\n\n✨ 合計 {total_count} 件の求人をご紹介しました。"
        
        ChatHistoryManager.save_message(user_id, 'bot', reply_text, session_id=session_id)
        return jsonify({"reply": reply_text})

    # ★★★ 4件以上なら完全動的に質問を生成（求人リストは表示しない） ★★★
    next_question = dynamic_question_gen.generate_next_question(user_id, recommendations, user_msg)

    if next_question:
        # セッションに質問情報を保存
        session['last_question_key'] = next_question['question_key']
        session['last_question_text'] = next_question['question_text']
        session['last_question_category'] = next_question.get('category', '働き方の柔軟性')
        print(f">>> Stored question_key in session: {next_question['question_key']}")
        
        # ★★★ 求人リストは表示せず、件数と質問のみ ★★★
        reply_text = f"該当求人数は {count} 件です。\n\n{next_question['question_text']}"
    else:
        # ★★★ 質問がない場合もエンベディング検索 + 類似ユーザー求人を含めて表示 ★★★
        print("\n=== No more questions, switching to Embedding Search ===")
        
        # ユーザーの会話履歴をエンベディング化
        update_user_conversation_embedding(user_id)
        
        # 絞り込んだ求人（最大3件）
        displayed_ids = [str(job['id']) for job in recommendations[:3]]
        
        # エンベディング検索で追加の2件を取得
        best_matches = find_best_matches_with_embeddings(
            user_id, 
            filtered_jobs=None,
            top_k=2,
            exclude_ids=displayed_ids
        )
        
        # 類似ユーザーの応募済み求人を1件取得
        similar_user_job = find_similar_user_applied_job(user_id)
        
        # 結合
        all_jobs = recommendations[:3] + best_matches
        if similar_user_job:
            all_jobs.append(similar_user_job)
        
        # GPT-4で説明文を生成
        explanation = generate_final_recommendation_with_gpt(user_id, all_jobs)
        
        # 整形
        filtered_job_texts = []
        for i, job in enumerate(recommendations[:3], 1):
            detail = (
                f"🎯 絞り込み候補{i}: {job['company_name']} / {job['job_title']}\n"
                f"📍 {job['location_prefecture']}\n"
                f"💰 年収: {job['salary_min']}万〜{job['salary_max']}万"
            )
            filtered_job_texts.append(detail)
        
        additional_job_texts = []
        if best_matches and len(best_matches) > 0:
            for i, job in enumerate(best_matches, 1):
                detail = (
                    f"⭐ AIおすすめ{i}: {job['company_name']} / {job['job_title']}\n"
                    f"📍 {job['location_prefecture']}\n"
                    f"💰 年収: {job['salary_min']}万〜{job['salary_max']}万\n"
                    f"🎯 マッチ度: {job['similarity']:.1%}"
                )
                additional_job_texts.append(detail)
        
        similar_user_job_text = None
        if similar_user_job:
            similar_text = generate_similar_user_recommendation_text(user_id, similar_user_job)
            similar_user_job_text = (
                f"{similar_text}\n\n"
                f"💼 {similar_user_job['company_name']} / {similar_user_job['job_title']}\n"
                f"📍 {similar_user_job['location_prefecture']}\n"
                f"💰 年収: {similar_user_job['salary_min']}万〜{similar_user_job['salary_max']}万\n"
                f"👥 類似ユーザー {similar_user_job['apply_count']}人が応募"
            )
        
        total_count = min(len(recommendations), 3) + len(best_matches) + (1 if similar_user_job else 0)
        
        reply_text = f"{explanation}\n\n"
        reply_text += f"【絞り込んだ候補（{min(len(recommendations), 3)}件）】\n\n"
        reply_text += "\n\n".join(filtered_job_texts)
        
        if additional_job_texts:
            reply_text += f"\n\n【AIが選んだ追加のおすすめ（{len(best_matches)}件）】\n\n"
            reply_text += "\n\n".join(additional_job_texts)
        
        if similar_user_job_text:
            reply_text += f"\n\n【類似ユーザーが応募した求人】\n\n"
            reply_text += similar_user_job_text
        
        reply_text += f"\n\n✨ 合計 {total_count} 件の求人をご紹介しました。"

    ChatHistoryManager.save_message(user_id, 'bot', reply_text, session_id=session_id)
    return jsonify({"reply": reply_text})


def generate_final_recommendation_with_gpt(user_id: int, matched_jobs: List[Dict]) -> str:
    """
    GPT-4で最終レコメンデーション文を生成
    
    Args:
        user_id: ユーザーID
        matched_jobs: マッチした求人リスト（絞り込み+AI推薦の全て）
    
    Returns:
        説明文
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # ユーザーの回答履歴を取得
        cur.execute("""
            SELECT dq.question_text, uqr.response_text
            FROM user_question_responses uqr
            JOIN dynamic_questions dq ON uqr.question_id = dq.id
            WHERE uqr.user_id = %s
            ORDER BY uqr.created_at
        """, (user_id,))
        
        responses = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # ユーザーの条件を整理
        conditions_text = "\n".join([
            f"- {resp['question_text']}: {resp['response_text']}"
            for resp in responses
        ])
        
        # 求人情報を整理
        jobs_text = ""
        for i, job in enumerate(matched_jobs, 1):
            jobs_text += f"\n{i}. {job['company_name']} / {job['job_title']}\n"
            jobs_text += f"   年収: {job['salary_min']}万〜{job['salary_max']}万\n"
            if 'similarity' in job:
                jobs_text += f"   マッチ度: {job['similarity']:.1%}\n"
        
        prompt = f"""
あなたは求人マッチングAIアシスタントです。ユーザーの希望条件に基づいて、最もマッチする求人を厳選しました。

【ユーザーの希望条件】
{conditions_text}

【厳選した求人】
{jobs_text}

【あなたのタスク】
上記の求人がなぜユーザーにマッチするのか、温かみのある文章で説明してください。

以下の要素を含めてください：
1. 導入文（「あなたの希望に最もマッチする求人を厳選しました」など）
2. 求人の魅力ポイント（ユーザーの条件との一致点）
3. 前向きな締めくくり（必ず完結させること）

自然で親しみやすいトーンで、3〜4文程度で書いてください。
**重要**: 文章を途中で終わらせず、必ず完結させてください。
"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )

        explanation = response.choices[0].message.content.strip()
        return explanation

    except Exception as e:
        print(f"Error generating explanation: {e}")
        import traceback
        traceback.print_exc()
        return f"あなたの希望条件に合った求人を {len(top_jobs)} 件見つけました！"
    
def find_similar_users_conversation_history(user_id: int, limit: int = 5) -> List[Dict]:
    """
    類似条件を持つ過去ユーザーの会話履歴を取得
    
    Args:
        user_id: 現在のユーザーID
        limit: 取得する類似ユーザー数
    
    Returns:
        類似ユーザーの会話履歴リスト
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 現在のユーザーのプロファイルを取得
        cur.execute("""
            SELECT job_title, location_prefecture
            FROM user_profile
            WHERE user_id = %s
        """, (user_id,))
        
        current_profile = cur.fetchone()
        
        if not current_profile:
            cur.close()
            conn.close()
            return []
        
        # ★★★ SQL修正：SELECT DISTINCTとORDER BYの問題を解決 ★★★
        cur.execute("""
            WITH successful_users AS (
                SELECT 
                    up.user_id,
                    COUNT(DISTINCT ui.job_id) as interaction_count
                FROM user_profile up
                JOIN user_interactions ui ON up.user_id = ui.user_id
                WHERE up.job_title ILIKE %s
                  AND up.location_prefecture ILIKE %s
                  AND up.user_id != %s
                  AND ui.interaction_type IN ('apply', 'favorite', 'click')
                GROUP BY up.user_id
                HAVING COUNT(DISTINCT ui.job_id) >= 1
                ORDER BY interaction_count DESC
                LIMIT %s
            )
            SELECT 
                su.user_id,
                up.job_title,
                up.location_prefecture,
                COUNT(DISTINCT uqr.id) as total_responses
            FROM successful_users su
            JOIN user_profile up ON su.user_id = up.user_id
            LEFT JOIN user_question_responses uqr ON su.user_id = uqr.user_id
            GROUP BY su.user_id, up.job_title, up.location_prefecture
            ORDER BY total_responses DESC
        """, (
            f"%{current_profile['job_title']}%",
            f"%{current_profile['location_prefecture']}%",
            user_id,
            limit
        ))
        
        similar_users = cur.fetchall()
        
        if not similar_users:
            print("⚠ No similar users found")
            cur.close()
            conn.close()
            return []
        
        print(f"✓ Found {len(similar_users)} similar users")
        
        # 各ユーザーの会話履歴を取得
        conversation_histories = []
        
        for user in similar_users:
            similar_user_id = user['user_id']
            
            # 質問と回答を取得
            cur.execute("""
                SELECT 
                    dq.question_key,
                    dq.question_text,
                    uqr.response_text,
                    uqr.normalized_response,
                    uqr.created_at
                FROM user_question_responses uqr
                JOIN dynamic_questions dq ON uqr.question_id = dq.id
                WHERE uqr.user_id = %s
                ORDER BY uqr.created_at
            """, (similar_user_id,))
            
            responses = cur.fetchall()
            
            # このユーザーが最終的に見た求人を取得
            cur.execute("""
                SELECT COUNT(DISTINCT job_id) as viewed_jobs
                FROM user_interactions
                WHERE user_id = %s
                  AND interaction_type IN ('apply', 'favorite', 'click')
            """, (similar_user_id,))
            
            interaction_count = cur.fetchone()['viewed_jobs']
            
            conversation_histories.append({
                'user_id': similar_user_id,
                'job_title': user['job_title'],
                'location': user['location_prefecture'],
                'responses': [dict(r) for r in responses],
                'total_interactions': interaction_count
            })
        
        cur.close()
        conn.close()
        
        return conversation_histories
        
    except Exception as e:
        print(f"Error finding similar users: {e}")
        import traceback
        traceback.print_exc()
        return []


def analyze_successful_question_patterns(conversation_histories: List[Dict]) -> str:
    """
    成功ユーザーの質問パターンを分析してテキスト化
    
    Args:
        conversation_histories: 類似ユーザーの会話履歴
    
    Returns:
        分析結果のテキスト
    """
    if not conversation_histories:
        return "参考データなし"
    
    # 質問キーの出現頻度を集計
    question_freq = {}
    question_examples = {}
    
    for history in conversation_histories:
        for response in history['responses']:
            q_key = response['question_key']
            q_text = response['question_text']
            r_text = response['response_text']
            
            if q_key not in question_freq:
                question_freq[q_key] = 0
                question_examples[q_key] = []
            
            question_freq[q_key] += 1
            question_examples[q_key].append({
                'question': q_text,
                'answer': r_text
            })
    
    # 頻度の高い質問順にソート
    sorted_questions = sorted(question_freq.items(), key=lambda x: x[1], reverse=True)
    
    # テキスト化
    analysis_text = "【類似ユーザーが答えた質問トップ5】\n"
    
    for i, (q_key, freq) in enumerate(sorted_questions[:5], 1):
        examples = question_examples[q_key][:2]  # 最大2例
        analysis_text += f"\n{i}. {q_key} (回答率: {freq}/{len(conversation_histories)}人)\n"
        
        for example in examples:
            analysis_text += f"   Q: {example['question']}\n"
            analysis_text += f"   A: {example['answer']}\n"
    
    return analysis_text
    
def generate_conversational_question(user_id: int, recommendations: List[Dict], user_last_message: str) -> Optional[Dict[str, Any]]:
    """GPT-4で自然な会話形式の質問を生成（類似ユーザー参照版）"""
    try:
        # ユーザーの回答履歴を取得
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 既に回答済みの質問と回答内容を取得
        cur.execute("""
            SELECT dq.question_key, dq.question_text, uqr.response_text
            FROM user_question_responses uqr
            JOIN dynamic_questions dq ON uqr.question_id = dq.id
            WHERE uqr.user_id = %s
            ORDER BY uqr.created_at
        """, (user_id,))
        
        answered_questions = cur.fetchall()
        answered_keys = set([row['question_key'] for row in answered_questions])
        print(f"Already answered: {answered_keys}")

        # 未回答の質問のみ取得
        if answered_keys:
            placeholders = ','.join(['%s'] * len(answered_keys))
            cur.execute(f"""
                SELECT id, question_key, question_text, category 
                FROM dynamic_questions
                WHERE question_key NOT IN ({placeholders})
                ORDER BY id
                LIMIT 20
            """, tuple(answered_keys))
        else:
            cur.execute("""
                SELECT id, question_key, question_text, category 
                FROM dynamic_questions
                ORDER BY id
                LIMIT 20
            """)

        available_questions = cur.fetchall()
        
        if not available_questions:
            print("⚠ No more questions available")
            cur.close()
            conn.close()
            return None

        print(f"Available questions: {len(available_questions)}")
        
        # 求人の差分を分析
        cur.execute("""
            SELECT ja.company_culture, ja.work_flexibility, ja.career_path
            FROM job_attributes ja
            WHERE ja.job_id::text IN %s
            LIMIT 20
        """, (tuple([str(job['id']) for job in recommendations[:20]]),))
        
        job_attributes = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # ★★★ 類似ユーザーの会話履歴を取得 ★★★
        print("\n=== Fetching Similar Users' Conversation History ===")
        similar_users_history = find_similar_users_conversation_history(user_id, limit=5)
        
        # 成功パターンを分析
        success_patterns = analyze_successful_question_patterns(similar_users_history)
        print(f"\n{success_patterns}")
        
        # 回答済みの質問をテキスト化
        answered_text = "\n".join([
            f"- {q['question_text']}: {q['response_text']}"
            for q in answered_questions
        ]) if answered_questions else "まだ質問に答えていません"
        
        # 求人の特徴を分析
        remote_count = sum(1 for attr in job_attributes if attr.get('work_flexibility', {}).get('remote') == True)
        flex_count = sum(1 for attr in job_attributes if attr.get('work_flexibility', {}).get('flex_time') == True)
        large_company_count = sum(1 for attr in job_attributes if attr.get('company_culture', {}).get('size') == 'large')
        training_count = sum(1 for attr in job_attributes if attr.get('career_path', {}).get('training') == True)
        
        # ★★★ 類似ユーザーの情報を含めたプロンプト ★★★
        prompt = f"""
あなたは求人マッチングAIアシスタントです。ユーザーと自然な会話をしながら、最適な求人を絞り込んでいます。

【現在の状況】
- 該当求人数: {len(recommendations)}件
- ユーザーの最後のメッセージ: "{user_last_message}"

【ユーザーが既に回答した質問】
{answered_text}

【求人の特徴分析】
- リモートワーク可能: {remote_count}/{len(job_attributes)}件
- フレックスタイム制: {flex_count}/{len(job_attributes)}件
- 大企業: {large_company_count}/{len(job_attributes)}件
- 研修制度充実: {training_count}/{len(job_attributes)}件

【★参考★ 同じ条件で求人を探した過去ユーザーの傾向】
{success_patterns}

上記の過去ユーザーは、これらの質問に答えることで、最終的に希望の求人を見つけることができました。
この情報を参考に、現在のユーザーにも効果的な質問を選んでください。

【あなたのタスク】
以下のルールに従って、次に聞くべき質問を1つ生成してください：

1. **既に聞いた質問は絶対に聞かない**
2. **過去の成功ユーザーが答えた質問を優先的に参考にする**
3. **自然な会話形式で質問する**（「〜についてはどうですか？」「〜は気になりますか？」など）
4. **求人の差分がある項目について聞く**（例: リモートワークありなしが混在している場合）
5. **ユーザーの最後のメッセージを踏まえて、自然な流れで質問する**
6. **一問一答ではなく、会話的に**

【利用可能な質問キー】
以下から選んでください：
- remote: リモートワーク
- flex_time: フレックスタイム制度
- side_job: 副業
- overtime: 残業時間
- company_type: 企業規模
- atmosphere: 職場の雰囲気
- growth: キャリア成長機会
- training: 研修制度
- promotion: 昇進スピード

【出力形式】
以下のJSON形式で返してください。もし適切な質問がない、または全ての重要な質問を聞き終えた場合は、question_key を null にしてください。

{{
  "question_key": "remote" または null,
  "question_text": "自然な質問文"
}}

質問文のみ返してください（説明不要）。
"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )

        result_text = response.choices[0].message.content.strip()
        
        # JSONを抽出
        import re
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(0)
        
        result = json.loads(result_text)
        
        # question_keyがnullなら質問終了
        if not result.get('question_key'):
            return None
        
        # 既に回答済みのキーなら別の質問を選ぶ
        if result.get('question_key') in answered_keys:
            print(f"⚠ Question key '{result.get('question_key')}' already answered, skipping")
            return None
        
        # 対応する質問IDを取得
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id FROM dynamic_questions
            WHERE question_key = %s
        """, (result['question_key'],))
        
        question_row = cur.fetchone()
        cur.close()
        conn.close()
        
        if question_row:
            return {
                'question_id': question_row['id'],
                'question_text': result['question_text']
            }
        else:
            print(f"⚠ Question key '{result.get('question_key')}' not found in database")
            return {
                'question_text': result['question_text']
            }

    except Exception as e:
        print(f"Error generating conversational question: {e}")
        import traceback
        traceback.print_exc()
        return None

# --- お気に入りAPI ---
@app.route("/api/favorite", methods=["POST"])
def add_favorite():
    """求人をお気に入りに追加"""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    job_id = request.json["job_id"]

    success = UserInteractionTracker.add_favorite(user_id, job_id)

    if success:
        return jsonify({"status": "success", "message": "お気に入りに追加しました"})
    else:
        return jsonify({"status": "error", "message": "エラーが発生しました"}), 500


@app.route("/api/favorite", methods=["DELETE"])
def remove_favorite():
    """お気に入りから削除"""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    job_id = request.json["job_id"]

    success = UserInteractionTracker.remove_favorite(user_id, job_id)

    if success:
        return jsonify({"status": "success", "message": "お気に入りから削除しました"})
    else:
        return jsonify({"status": "error", "message": "エラーが発生しました"}), 500


@app.route("/api/favorites", methods=["GET"])
def get_favorites():
    """お気に入り一覧を取得"""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    favorites = UserInteractionTracker.get_user_favorites(user_id)

    return jsonify({"favorites": favorites})


# --- 応募API ---
@app.route("/api/apply", methods=["POST"])
def apply():
    """求人に応募"""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    job_id = request.json["job_id"]

    success = UserInteractionTracker.record_apply(user_id, job_id)

    if success:
        # 応募が成功したら、最後に回答した質問を効果的とマーク
        if 'last_question_id' in session:
            QuestionResponseManager.mark_question_as_effective(session['last_question_id'])

        return jsonify({"status": "success", "message": "応募を記録しました"})
    else:
        return jsonify({"status": "error", "message": "エラーが発生しました"}), 500


# --- プロフィール表示 ---
@app.route("/profile")
def profile():
    """ユーザープロフィール表示"""
    if 'user_id' not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT pd.user_name, pd.email, pd.birth_day, pd.phone_number, pd.address,
               up.job_title, up.location_prefecture, up.salary_min
        FROM personal_date pd
        INNER JOIN user_profile up ON pd.user_id = up.user_id
        WHERE pd.user_id = %s
    """, (user_id,))

    user_data = cur.fetchone()
    cur.close()
    conn.close()

    return render_template("profile.html", user=dict(user_data) if user_data else {})

def update_user_conversation_embedding(user_id: int):
    """
    ユーザーの会話履歴をエンベディング化してDBに保存
    
    Args:
        user_id: ユーザーID
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # ユーザープロファイルを取得
        cur.execute("""
            SELECT job_title, location_prefecture, salary_min
            FROM user_profile
            WHERE user_id = %s
        """, (user_id,))
        
        profile = cur.fetchone()
        
        if not profile:
            cur.close()
            conn.close()
            return
        
        # ユーザーの質問回答を取得
        cur.execute("""
            SELECT dq.question_text, uqr.response_text
            FROM user_question_responses uqr
            JOIN dynamic_questions dq ON uqr.question_id = dq.id
            WHERE uqr.user_id = %s
            ORDER BY uqr.created_at
        """, (user_id,))
        
        responses = cur.fetchall()
        
        # 会話履歴をテキスト化
        conversation_text = f"""
職種: {profile['job_title']}
勤務地: {profile['location_prefecture']}
希望年収: {profile['salary_min']}万円以上

【希望条件】
"""
        
        for resp in responses:
            conversation_text += f"- {resp['question_text']}: {resp['response_text']}\n"
        
        # エンベディング化
        embedding = generate_embedding(conversation_text)
        
        if embedding is None:
            print("⚠ Failed to generate embedding")
            cur.close()
            conn.close()
            return
        
        # JSON形式で保存
        embedding_json = json.dumps(embedding)
        
        # DBに保存
        cur.execute("""
            INSERT INTO user_conversation_embeddings (user_id, embedding_vector, conversation_summary, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                embedding_vector = EXCLUDED.embedding_vector,
                conversation_summary = EXCLUDED.conversation_summary,
                updated_at = NOW()
        """, (user_id, embedding_json, conversation_text[:500]))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✓ Updated conversation embedding for user {user_id}")
        
    except Exception as e:
        print(f"Error updating conversation embedding: {e}")
        import traceback
        traceback.print_exc()


def find_similar_user_applied_job(user_id: int) -> Optional[Dict[str, Any]]:
    """
    エンベディングで類似ユーザーを検索し、その人が応募した求人を1件返す
    
    Args:
        user_id: 現在のユーザーID
    
    Returns:
        おすすめの求人情報（1件）
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 現在のユーザーのエンベディングを取得
        cur.execute("""
            SELECT embedding_vector
            FROM user_conversation_embeddings
            WHERE user_id = %s
        """, (user_id,))
        
        current_user_emb = cur.fetchone()
        
        if not current_user_emb:
            print("⚠ No embedding found for current user")
            cur.close()
            conn.close()
            return None
        
        current_embedding = json.loads(current_user_emb['embedding_vector'])
        
        # 全ユーザーのエンベディングを取得
        cur.execute("""
            SELECT user_id, embedding_vector
            FROM user_conversation_embeddings
            WHERE user_id != %s
        """, (user_id,))
        
        all_users = cur.fetchall()
        
        if not all_users:
            print("⚠ No other users with embeddings found")
            cur.close()
            conn.close()
            return None
        
        # 類似度を計算
        similarities = []
        for user in all_users:
            other_embedding = json.loads(user['embedding_vector'])
            
            similarity = cosine_similarity(
                [current_embedding],
                [other_embedding]
            )[0][0]
            
            similarities.append({
                'user_id': user['user_id'],
                'similarity': float(similarity)
            })
        
        # 類似度の高い順にソート
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        print(f"\n=== Top 5 Similar Users by Embedding ===")
        for i, sim in enumerate(similarities[:5], 1):
            print(f"{i}. User {sim['user_id']} - Similarity: {sim['similarity']:.4f}")
        
        # 上位5人の類似ユーザーから応募済み求人を取得
        similar_user_ids = [s['user_id'] for s in similarities[:5]]
        
        # ★★★ デバッグ：各ユーザーの応募件数を確認 ★★★
        print("\n=== Similar Users' Apply Data ===")
        for uid in similar_user_ids:
            cur.execute("""
                SELECT COUNT(*) as count
                FROM user_interactions
                WHERE user_id = %s AND interaction_type = 'apply'
            """, (uid,))
            count = cur.fetchone()['count']
            print(f"  User {uid}: {count} applies")
        
        # ★★★ デバッグ：現在のユーザーが既に見た求人数を確認 ★★★
        cur.execute("""
            SELECT COUNT(DISTINCT job_id) as count
            FROM user_interactions
            WHERE user_id = %s
        """, (user_id,))
        excluded_count = cur.fetchone()['count']
        print(f"\n=== Current User's Interactions ===")
        print(f"  User {user_id} has interacted with {excluded_count} jobs (will be excluded)")
        
        # ★★★ デバッグ：除外前の応募求人数を確認 ★★★
        cur.execute("""
            SELECT COUNT(*) as count
            FROM user_interactions ui
            WHERE ui.user_id = ANY(%s)
              AND ui.interaction_type = 'apply'
        """, (similar_user_ids,))
        total_applies = cur.fetchone()['count']
        print(f"\n=== Available Jobs ===")
        print(f"  Total applies from similar users: {total_applies}")
        
        # ★★★ デバッグ：除外後の応募求人数を確認 ★★★
        cur.execute("""
            SELECT COUNT(DISTINCT ui.job_id) as count
            FROM user_interactions ui
            WHERE ui.user_id = ANY(%s)
              AND ui.interaction_type = 'apply'
              AND ui.job_id::text NOT IN (
                  SELECT job_id::text 
                  FROM user_interactions 
                  WHERE user_id = %s
              )
        """, (similar_user_ids, user_id))
        available_applies = cur.fetchone()['count']
        print(f"  Available applies (after exclusion): {available_applies}")
        
        # 実際のクエリ実行
        cur.execute("""
            SELECT 
                ui.job_id,
                cp.job_title,
                cp.location_prefecture,
                cp.salary_min,
                cp.salary_max,
                cd.company_name,
                COUNT(*) as apply_count,
                MAX(ui.created_at) as latest_apply
            FROM user_interactions ui
            JOIN company_profile cp ON ui.job_id::text = cp.id::text
            JOIN company_date cd ON cp.company_id = cd.company_id
            WHERE ui.user_id = ANY(%s)
              AND ui.interaction_type = 'apply'
              AND ui.job_id::text NOT IN (
                  SELECT job_id::text 
                  FROM user_interactions 
                  WHERE user_id = %s
              )
            GROUP BY ui.job_id, cp.job_title, cp.location_prefecture, 
                     cp.salary_min, cp.salary_max, cd.company_name
            ORDER BY apply_count DESC, latest_apply DESC
            LIMIT 1
        """, (similar_user_ids, user_id))
        
        recommended_job = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if recommended_job:
            print(f"\n✓ Found similar user applied job: {recommended_job['company_name']} / {recommended_job['job_title']}")
            return dict(recommended_job)
        else:
            print("\n⚠ No applied jobs found from similar users (after exclusion)")
            return None
        
    except Exception as e:
        print(f"Error finding similar user applied job: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_similar_user_recommendation_text(user_id: int, recommended_job: Dict) -> str:
    """
    類似ユーザーの応募求人について、GPT-4で提案文を生成
    
    Args:
        user_id: ユーザーID
        recommended_job: おすすめの求人情報
    
    Returns:
        提案文
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # ユーザーの回答履歴を取得
        cur.execute("""
            SELECT dq.question_text, uqr.response_text
            FROM user_question_responses uqr
            JOIN dynamic_questions dq ON uqr.question_id = dq.id
            WHERE uqr.user_id = %s
            ORDER BY uqr.created_at
        """, (user_id,))
        
        responses = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # ユーザーの条件を整理
        conditions_text = "\n".join([
            f"- {resp['question_text']}: {resp['response_text']}"
            for resp in responses
        ])
        
        prompt = f"""
あなたは求人マッチングAIアシスタントです。ユーザーと似た条件で求人を探していた過去のユーザーが、実際に応募した求人を見つけました。

【現在のユーザーの希望条件】
{conditions_text}

【過去の類似ユーザーが応募した求人】
- 企業名: {recommended_job['company_name']}
- 職種: {recommended_job['job_title']}
- 勤務地: {recommended_job['location_prefecture']}
- 年収: {recommended_job['salary_min']}万〜{recommended_job['salary_max']}万
- 応募実績: {recommended_job['apply_count']}人

【あなたのタスク】
この求人がなぜユーザーにマッチする可能性があるのか、温かみのある文章で提案してください。

以下の要素を含めてください：
1. 「あなたと似た条件で求人を探していた方が、実際に応募した求人があります」という導入
2. この求人の魅力ポイント
3. 「ぜひ検討してみてください」という前向きな締めくくり

自然で親しみやすいトーンで、2〜3文程度で書いてください。
"""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating similar user recommendation text: {e}")
        return "あなたと似た条件で求人を探していた方が、実際に応募した求人があります。ぜひ検討してみてください。"


# --- ヘルパー関数 ---
def extract_intent_with_ai(user_message: str) -> dict:
    """AIでユーザーの意図を抽出"""
    prompt = f"""
ユーザーの発言から以下の情報を抽出してJSON形式で返してください:

ユーザー発言: {user_message}

抽出する情報:
- job_title: 職種
- location_prefecture: 勤務地（都道府県のみ）
- salary_min: 最低年収（数値）
- その他、ユーザーが言及した条件

出力はJSON形式のみ返してください。
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        result_text = response.choices[0].message.content.strip()

        # JSON部分を抽出
        import re
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(0)

        intent = json.loads(result_text)
        return intent

    except Exception as e:
        print(f"Error extracting intent: {e}")
        return {}


def update_user_profile_with_intent(user_id: int, intent: dict):
    """抽出した意図でユーザープロファイルを更新"""
    if not intent:
        return

    # 意図が空または職種・勤務地・年収が含まれていない場合はスキップ
    has_useful_info = any(key in intent for key in ['job_title', 'location_prefecture', 'salary_min'])
    
    if not has_useful_info:
        print("  → No useful profile info in intent, skipping update")
        return

    conn = get_db_conn()
    cur = conn.cursor()

    # 既存のプロファイルを取得
    cur.execute("""
        SELECT job_title, location_prefecture, salary_min
        FROM user_profile
        WHERE user_id = %s
    """, (user_id,))

    profile = cur.fetchone()

    if not profile:
        cur.close()
        conn.close()
        return

    # マージ（既存の値を保持、空の場合のみ更新）
    job_title = intent.get('job_title') if intent.get('job_title') else profile[0]
    location_prefecture = intent.get('location_prefecture') if intent.get('location_prefecture') else profile[1]
    salary_min = intent.get('salary_min') if intent.get('salary_min') else profile[2]

    # 更新
    cur.execute("""
        UPDATE user_profile
        SET job_title = %s,
            location_prefecture = %s,
            salary_min = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
    """, (job_title, location_prefecture, salary_min, user_id))

    conn.commit()
    cur.close()
    conn.close()

# --- 管理者機能: 動的質問の生成 ---
@app.route("/admin/generate_questions", methods=["POST"])
def admin_generate_questions():
    """求人データから動的質問を生成（管理者用）"""
    questions = QuestionGenerator.generate_questions_from_jobs()
    saved_count = QuestionGenerator.save_generated_questions(questions)

    return jsonify({
        "status": "success",
        "generated_questions": len(questions),
        "saved": saved_count
    })


# --- 初期化関数（ここに追加）---
def initialize_questions():
    """
    初期質問をDBに登録（オプション）
    
    注意: 新しい動的質問生成システムでは、このリストは参考用として残していますが、
    実際の質問はAIが求人データとユーザーの状況から自動生成します。
    
    固定リストを使いたい場合は、このまま実行してください。
    完全動的にする場合は、この関数を実行しないでください。
    """
    conn = get_db_conn()
    cur = conn.cursor()
    
    # 基本的な質問テンプレート（参考用）
    # これらは動的生成のベースとなる質問パターンです
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
        try:
            cur.execute("""
                INSERT INTO dynamic_questions (question_key, question_text, category, question_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (question_key) DO NOTHING
            """, (q_key, q_text, category, q_type))
        except Exception as e:
            print(f"Error inserting question: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    print("✓ Initial questions initialized (optional templates)")
    print("  Note: New system uses AI to generate questions dynamically")


def extract_all_job_attributes():
    """全求人の属性を抽出（バックグラウンド実行用）"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM company_profile")
    job_ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    print(f"⏳ Extracting attributes for {len(job_ids)} jobs...")
    
    for i, job_id in enumerate(job_ids, 1):
        try:
            JobAttributeExtractor.extract_and_save_job_attributes(job_id)
            print(f"  [{i}/{len(job_ids)}] Extracted: {job_id}")
        except Exception as e:
            print(f"  [{i}/{len(job_ids)}] Failed: {job_id} - {e}")
    
    print("✓ All job attributes extracted")


# --- メイン起動（ここから）---
if __name__ == "__main__":
    # アプリ起動時に初期質問を登録
    initialize_questions()
    
    # 求人属性が未抽出なら抽出
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM job_attributes")
    attr_count = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    if attr_count == 0:
        print("⚠ Job attributes not extracted. Extracting...")
        # バックグラウンドで実行（時間がかかるため）
        import threading
        threading.Thread(target=extract_all_job_attributes, daemon=True).start()
    else:
        print(f"✓ Job attributes already extracted ({attr_count} records)")
    
    app.run(debug=True, port=5002, load_dotenv=False)