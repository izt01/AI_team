"""
AI求人マッチングシステム FastAPI版 v2.0
- 動的質問生成（学習データ駆動）
- ハイブリッドレコメンデーション（協調フィルタリング + コンテンツベース）
- 多軸評価（企業文化、働き方、キャリアパス）
- ユーザー行動追跡（クリック、お気に入り、応募）
"""

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.sessions import SessionMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from openai import OpenAI
import uuid
import json
from typing import List, Dict, Any, Optional
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
from db_config import get_db_conn

# FastAPIアプリケーション初期化
app = FastAPI(
    title="AI求人マッチングシステム",
    description="FastAPI版求人マッチングAPI",
    version="2.0.0"
)

# セッション管理のミドルウェアを追加
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("FLASK_SECRET_KEY", "supersecretkey")
)

# テンプレート設定
templates = Jinja2Templates(directory="templates_fastapi")

# 静的ファイル
# app.mount("/static", StaticFiles(directory="static"), name="static")

# OpenAI APIキーを環境変数から取得
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY が .env ファイルに設定されていません")

client = OpenAI(api_key=openai_api_key)

# 動的質問生成器の初期化
dynamic_question_gen = DynamicQuestionGenerator(client)


# --- セッションヘルパー ---
def get_user_id(request: Request) -> Optional[int]:
    """リクエストからuser_idを取得"""
    return request.session.get("user_id")


def get_or_create_session_id(request: Request) -> str:
    """チャットセッションIDを取得または生成"""
    if 'chat_session_id' not in request.session:
        request.session['chat_session_id'] = str(uuid.uuid4())
    return request.session['chat_session_id']


def require_login(request: Request):
    """ログイン必須の依存性"""
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインが必要です"
        )
    return user_id


# --- ルート ---
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """ランディングページ"""
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/step1", response_class=HTMLResponse)
async def step1_get(request: Request):
    """Step1: 個人情報登録画面"""
    return templates.TemplateResponse("form_step1.html", {"request": request})


