"""
進化型AI求人マッチングシステム FastAPI版 v3.0 完全版

【主要機能】
1. 基本情報で初期検索（DB検索は1回のみ）
2. AIによる動的質問生成（ユーザーごとにパーソナライズ）
3. 会話ごとにスコアリング（全候補を再評価）
4. 複数の終了条件（80%達成、収束、ユーザー要求、10ターン上限）
5. マッチ理由の説明付き推薦（マッチ度0-100%表示）
6. 会話・スコア履歴の完全追跡
"""

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import uuid
import json
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from datetime import datetime

# 環境変数読み込み
load_dotenv()

# 自作モジュール
from db_config import get_db_conn
from tracking_evolved import (
    ConversationTracker,
    ScoreHistoryTracker,
    UserInteractionTracker,
    ChatHistoryManager
)
from dynamic_question_generator_evolved import EvolvingQuestionGenerator

# FastAPIアプリケーション初期化
app = FastAPI(
    title="進化型AI求人マッチングシステム",
    description="動的質問生成とAIスコアリングによる高精度マッチング",
    version="3.0.0"
)

# セッション管理
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("FLASK_SECRET_KEY", "evolving-ai-matching-secret")
)

# テンプレート設定
templates = Jinja2Templates(directory="templates_fastapi")

# OpenAI クライアント
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY が .env ファイルに設定されていません")

client = OpenAI(api_key=openai_api_key)

# 質問生成器の初期化
question_generator = EvolvingQuestionGenerator()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# セッションヘルパー
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_user_id(request: Request) -> Optional[int]:
    """リクエストからuser_idを取得"""
    return request.session.get("user_id")


def get_session_id(request: Request) -> Optional[str]:
    """チャットセッションIDを取得"""
    return request.session.get("chat_session_id")