@app.post("/step1")
async def step1_post(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    birth_day: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    address: Optional[str] = Form(None)
):
    """Step1: 個人情報登録処理"""
    password_hash = generate_password_hash(password)
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    # 最大user_id + 1を取得
    cur.execute("SELECT COALESCE(MAX(user_id), 0) + 1 FROM personal_date")
    new_user_id = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO personal_date (user_id, email, password_hash, user_name, birth_day, phone_number, address, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (new_user_id, email, password_hash, name, birth_day, phone_number, address))
    
    cur.execute("""
        INSERT INTO user_profile (user_id, job_title, location_prefecture, salary_min, created_at, updated_at)
        VALUES (%s, '', '', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (new_user_id,))
    
    conn.commit()
    cur.close()
    conn.close()
    
    # セッションに保存
    request.session["user_id"] = new_user_id
    
    return RedirectResponse(url="/step2", status_code=302)


@app.get("/step2", response_class=HTMLResponse)
async def step2_get(request: Request):
    """Step2: 希望条件入力画面"""
    return templates.TemplateResponse("form_step2.html", {"request": request})


@app.post("/step2")
async def step2_post(
    request: Request,
    job_title: str = Form(...),
    location_prefecture: str = Form(...),
    salary_min: int = Form(...)
):
    """Step2: 希望条件入力処理"""
    user_id = get_user_id(request)
    if not user_id:
        return RedirectResponse(url="/step1", status_code=302)
    
    conn = get_db_conn()
    cur = conn.cursor()
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
    
    return RedirectResponse(url="/profile", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    """ログイン画面"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login_post(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...)
):
    """ログイン処理"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, email, password_hash FROM personal_date WHERE email=%s OR user_name=%s",
        (identifier, identifier)
    )
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user and check_password_hash(user[2], password):
        request.session["user_id"] = user[0]
        return RedirectResponse(url="/profile", status_code=302)
    else:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "ログイン失敗しました"}
        )


@app.get("/logout")
async def logout(request: Request):
    """ログアウト"""
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user_id: int = Depends(require_login)):
    """プロフィール確認ページ"""
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # ユーザー基本情報を取得
    cur.execute("""
        SELECT pd.email, pd.user_name, 
               up.job_title, up.location_prefecture, up.salary_min
        FROM personal_date pd
        LEFT JOIN user_profile up ON pd.user_id = up.user_id
        WHERE pd.user_id = %s
    """, (user_id,))
    
    user_data = cur.fetchone()
    cur.close()
    conn.close()
    
    if not user_data:
        return RedirectResponse(url="/step1", status_code=302)
    
    # テンプレートに渡すデータ
    context = {
        "request": request,
        "user_name": user_data.get('user_name', 'ユーザー'),
        "email": user_data.get('email', ''),
        "job_title": user_data.get('job_title'),
        "location": user_data.get('location_prefecture'),
        "salary": user_data.get('salary_min'),
        # 追加情報（後で拡張可能）
        "employment_type": None,
        "work_hours": None,
        "holiday_policy": None,
        "workplace_atmosphere": None,
        "remote": None,
        "employee_benefits": None,
        "job_summary": None,
        "skills": None,
        "certifications": None
    }
    
    return templates.TemplateResponse("profile.html", context)

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, user_id: int = Depends(require_login)):
    """チャット画面"""
    session_id = get_or_create_session_id(request)
    
    # 推薦を取得
    recommendations = HybridRecommender.get_hybrid_recommendations(user_id, top_k=None, previous_job_ids=None)
    count = len(recommendations)
    print(f"Initial recommendations: {count} jobs")
    
    # データベースに初回の結果を保存
    initial_job_ids = [str(job['id']) for job in recommendations]
    save_filtered_job_ids_to_db(user_id, session_id, initial_job_ids)
    
    if count == 0:
        initial_message = "条件に合う求人が見つかりませんでした。条件を見直してください。"
    elif count <= 3:
        # 3件以下なら最終段階
        update_user_conversation_embedding(user_id)
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
        
        # メッセージ生成
        initial_message = build_final_message(
            recommendations, best_matches, similar_user_job, explanation, user_id
        )
    else:
        # 4件以上なら完全動的に質問を生成
        next_question = dynamic_question_gen.generate_next_question(user_id, recommendations, "")
        
        if next_question:
            # セッションに質問情報を保存
            request.session['last_question_key'] = next_question['question_key']
            request.session['last_question_text'] = next_question['question_text']
            request.session['last_question_category'] = next_question.get('category', '働き方の柔軟性')
            
            initial_message = f"あなたにマッチする求人が {count} 件見つかりました。\n\n{next_question['question_text']}"
        else:
            initial_message = f"あなたにマッチする求人が {count} 件見つかりました。\n\n条件を追加してください。"
    
    # 初回メッセージをチャット履歴に保存
    ChatHistoryManager.save_message(user_id, 'bot', initial_message, session_id=session_id)
    
    return templates.TemplateResponse(
        'chat.html',
        {"request": request, "initial_message": initial_message}
    )


@app.post("/api/chat")
async def chat_api(request: Request, user_id: int = Depends(require_login)):
    """チャットAPIエンドポイント"""
    data = await request.json()
    user_message = data.get("message", "")
    
    session_id = get_or_create_session_id(request)
    
    # ユーザーメッセージを保存
    ChatHistoryManager.save_message(user_id, 'user', user_message, session_id=session_id)
    
    # 前回のフィルタリング結果を取得
    previous_job_ids = get_filtered_job_ids_from_db(user_id, session_id)
    
    # 質問に対する回答を処理
    last_question_key = request.session.get('last_question_key')
    last_question_category = request.session.get('last_question_category', '働き方の柔軟性')
    
    if last_question_key:
        # 回答を保存
        QuestionResponseManager.save_response(
            user_id=user_id,
            question_key=last_question_key,
            response_text=user_message,
            category=last_question_category
        )
    
    # 推薦を再取得
    recommendations = HybridRecommender.get_hybrid_recommendations(
        user_id,
        top_k=None,
        previous_job_ids=previous_job_ids
    )
    
    count = len(recommendations)
    print(f"Filtered recommendations: {count} jobs")
    
    # 結果を保存
    current_job_ids = [str(job['id']) for job in recommendations]
    save_filtered_job_ids_to_db(user_id, session_id, current_job_ids)
    
    # レスポンス生成
    if count == 0:
        bot_message = "条件に合う求人が見つかりませんでした。条件を見直してください。"
        final_jobs = []
    elif count <= 3:
        # 最終段階
        update_user_conversation_embedding(user_id)
        displayed_ids = [str(job['id']) for job in recommendations]
        
        best_matches = find_best_matches_with_embeddings(
            user_id,
            filtered_jobs=None,
            top_k=2,
            exclude_ids=displayed_ids
        )
        
        similar_user_job = find_similar_user_applied_job(user_id)
        
        all_jobs = recommendations + best_matches
        if similar_user_job:
            all_jobs.append(similar_user_job)
        
        explanation = generate_final_recommendation_with_gpt(user_id, all_jobs)
        bot_message = build_final_message(
            recommendations, best_matches, similar_user_job, explanation, user_id
        )
        
        # ✅ 最終求人データを保存（フロントエンドに送信するため）
        final_jobs = all_jobs
    else:
        # 次の質問を生成
        next_question = dynamic_question_gen.generate_next_question(user_id, recommendations, user_message)
        
        if next_question:
            request.session['last_question_key'] = next_question['question_key']
            request.session['last_question_text'] = next_question['question_text']
            request.session['last_question_category'] = next_question.get('category', '働き方の柔軟性')
            
            bot_message = f"{count}件に絞り込まれました。\n\n{next_question['question_text']}"
        else:
            bot_message = f"{count}件に絞り込まれました。\n\n条件を追加してください。"
        
        final_jobs = []
    
    # ボットメッセージを保存
    ChatHistoryManager.save_message(user_id, 'bot', bot_message, session_id=session_id)
    
    # ✅ レスポンスに求人データを含める
    return JSONResponse({
        "response": bot_message,
        "jobs": final_jobs if count <= 3 else []
    })


# --- ヘルパー関数 ---
def save_filtered_job_ids_to_db(user_id: int, session_id: str, job_ids: List[str]):
    """フィルタリング結果をデータベースに保存"""
    conn = get_db_conn()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO user_filtering_history (user_id, session_id, filtered_job_ids, created_at)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id, session_id)
        DO UPDATE SET filtered_job_ids = EXCLUDED.filtered_job_ids, created_at = CURRENT_TIMESTAMP
    """, (user_id, session_id, job_ids))
    
    conn.commit()
    cur.close()
    conn.close()


def get_filtered_job_ids_from_db(user_id: int, session_id: str) -> Optional[List[str]]:
    """前回のフィルタリング結果を取得"""
    conn = get_db_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT filtered_job_ids FROM user_filtering_history
        WHERE user_id = %s AND session_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id, session_id))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    return result[0] if result else None


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


def update_user_conversation_embedding(user_id: int):
    """ユーザーの会話履歴をエンベディング化"""
    # チャット履歴を取得
    history = ChatHistoryManager.get_chat_history(user_id, limit=20)
    
    # ユーザーメッセージのみを結合
    user_messages = [msg['message_text'] for msg in history if msg['message_type'] == 'user']
    combined_text = " ".join(user_messages)
    
    if not combined_text:
        return
    
    # エンベディング生成
    embedding = generate_embedding(combined_text)
    
    if embedding:
        # データベースに保存
        conn = get_db_conn()
        cur = conn.cursor()

        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        
        cur.execute("""
            UPDATE user_profile
            SET conversation_embedding = %s
            WHERE user_id = %s
        """, (embedding, user_id))

        print(f"✅ Updated conversation embedding for user {user_id}")
        
        conn.commit()
        cur.close()
        conn.close()


def find_best_matches_with_embeddings(
    user_id: int,
    filtered_jobs: List[Dict] = None,
    top_k: int = 2,
    exclude_ids: List[str] = None
) -> List[Dict[str, Any]]:
    """エンベディング検索で最もマッチする求人を見つける"""
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # ユーザーのエンベディングを取得
    cur.execute("""
        SELECT conversation_embedding FROM user_profile WHERE user_id = %s
    """, (user_id,))
    
    result = cur.fetchone()
    if not result or not result['conversation_embedding']:
        cur.close()
        conn.close()
        return []
    
    user_embedding = result['conversation_embedding']

    # 文字列の場合はパースする
    if isinstance(user_embedding, str):
        import json
        user_embedding = json.loads(user_embedding)

    user_embedding = np.array(user_embedding)
    print(f"✅ User embedding shape: {user_embedding.shape}")
    
    # 求人のエンベディングを取得
    exclude_clause = ""
    params = []
    
    if exclude_ids:
        placeholders = ','.join(['%s'] * len(exclude_ids))
        exclude_clause = f" AND cp.id::text NOT IN ({placeholders})"
        params = exclude_ids
    
    query = f"""
        SELECT 
            cp.id::text,
            cp.job_title,
            cp.location_prefecture,
            cp.salary_min,
            cp.salary_max,
            cp.embedding,
            cd.company_name
        FROM company_profile cp
        JOIN company_date cd ON cp.company_id = cd.company_id
        WHERE cp.embedding IS NOT NULL{exclude_clause}
    """
    
    cur.execute(query, params)
    jobs = cur.fetchall()
    
    cur.close()
    conn.close()
    
    if not jobs:
        return []
    
    # 類似度計算
    similarities = []
    for job in jobs:
        # ✅ 求人エンベディングの型チェックと変換
        job_embedding = job['embedding']
        
        # 文字列の場合はパースする
        if isinstance(job_embedding, str):
            import json
            job_embedding = json.loads(job_embedding)
        
        job_embedding = np.array(job_embedding)
        
        # コサイン類似度を計算
        similarity = cosine_similarity([user_embedding], [job_embedding])[0][0]
        similarities.append({
            'id': job['id'],
            'job_title': job['job_title'],
            'location_prefecture': job['location_prefecture'],
            'salary_min': job['salary_min'],
            'salary_max': job['salary_max'],
            'company_name': job['company_name'],
            'similarity': similarity
        })
    
    # 類似度でソート
    similarities.sort(key=lambda x: x['similarity'], reverse=True)
    
    return similarities[:top_k]