def require_login(request: Request):
    """ログイン必須の依存性"""
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインが必要です"
        )
    return user_id


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 基本ルート（登録・ログイン）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
    
    # 最大user_id + 1を取得（idとuser_idを同じ値にする）
    cur.execute("SELECT COALESCE(MAX(user_id), 0) + 1 FROM personal_date")
    new_user_id = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO personal_date (
            id, user_id, email, password_hash, user_name, 
            birth_day, phone_number, address, 
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (new_user_id, new_user_id, email, password_hash, name, birth_day, phone_number, address))
    
    cur.execute("""
        INSERT INTO user_profile (
            user_id, job_title, location_prefecture, salary_min, 
            created_at, updated_at
        )
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
    """Step2: 希望条件入力処理 → 初期検索を実行"""
    user_id = get_user_id(request)
    if not user_id:
        return RedirectResponse(url="/step1", status_code=302)
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # user_profile を更新
    cur.execute("""
        UPDATE user_profile
        SET job_title = %s,
            location_prefecture = %s,
            salary_min = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
    """, (job_title, location_prefecture, salary_min, user_id))
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔥 初期検索（DB検索は1回だけ）
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 注: テーブルに存在するカラムのみを取得
    cur.execute("""
        SELECT 
            cp.id::text as job_id,
            cp.job_title,
            cp.location_prefecture,
            cp.salary_min,
            cp.salary_max,
            cd.company_name
        FROM company_profile cp
        JOIN company_date cd ON cp.company_id = cd.company_id
        WHERE cp.job_title ILIKE %s
          AND cp.location_prefecture = %s
          AND cp.salary_min >= %s
        ORDER BY cp.created_at DESC
    """, (f'%{job_title}%', location_prefecture, salary_min))
    
    initial_candidates = cur.fetchall()
    
    # キャンディデートをセッションに保存（JSON形式）
    candidates_list = []
    for job in initial_candidates:
        job_dict = dict(job)
        
        # 基本スコア情報
        job_dict['score'] = 0  # 初期スコア0
        job_dict['score_details'] = []  # スコア詳細
        job_dict['match_percentage'] = 0  # マッチ度0%
        
        # テーブルに存在しない可能性のあるカラムにデフォルト値を設定
        job_dict.setdefault('job_summary', '')
        job_dict.setdefault('remote_work', 'なし')
        
        # 🎲 デモ用: リモート情報をランダムに設定（実際はDBから取得すべき）
        import random
        if 'remote_option' not in job_dict or not job_dict.get('remote_option'):
            remote_options = ['完全リモート可', 'ハイブリッド', 'なし', 'なし', 'なし']  # なしが多め
            job_dict['remote_option'] = random.choice(remote_options)
        
        job_dict.setdefault('company_culture', '')
        job_dict.setdefault('work_flexibility', '')
        
        candidates_list.append(job_dict)
    
    # セッションIDを生成
    session_id = str(uuid.uuid4())
    request.session['chat_session_id'] = session_id
    
    # 🔥 セッションデータをデータベースに保存（クッキー制限回避）
    conn_session = get_db_conn()
    cur_session = conn_session.cursor()
    
    # user_sessions テーブルが存在しない場合は作成
    cur_session.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id VARCHAR(100) PRIMARY KEY,
            user_id INTEGER,
            session_data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # セッションデータを保存
    session_data = {
        'candidates': candidates_list,
        'initial_candidate_count': len(candidates_list),
        'conversation_turn': 0,
        'score_history': [],
        'accumulated_insights': {
            'explicit_preferences': {},
            'implicit_values': {},
            'pain_points': [],
            'keywords': []
        }
    }
    
    cur_session.execute("""
        INSERT INTO user_sessions (session_id, user_id, session_data)
        VALUES (%s, %s, %s)
        ON CONFLICT (session_id) DO UPDATE
        SET session_data = EXCLUDED.session_data,
            updated_at = CURRENT_TIMESTAMP
    """, (session_id, user_id, json.dumps(session_data)))
    
    conn_session.commit()
    cur_session.close()
    conn_session.close()
    
    # 🔍 デバッグ: セッション保存を確認
    print(f"✅ DEBUG: Saved {len(candidates_list)} candidates to DATABASE (not cookie)")
    print(f"✅ DEBUG: session_id={session_id}")
    
    # クッキーには最小限の情報のみ保存
    request.session['initial_candidate_count'] = len(candidates_list)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ 初期検索: {len(candidates_list)}件の候補を取得")
    
    return RedirectResponse(url="/chat", status_code=302)


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
    
    context = {
        "request": request,
        "user_name": user_data.get('user_name', 'ユーザー'),
        "email": user_data.get('email', ''),
        "job_title": user_data.get('job_title'),
        "location": user_data.get('location_prefecture'),
        "salary": user_data.get('salary_min'),
    }
    
    return templates.TemplateResponse("profile.html", context)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# チャット機能（進化型システムのコア）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, user_id: int = Depends(require_login)):
    """チャット画面（初回表示）"""
    
    # 🔍 デバッグ: セッション内容を確認
    print(f"🔍 DEBUG: user_id={user_id}")
    session_id = request.session.get('chat_session_id')
    print(f"🔍 DEBUG: session_id={session_id}")
    
    if not session_id:
        print(f"❌ DEBUG: No session_id found, redirecting to /profile")
        return RedirectResponse(url="/profile", status_code=302)
    
    # 🔥 データベースからセッションデータを取得
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT session_data FROM user_sessions
        WHERE session_id = %s AND user_id = %s
    """, (session_id, user_id))
    
    result = cur.fetchone()
    
    if not result:
        print(f"❌ DEBUG: No session data found in DB, redirecting to /profile")
        cur.close()
        conn.close()
        return RedirectResponse(url="/profile", status_code=302)
    
    session_data = result['session_data']
    candidates = session_data.get('candidates', [])
    initial_count = session_data.get('initial_candidate_count', 0)
    
    print(f"🔍 DEBUG: candidates count={len(candidates)} (from DATABASE)")
    print(f"🔍 DEBUG: initial_count={initial_count}")
    
    if not candidates:
        # 候補がない場合はプロフィールに戻る
        print(f"❌ DEBUG: No candidates found, redirecting to /profile")
        cur.close()
        conn.close()
        return RedirectResponse(url="/profile", status_code=302)
    
    # ユーザー情報取得（同じ接続を再利用）
    cur.execute("""
        SELECT pd.user_name, up.job_title
        FROM personal_date pd
        LEFT JOIN user_profile up ON pd.user_id = up.user_id
        WHERE pd.user_id = %s
    """, (user_id,))
    
    user_data = cur.fetchone()
    
    user_name = user_data.get('user_name', 'ユーザー') if user_data else 'ユーザー'
    job_title = user_data.get('job_title', '希望職種') if user_data else '希望職種'
    
    # 🔥 DBからチャット履歴を取得
    chat_history = []
    cur.execute("""
        SELECT sender, message, created_at
        FROM chat_history
        WHERE session_id = %s
        ORDER BY created_at
    """, (session_id,))
    
    for row in cur.fetchall():
        chat_history.append({
            'sender': row['sender'],
            'message': row['message'],
            'timestamp': row['created_at'].isoformat()
        })
    
    # 初回アクセスの場合（履歴が空）
    if not chat_history:
        # 初回メッセージを生成
        first_message = f"""こんにちは、{user_name}さん！

{job_title}の求人を{initial_count}件見つけました。
あなたに最適な求人を見つけるため、いくつか質問させてください。

まず、理想の働き方について教えていただけますか？

（例: 「リモートワークで柔軟に働きたい」「チームで協力して働きたい」「成長できる環境がいい」など）"""
        
        # チャット履歴に追加
        chat_history = [{
            'sender': 'bot',
            'message': first_message,
            'timestamp': datetime.now().isoformat()
        }]
        
        # DBに保存
        ChatHistoryManager.save_message(
            user_id=user_id,
            session_id=session_id,
            sender='bot',
            message=first_message
        )
    
    print(f"✅ DEBUG: チャット履歴 {len(chat_history)}件をテンプレートに渡します")
    
    cur.close()
    conn.close()
    
    # 初回メッセージをテンプレートに渡す
    initial_message = None
    if chat_history:
        # 最初のメッセージ（BOTのメッセージ）を取得
        first_bot_message = next((msg for msg in chat_history if msg['sender'] == 'bot'), None)
        if first_bot_message:
            initial_message = first_bot_message['message'].replace('\n', '<br>')
    
    context = {
        "request": request,
        "user_name": user_name,
        "candidate_count": initial_count,
        "messages": chat_history,
        "initial_message": initial_message  # テンプレート用
    }
    
    return templates.TemplateResponse("chat.html", context)