def find_similar_user_applied_job(user_id: int) -> Optional[Dict[str, Any]]:
    """類似ユーザーの応募済み求人を取得"""
    try:
        from hybrid_recommender import CollaborativeFiltering
        
        # 類似ユーザーを取得（上位10人）
        similar_users = CollaborativeFiltering.find_similar_users(user_id, top_k=10)
        
        if not similar_users:
            print(f"⚠️ No similar users found for user {user_id}")
            return None
        
        print(f"🔍 Found {len(similar_users)} similar users")
        
        # 類似ユーザーのIDリストを取得
        similar_user_ids = [uid for uid, _ in similar_users]
        
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 類似ユーザーが応募した求人を取得（応募回数が多い順）
        cur.execute("""
            SELECT 
                cp.id,
                cp.job_title,
                cp.location_prefecture,
                cp.salary_min,
                cp.salary_max,
                cd.company_name,
                COUNT(*) as apply_count
            FROM user_interactions ui
            JOIN company_profile cp ON ui.job_id = cp.id
            JOIN company_date cd ON cp.company_id = cd.company_id
            WHERE ui.user_id = ANY(%s)
              AND ui.interaction_type = 'apply'
              AND ui.user_id != %s
            GROUP BY cp.id, cp.job_title, cp.location_prefecture, 
                     cp.salary_min, cp.salary_max, cd.company_name
            ORDER BY apply_count DESC, cp.salary_max DESC
            LIMIT 1
        """, (similar_user_ids, user_id))
        
        job = cur.fetchone()
        cur.close()
        conn.close()
        
        if job:
            job_dict = dict(job)
            print(f"✅ Found similar user job: {job_dict['job_title']} (applied by {job_dict['apply_count']} similar users)")
            return job_dict
        else:
            print(f"⚠️ No applied jobs found from similar users")
            return None
            
    except Exception as e:
        print(f"Error finding similar user job: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_final_recommendation_with_gpt(user_id: int, jobs: List[Dict]) -> str:
    """GPT-4で最終推薦の説明文を生成"""
    try:
        # ユーザープロフィールを取得
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT job_title, location_prefecture, salary_min
            FROM user_profile WHERE user_id = %s
        """, (user_id,))
        
        profile = cur.fetchone()
        cur.close()
        conn.close()
        
        # プロンプト作成
        prompt = f"""
あなたは求人マッチングのキャリアアドバイザーです。
以下のユーザーに対して、おすすめの求人を紹介してください。

【ユーザープロフィール】
希望職種: {profile['job_title']}
希望勤務地: {profile['location_prefecture']}
希望年収: {profile['salary_min']}万円以上

【推薦求人】
{json.dumps([{
    'title': job['job_title'],
    'company': job['company_name'],
    'location': job['location_prefecture'],
    'salary': f"{job['salary_min']}~{job['salary_max']}万円"
} for job in jobs[:5]], ensure_ascii=False, indent=2)}

簡潔に3行程度で、なぜこれらの求人をおすすめするのか説明してください。
"""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating GPT explanation: {e}")
        return "あなたに最適な求人をご紹介します。"


def build_final_message(
    recommendations: List[Dict],
    best_matches: List[Dict],
    similar_user_job: Optional[Dict],
    explanation: str,
    user_id: int
) -> str:
    """最終メッセージを組み立て"""
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
        similar_user_detail = (
            f"💼 {similar_user_job['company_name']} / {similar_user_job['job_title']}\n"
            f"📍 {similar_user_job['location_prefecture']}\n"
            f"💰 年収: {similar_user_job['salary_min']}万〜{similar_user_job['salary_max']}万\n"
            f"👥 類似ユーザー {similar_user_job['apply_count']}人が応募"
        )
    
    # 最終メッセージを組み立て
    total_count = len(recommendations) + len(best_matches) + (1 if similar_user_job else 0)
    
    message = f"{explanation}\n\n"
    message += f"【絞り込んだ候補（{len(recommendations)}件）】\n\n"
    message += "\n\n".join(filtered_details)
    
    if additional_details:
        message += f"\n\n【AIが選んだ追加のおすすめ（{len(best_matches)}件）】\n\n"
        message += "\n\n".join(additional_details)
    
    if similar_user_detail:
        message += f"\n\n【類似ユーザーが応募した求人】\n\n"
        message += similar_user_detail
    
    message += f"\n\n✨ 合計 {total_count} 件の求人をご紹介しました。"
    
    return message


# --- 起動 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)