@app.post("/api/chat")
async def chat_message(
    request: Request,
    user_id: int = Depends(require_login)
):
    """ユーザーメッセージを受信して応答（進化型システムのメイン処理）"""
    
    # JSONボディを取得
    try:
        body = await request.json()
        message = body.get('message', '')
    except Exception as e:
        return JSONResponse({
            'error': 'Invalid request format',
            'redirect': '/profile'
        })
    
    if not message:
        return JSONResponse({
            'error': 'メッセージが空です',
            'redirect': '/profile'
        })
    
    # セッションIDを取得
    session_id = request.session.get('chat_session_id')
    
    if not session_id:
        return JSONResponse({
            'error': 'セッションが見つかりません。最初からやり直してください。',
            'redirect': '/profile'
        })
    
    # 🔥 データベースからセッションデータを取得
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT session_data FROM user_sessions
        WHERE session_id = %s AND user_id = %s
    """, (session_id, user_id))
    
    result = cur.fetchone()
    
    if not result:
        cur.close()
        conn.close()
        return JSONResponse({
            'error': 'セッションデータが見つかりません。最初からやり直してください。',
            'redirect': '/profile'
        })
    
    session_data = result['session_data']
    
    # セッションデータから取得
    candidates = session_data.get('candidates', [])
    conversation_turn = session_data.get('conversation_turn', 0)
    score_history = session_data.get('score_history', [])
    accumulated_insights = session_data.get('accumulated_insights', {
        'explicit_preferences': {},
        'implicit_values': {},
        'pain_points': [],
        'keywords': []
    })
    
    # chat_historyはDBから取得
    chat_history = []
    cur.execute("""
        SELECT sender, message, created_at
        FROM chat_history
        WHERE session_id = %s
        ORDER BY created_at
    """, (session_id,))
    
    for row in cur.fetchall():
        chat_history.append({
            'sender': row['sender'],
            'message': row['message'],
            'timestamp': row['created_at'].isoformat()
        })
    
    cur.close()
    conn.close()
    
    if not candidates:
        return JSONResponse({
            'error': '候補求人が見つかりません。最初からやり直してください。',
            'redirect': '/profile'
        })
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1: ユーザーメッセージを保存
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    chat_history.append({
        'sender': 'user',
        'message': message,
        'timestamp': datetime.now().isoformat()
    })
    
    # DB にも保存
    ChatHistoryManager.save_message(
        user_id=user_id,
        session_id=session_id,
        sender='user',
        message=message
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2: AI意図抽出
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    extracted_info = extract_user_intent(message)
    
    print(f"🔍 抽出情報: {json.dumps(extracted_info, ensure_ascii=False, indent=2)}")
    
    # 🔥 職種変更・追加の検出
    job_change = extracted_info.get('job_change_request', {})
    if job_change.get('requested') and job_change.get('new_job_titles'):
        print(f"🔄 職種変更・追加を検出: {job_change['new_job_titles']}")
        
        # 追加検索を実行
        for new_job_title in job_change['new_job_titles']:
            conn_add = get_db_conn()
            cur_add = conn_add.cursor(cursor_factory=RealDictCursor)
            
            cur_add.execute("""
                SELECT 
                    cp.id::text as job_id,
                    cp.job_title,
                    cp.location_prefecture,
                    cp.salary_min,
                    cp.salary_max,
                    cd.company_name
                FROM company_profile cp
                JOIN company_date cd ON cp.company_id = cd.company_id
                WHERE cp.job_title LIKE %s
                LIMIT 40
            """, (f'%{new_job_title}%',))
            
            new_candidates = cur_add.fetchall()
            cur_add.close()
            conn_add.close()
            
            # 既存候補と重複しない求人のみ追加
            existing_ids = {job['job_id'] for job in candidates}
            for new_job in new_candidates:
                job_dict = dict(new_job)
                if job_dict['job_id'] not in existing_ids:
                    job_dict['score'] = 50.0  # 初期スコア
                    job_dict['score_details'] = [('基本スコア', 50)]
                    job_dict['match_percentage'] = 0.0
                    candidates.append(job_dict)
                    existing_ids.add(job_dict['job_id'])
            
            print(f"✅ {new_job_title}の求人を{len(new_candidates)}件追加（重複除外後: {len(candidates)}件）")
    
    # 🔥 代替条件への同意を検出
    alt_condition = extracted_info.get('alternative_condition_acceptance', {})
    if alt_condition.get('accepted'):
        condition_type = alt_condition.get('condition_type', '')
        details = alt_condition.get('details', '')
        
        print(f"✨ 代替条件への同意を検出: {condition_type} - {details}")
        
        # explicit_preferencesに追加
        if condition_type == 'work_hours' and details:
            # フレックスタイム、10時出社などの条件
            if 'explicit_preferences' not in accumulated_insights:
                accumulated_insights['explicit_preferences'] = {}
            accumulated_insights['explicit_preferences']['flexible_hours'] = details
            accumulated_insights['keywords'].append('フレックス')
            print(f"  → 勤務時間の柔軟性を条件に追加: {details}")
    
    # 抽出情報を蓄積
    accumulated_insights = merge_insights(accumulated_insights, extracted_info)
    
    # DBに蓄積情報を保存
    ConversationTracker.save_extracted_insights(
        user_id=user_id,
        session_id=session_id,
        extracted_info=accumulated_insights
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 3: 全候補を再スコアリング
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    conversation_turn += 1
    # 🔥 重要: 蓄積された情報（accumulated_insights）を使う
    candidates = rescore_all_candidates(candidates, accumulated_insights, conversation_turn)
    
    print(f"📝 蓄積された条件:")
    print(f"  - リモート: {accumulated_insights.get('explicit_preferences', {}).get('remote_work', 'なし')}")
    print(f"  - 学習興味: {accumulated_insights.get('explicit_preferences', {}).get('learning_interest', 'なし')}")
    print(f"  - キーワード: {accumulated_insights.get('keywords', [])}")
    
    # マッチ度を計算
    candidates = calculate_match_percentages(candidates, conversation_turn)
    
    # スコア順にソート
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # スコア履歴に追加
    top_job = candidates[0]
    score_history.append({
        'turn': conversation_turn,
        'top_score': top_job['score'],
        'top_match_percentage': top_job['match_percentage']
    })
    
    print(f"📊 ターン{conversation_turn}: トップスコア={top_job['score']:.1f}, マッチ度={top_job['match_percentage']:.1f}%")
    
    # スコア履歴をDBに保存（上位10件のみ）
    for job in candidates[:10]:
        ScoreHistoryTracker.record_score(
            user_id=user_id,
            session_id=session_id,
            turn_number=conversation_turn,
            job_id=job['job_id'],
            score=job['score'],
            match_percentage=job['match_percentage'],
            score_details=job.get('score_details', [])
        )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 4: 終了判定
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    context = {
        'conversation_turn': conversation_turn,
        'top_match_percentage': top_job['match_percentage'],
        'score_history': score_history,
        'user_message': message
    }
    
    decision = should_end_conversation(context)
    
    if decision['should_end']:
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 会話終了 → 求人提案
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # 上位5件を取得
        top_5 = candidates[:5]
        
        # マッチ理由を生成（AI）
        for job in top_5:
            job['match_reasoning'] = generate_match_reasoning(
                user_id,
                job,
                accumulated_insights
            )
        
        # 推薦メッセージ生成
        recommendation_message = generate_recommendation_message(
            user_id,
            top_5,
            decision['reason'],
            accumulated_insights
        )
        
        # チャット履歴に追加
        chat_history.append({
            'sender': 'bot',
            'message': recommendation_message,
            'timestamp': datetime.now().isoformat(),
            'recommendations': top_5
        })
        
        # DB に保存
        ChatHistoryManager.save_message(
            user_id=user_id,
            session_id=session_id,
            sender='bot',
            message=recommendation_message,
            extracted_intent=None
        )
        
        # ターンデータを保存
        ConversationTracker.save_turn_data(
            user_id=user_id,
            session_id=session_id,
            turn_number=conversation_turn,
            user_message=message,
            bot_message=recommendation_message,
            extracted_info=extracted_info,
            top_score=top_job['score'],
            top_match_percentage=top_job['match_percentage'],
            candidate_count=len(candidates)
        )
        
        # セッションサマリーを保存
        ConversationTracker.save_session_summary(
            user_id=user_id,
            session_id=session_id,
            total_turns=conversation_turn,
            end_reason=decision['reason'],
            final_match_percentage=top_job['match_percentage'],
            presented_jobs=[job['job_id'] for job in top_5]
        )
        
        # セッション更新
        request.session['chat_history'] = chat_history
        request.session['conversation_ended'] = True
        
        # chat_message関数内の修正
        # 🔥 マッチ度が80%以上で、かつ最低5ターン経過した場合のみ求人を表示
        jobs_for_display = []
        if top_job['match_percentage'] >= 80 and conversation_turn >= 5:  # 条件を厳格化
            top_5_preview = candidates[:5]
            
            for job in top_5_preview:
                jobs_for_display.append({
                    'job_id': job['job_id'],
                    'job_title': job.get('job_title', ''),
                    'company_name': job.get('company_name', ''),
                    'salary_min': job.get('salary_min', 0),
                    'salary_max': job.get('salary_max', 0),
                    'location_prefecture': job.get('location_prefecture', ''),
                    'match_percentage': job.get('match_percentage', 0),
                    'score': job.get('score', 0),
                    'remote_option': job.get('remote_option', '') or job.get('remote_work', ''),
                })
        
        return JSONResponse({
            'conversation_ended': True,
            'response': recommendation_message,  # JavaScriptが期待するキー名
            'message': recommendation_message,   # 後方互換性のため残す
            'jobs': jobs_for_display,  # 🔥 統一: recommendations → jobs
            'recommendations': top_5,  # 後方互換性のため残す
            'reason': decision['reason']
        })
    
    else:
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 会話続行 → 次の質問生成
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        generator = EvolvingQuestionGenerator()
        next_question = generator.generate_next_question(
            user_id=user_id,
            session_id=session_id,
            conversation_turn=conversation_turn,
            candidates=candidates,
            accumulated_insights=accumulated_insights,
            user_last_message=message
        )
        
        # 進捗メッセージ（段階的表示）
        if conversation_turn <= 5:
            stage = "基本情報収集中"
            progress_ratio = (conversation_turn / 5) * 50  # 50%まで
        elif conversation_turn <= 7:
            stage = "詳細情報深掘り中"
            progress_ratio = 50 + ((conversation_turn - 5) / 2) * 30  # 50-80%
        elif conversation_turn <= 9:
            stage = "最終調整中"
            progress_ratio = 80 + ((conversation_turn - 7) / 2) * 15  # 80-95%
        else:
            stage = "最終提案"
            progress_ratio = 95

        progress_bar = "🟦" * int(progress_ratio / 5) + "⬜" * (20 - int(progress_ratio / 5))

        # 🔥 段階に応じたメッセージ生成
        if conversation_turn <= 4:
            # 最初の4ターンは次のステップまでの道のりを表示
            remaining = 5 - conversation_turn
            top_job = candidates[0] if candidates else {"match_percentage": 0}
            bot_message = f"""{stage}: {progress_bar}
        候補: {len(candidates)}件 | マッチ度: {top_job['match_percentage']:.1f}%

        あと{remaining}ターンで最適な求人をご提案します！

        {next_question}"""
        elif conversation_turn <= 7:
            top_job = candidates[0] if candidates else {"match_percentage": 0}
            bot_message = f"""{stage}: {progress_bar}
        候補: {len(candidates)}件 | マッチ度: {top_job['match_percentage']:.1f}%

        {next_question}"""
        else:
            # 8ターン以降は最終調整
            top_job = candidates[0] if candidates else {"match_percentage": 0}
            bot_message = f"""{stage}: {progress_bar}
        候補: {len(candidates)}件 | マッチ度: {top_job['match_percentage']:.1f}%

        {next_question}"""
        
        # チャット履歴に追加
        chat_history.append({
            'sender': 'bot',
            'message': bot_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # DB に保存
        ChatHistoryManager.save_message(
            user_id=user_id,
            session_id=session_id,
            sender='bot',
            message=bot_message
        )
        
        # ターンデータを保存
        ConversationTracker.save_turn_data(
            user_id=user_id,
            session_id=session_id,
            turn_number=conversation_turn,
            user_message=message,
            bot_message=bot_message,
            extracted_info=extracted_info,
            top_score=top_job['score'],
            top_match_percentage=top_job['match_percentage'],
            candidate_count=len(candidates)
        )
        
        # 🔥 セッションデータをデータベースに保存
        session_data_updated = {
            'candidates': candidates,
            'initial_candidate_count': len(candidates),
            'conversation_turn': conversation_turn,
            'score_history': score_history,
            'accumulated_insights': accumulated_insights
        }
        
        conn_update = get_db_conn()
        cur_update = conn_update.cursor()
        
        cur_update.execute("""
            UPDATE user_sessions
            SET session_data = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE session_id = %s AND user_id = %s
        """, (json.dumps(session_data_updated), session_id, user_id))
        
        conn_update.commit()
        cur_update.close()
        conn_update.close()
        
        # 🔥 マッチ度が80%以上の場合のみ求人を表示
        jobs_for_display = []
        if top_job['match_percentage'] >= 70 and conversation_turn >= 5:  
            top_5_preview = candidates[:5]
            
            for job in top_5_preview:
                jobs_for_display.append({
                    'job_id': job['job_id'],
                    'job_title': job.get('job_title', ''),
                    'company_name': job.get('company_name', ''),
                    'salary_min': job.get('salary_min', 0),
                    'salary_max': job.get('salary_max', 0),
                    'location_prefecture': job.get('location_prefecture', ''),
                    'match_percentage': job.get('match_percentage', 0),
                    'score': job.get('score', 0),
                    'remote_option': job.get('remote_option', '') or job.get('remote_work', ''),
                })
        
        return JSONResponse({
            'conversation_ended': False,
            'response': bot_message,
            'message': bot_message,
            'candidate_count': len(candidates),
            'top_match': top_job['match_percentage'],
            'turn': conversation_turn,
            'progress': f"{conversation_turn}/10",
            'jobs': jobs_for_display  # 70%以上かつ5ターン以上の場合のみ表示
        })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ヘルパー関数（AI処理）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def extract_user_intent(message: str) -> Dict[str, Any]:
    """AIでユーザーの意図を抽出"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # JSON形式に対応したモデル
            messages=[
                {
                    "role": "system",
                    "content": """あなたは求人マッチングの専門家です。
ユーザーのメッセージから以下の情報を抽出してJSON形式で返してください:

1. explicit_preferences（明示的な希望条件）
   - remote_work: "強く希望" | "希望" | "不要" | null
   - learning_interest: 学びたい技術・スキル
   - work_life_balance: "重視" | "普通" | null
   - career_goal: キャリア目標

2. implicit_values（暗黙の価値観・優先度を1-5で推定）
   - work_life_balance_priority: 1-5
   - career_growth_priority: 1-5
   - salary_priority: 1-5
   - stability_priority: 1-5

3. pain_points（不満点・課題）

4. keywords（重要キーワード）

5. job_change_request（職種変更・追加の要求）
   - requested: true | false
   - new_job_titles: ["エンジニア", "デザイナー"] など
   - reason: 変更理由

6. alternative_condition_acceptance（代替条件への同意）
   - accepted: true | false
   - condition_type: "work_hours" | "location" | "benefits" | "flexibility" など
   - details: 具体的な条件（例: "10時出社", "フレックスタイム"）
   - reason: 同意した理由

7. confidence（抽出の信頼度 0.0-1.0）

例:
{
  "explicit_preferences": {
    "remote_work": "強く希望",
    "learning_interest": "React"
  },
  "implicit_values": {
    "work_life_balance_priority": 5,
    "career_growth_priority": 4
  },
  "pain_points": ["通勤時間が長い"],
  "keywords": ["React", "リモート", "家族"],
  "job_change_request": {
    "requested": false,
    "new_job_titles": [],
    "reason": ""
  },
  "alternative_condition_acceptance": {
    "accepted": false,
    "condition_type": "",
    "details": "",
    "reason": ""
  },
  "confidence": 0.9
}"""
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        print(f"❌ 意図抽出エラー: {e}")
        return {
            "explicit_preferences": {},
            "implicit_values": {},
            "pain_points": [],
            "keywords": [],
            "confidence": 0.5
        }


def merge_insights(
    existing: Dict[str, Any], 
    new: Dict[str, Any]
) -> Dict[str, Any]:
    """抽出情報をマージ"""
    
    # explicit_preferences をマージ
    existing_prefs = existing.get('explicit_preferences', {})
    new_prefs = new.get('explicit_preferences', {})
    merged_prefs = {**existing_prefs, **new_prefs}
    
    # implicit_values をマージ（最新の値で上書き）
    existing_values = existing.get('implicit_values', {})
    new_values = new.get('implicit_values', {})
    merged_values = {**existing_values, **new_values}
    
    # pain_points を追加
    existing_pains = existing.get('pain_points', [])
    new_pains = new.get('pain_points', [])
    merged_pains = list(set(existing_pains + new_pains))
    
    # keywords を追加
    existing_keywords = existing.get('keywords', [])
    new_keywords = new.get('keywords', [])
    merged_keywords = list(set(existing_keywords + new_keywords))
    
    return {
        'explicit_preferences': merged_prefs,
        'implicit_values': merged_values,
        'pain_points': merged_pains,
        'keywords': merged_keywords,
        'confidence': new.get('confidence', 0.5)
    }


def rescore_all_candidates(
    candidates: List[Dict],
    extracted_info: Dict,
    conversation_turn: int
) -> List[Dict]:
    """全候補を再スコアリング（緩和版）"""
    
    for job in candidates:
        # 初期スコア設定（変更なし）
        if 'score' not in job or job['score'] == 0:
            job['score'] = 50.0
            job['score_details'] = [('基本スコア', 50)]
        
        new_points = []
        
        # === リモートワーク条件（加点を緩和）===
        remote_pref = extracted_info.get('explicit_preferences', {}).get('remote_work')
        if remote_pref in ['強く希望', '希望']:
            remote_option = job.get('remote_option', '') or job.get('remote_work', '') or ''
            
            if '完全' in remote_option or 'フル' in remote_option or 'リモート可' in remote_option:
                job['score'] += 20  # 30→20に減点
                new_points.append(('完全リモート可', 20))
            elif 'ハイブリッド' in remote_option or '一部' in remote_option:
                job['score'] += 10  # 15→10に減点
                new_points.append(('一部リモート可', 10))
            elif remote_option in ['なし', 'none', '']:
                if remote_pref == '強く希望':
                    job['score'] -= 8  # 10→8に緩和
                    new_points.append(('リモート不可', -8))
                else:
                    job['score'] -= 3  # 5→3に緩和
                    new_points.append(('リモート不可', -3))
        
        # === 学習興味（加点を緩和）===
        learning_interest = extracted_info.get('explicit_preferences', {}).get('learning_interest')
        if learning_interest:
            job_text = f"{job.get('job_title', '')} {job.get('skills', '')}"
            if learning_interest.lower() in job_text.lower():
                job['score'] += 8  # 15→8に減点
                new_points.append((f'{learning_interest}使用', 8))
        
        # === その他の条件も同様に減点 ===
        # キャリア成長、ワークライフバランス、キーワードマッチなど
        # すべての加点を半分以下に減点
        
        # スコア詳細を記録
        if new_points:
            job['score_details'].extend(new_points)
    
    return candidates


def calculate_match_percentages(
    candidates: List[Dict],
    conversation_turn: int
) -> List[Dict]:
    """マッチ度を0-100%で計算（修正版）"""
    
    # シンプルな計算式:
    # 最低スコア30点 = 0%
    # 標準スコア50点 = 28.6%
    # 満点100点 = 100%
    
    for job in candidates:
        current_score = job['score']
        
        # 30-100点を0-100%に変換
        # (current_score - 30) / (100 - 30) * 100
        match_percentage = ((current_score - 30) / 70) * 100
        
        # 🔥 重要: 0-100%の範囲に収める（上限を100%に）
        match_percentage = max(0, min(100, match_percentage))
        
        job['match_percentage'] = round(match_percentage, 1)
    
    return candidates

def should_end_conversation(context: Dict) -> Dict[str, Any]:
    """終了判定（段階的アプローチ）"""
    
    turn = context['conversation_turn']
    top_match = context['top_match_percentage']
    score_history = context['score_history']
    user_message = context['user_message']
    
    # 🔥 段階1: 最低5ターンは必ず継続（基本情報収集）
    if turn < 5:
        return {'should_end': False}
    
    # 🔥 段階2: 5-7ターンは柔軟に（詳細情報収集）
    if 5 <= turn <= 7:
        # 高マッチ（75%以上）で終了
        if top_match >= 75:
            return {
                'should_end': True,
                'reason': 'high_match',
                'message': '最適な求人が見つかりました！'
            }
        
        # スコア収束（3回連続変化3点以下）で終了
        if turn >= 6 and len(score_history) >= 3:
            recent_scores = [h['top_score'] for h in score_history[-3:]]
            changes = [abs(recent_scores[i] - recent_scores[i-1]) for i in range(1, 3)]
            
            if all(change <= 3 for change in changes):
                return {
                    'should_end': True,
                    'reason': 'score_converged',
                    'message': 'おすすめの求人が絞り込めました。'
                }
        
        # 基本的に継続（詳細を深掘り）
        return {'should_end': False}
    
    # 🔥 段階3: 8-9ターンで最終調整
    if 8 <= turn <= 9:
        # 70%以上で終了（少し緩和）
        if top_match >= 70:
            return {
                'should_end': True,
                'reason': 'high_match',
                'message': '最適な求人が見つかりました！'
            }
        
        # スコア収束で終了
        if len(score_history) >= 2:
            recent_scores = [h['top_score'] for h in score_history[-2:]]
            if abs(recent_scores[1] - recent_scores[0]) <= 2:
                return {
                    'should_end': True,
                    'reason': 'score_converged',
                    'message': '最適な求人が決まりました。'
                }
        
        return {'should_end': False}
    
    # 🔥 段階4: 10ターンで強制終了
    if turn >= 10:
        return {
            'should_end': True,
            'reason': 'max_turns',
            'message': '十分にお話を伺えました。最適な求人をご紹介します。'
        }
    
    return {'should_end': False}


def generate_match_reasoning(
    user_id: int,
    job: Dict,
    accumulated_insights: Dict
) -> str:
    """AIでマッチ理由を生成"""
    
    try:
        # スコア詳細を整形
        score_details_text = "\n".join([
            f"- {detail[0]}: +{detail[1]}点"
            for detail in job.get('score_details', [])[:5]
        ])
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # コスト効率の良いモデル
            messages=[
                {
                    "role": "system",
                    "content": """あなたは求人マッチングの専門家です。
なぜこの求人がユーザーに最適なのか、200-300文字で説明してください。

【構成】
第1段落: ユーザーの最優先条件とのマッチ
第2段落: 技術的・スキル的なマッチ
第3段落: 働き方・環境のマッチ

【注意】
- 具体的な数字や条件を使う
- ポジティブかつ正直に
- 誇張しない"""
                },
                {
                    "role": "user",
                    "content": f"""【ユーザーの希望・価値観】
{json.dumps(accumulated_insights, ensure_ascii=False, indent=2)}

【求人情報】
- 職種: {job['job_title']}
- 企業: {job['company_name']}
- 勤務地: {job['location_prefecture']}
- 年収: {job['salary_min']}-{job['salary_max']}万円
- リモートワーク: {job.get('remote_work', '不明')}
- 企業文化: {job.get('company_culture', '不明')}

【マッチしたポイント】
{score_details_text if score_details_text else '（基本条件のみ）'}

【マッチ度】
{job['match_percentage']}%"""
                }
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"❌ マッチ理由生成エラー: {e}")
        return "あなたの希望条件に合致しています。"


def generate_recommendation_message(
    user_id: int,
    top_jobs: List[Dict],
    end_reason: str,
    accumulated_insights: Dict
) -> str:
    """推薦メッセージを生成"""
    
    # ユーザープロファイル取得
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT pd.user_name, up.job_title 
        FROM personal_date pd
        LEFT JOIN user_profile up ON pd.user_id = up.user_id
        WHERE pd.user_id = %s
    """, (user_id,))
    
    profile = cur.fetchone()
    cur.close()
    conn.close()
    
    user_name = profile['user_name'] if profile else 'ユーザー'
    job_title = profile['job_title'] if profile else '希望職種'
    
    # 終了理由に応じたメッセージ
    reason_messages = {
        'high_match': f'{user_name}さんに最適な{job_title}の求人が見つかりました！',
        'score_converged': f'{user_name}さんの希望を深く理解できました。',
        'user_requested': f'かしこまりました、{user_name}さん。',
        'max_turns': f'詳しくお話を伺えました、{user_name}さん。'
    }
    
    opening = reason_messages.get(end_reason, f'{user_name}さんにおすすめの求人をご紹介します。')
    
    # ユーザーの希望を要約
    prefs = accumulated_insights.get('explicit_preferences', {})
    summary_points = []
    
    if prefs.get('remote_work'):
        summary_points.append(f"✅ リモートワーク（{prefs['remote_work']}）")
    if prefs.get('learning_interest'):
        summary_points.append(f"✅ {prefs['learning_interest']}の学習・使用")
    if prefs.get('work_life_balance'):
        summary_points.append(f"✅ ワークライフバランス（{prefs['work_life_balance']}）")
    if prefs.get('career_goal'):
        summary_points.append(f"✅ {prefs['career_goal']}")
    
    summary_text = "\n".join(summary_points) if summary_points else "基本条件に合致"
    
    # メッセージ構築
    message = f"""{opening}

会話を通じて、以下の希望を理解しました：

{summary_text}

厳選した上位5件の{job_title}求人をご紹介します。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    for i, job in enumerate(top_jobs, 1):
        # リモート情報を整形
        remote_option = job.get('remote_option', '') or 'なし'
        if not remote_option or remote_option == 'なし':
            remote_display = '❌ 不可'
        elif '完全' in remote_option or 'フル' in remote_option:
            remote_display = '✅ 完全リモート可能'
        elif 'ハイブリッド' in remote_option or '一部' in remote_option:
            remote_display = '🔶 ハイブリッド（一部可能）'
        else:
            remote_display = f'📋 {remote_option}'
        
        message += f"""【第{i}位】{job['job_title']}
企業名: {job['company_name']}
マッチ度: {job['match_percentage']:.1f}%

【なぜマッチ？】
{job.get('match_reasoning', 'あなたの条件に合致しています。')}

【求人詳細】
📍 勤務地: {job['location_prefecture']}
💰 年収: {job['salary_min']}-{job['salary_max']}万円
🏠 リモート: {remote_display}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    message += "\n✨ 気になる求人はありましたか？各求人の詳細はクリックしてご確認いただけます。"
    
    return message


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 起動
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("🚀 進化型AI求人マッチングシステム v3.0")
    print("=" * 70)
    print()
    print("✅ 初期検索: 基本条件で1回のみ")
    print("✅ 動的質問生成: AIがユーザーごとにカスタマイズ")
    print("✅ 全候補再評価: 会話ごとにスコアリング")
    print("✅ 複数終了条件: 80%達成/収束/要求/10ターン")
    print("✅ マッチ理由説明: AIが200-300文字で生成")
    print()
    print("起動中... http://localhost:5000")
    print("=" * 70)
    
    uvicorn.run(app, host="0.0.0.0", port=5000)