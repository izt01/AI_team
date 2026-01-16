"""
ユーザー向けAPIエンドポイント
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime

from config.database import get_db_conn
from schemas.user import UserRegister, UserLogin, UserProfile, UserProfileUpdate, Token
from schemas.matching import ChatMessage, ChatResponse, RecommendationRequest, RecommendationResponse
from services.auth_service import get_password_hash, verify_password, create_access_token, get_current_user
from services.conversation_service import ConversationService
from services.matching_service import MatchingService
from utils.helpers import clean_dict_for_json

router = APIRouter(prefix="/api/user", tags=["User"])


@router.post("/register", response_model=Token)
async def register(user_data: UserRegister):
    """ユーザー登録"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # メールアドレス重複チェック
    cur.execute("SELECT user_id FROM personal_date WHERE email = %s", (user_data.email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスは既に登録されています"
        )
    
    # ユーザー作成（user_idはSERIALで自動採番）
    hashed_password = get_password_hash(user_data.password)
    
    cur.execute("""
        INSERT INTO personal_date 
        (name, email, password, age, gender, phone, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING user_id
    """, (
        user_data.name,
        user_data.email,
        hashed_password,
        user_data.age,
        user_data.gender,
        user_data.location,
        datetime.now(),
        datetime.now()
    ))
    
    result = cur.fetchone()
    user_id = result['user_id']
    
    conn.commit()
    cur.close()
    conn.close()
    
    # トークン生成
    access_token = create_access_token(data={"sub": str(user_id), "type": "user"})
    
    return Token(access_token=access_token, user_id=str(user_id))


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin):
    """ログイン"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT user_id, password
        FROM personal_date
        WHERE email = %s
    """, (login_data.email,))
    
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if not user or not verify_password(login_data.password, user['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません"
        )
    
    # トークン生成
    access_token = create_access_token(data={"sub": user['user_id'], "type": "user"})
    
    return Token(access_token=access_token, user_id=user['user_id'])


@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: str = Depends(get_current_user)):
    """プロフィール取得"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT user_id, name, email, age, gender, location, created_at, updated_at
        FROM personal_date
        WHERE user_id = %s
    """, (current_user,))
    
    user = cur.fetchone()
    
    if not user:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    # プリファレンス取得
    cur.execute("""
        SELECT preferences
        FROM user_preferences_profile
        WHERE user_id = %s
    """, (current_user,))
    
    pref_row = cur.fetchone()
    cur.close()
    conn.close()
    
    user_dict = dict(user)
    user_dict['preferences'] = pref_row['preferences'] if pref_row else None
    
    return UserProfile(**clean_dict_for_json(user_dict))


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: str = Depends(get_current_user)
):
    """プロフィール更新"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 更新フィールドを構築
    update_fields = []
    params = []
    
    if profile_data.name is not None:
        update_fields.append("name = %s")
        params.append(profile_data.name)
    
    if profile_data.age is not None:
        update_fields.append("age = %s")
        params.append(profile_data.age)
    
    if profile_data.gender is not None:
        update_fields.append("gender = %s")
        params.append(profile_data.gender)
    
    if profile_data.location is not None:
        update_fields.append("location = %s")
        params.append(profile_data.location)
    
    if not update_fields:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="更新するデータがありません")
    
    update_fields.append("updated_at = %s")
    params.append(datetime.now())
    params.append(current_user)
    
    query = f"""
        UPDATE personal_date
        SET {', '.join(update_fields)}
        WHERE user_id = %s
        RETURNING user_id, name, email, age, gender, location, created_at, updated_at
    """
    
    cur.execute(query, tuple(params))
    updated_user = cur.fetchone()
    
    conn.commit()
    cur.close()
    conn.close()
    
    return UserProfile(**clean_dict_for_json(dict(updated_user)))


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    message_data: ChatMessage
):
    """
    チャット（新しいAI質問生成システム）
    
    - 動的質問生成（OpenAI API）
    - 毎ターンスコアリング
    - 3つの求人提示トリガー（スコア80%、ユーザーリクエスト、10ターン）
    - 深掘り質問制御（2回連続防止）
    """
    from services.auth_service import get_current_user_from_cookie
    from services.chat_service import ChatService
    
    # Cookie認証
    current_user = await get_current_user_from_cookie(request)
    
    try:
        chat_service = ChatService()
        session_id = message_data.context.get("session_id") if message_data.context else None
        
        print(f"🔍 受信データ:")
        print(f"   メッセージ: {message_data.message}")
        print(f"   context: {message_data.context}")
        print(f"   session_id: {session_id}")
        
        # 初回接続
        if not session_id or message_data.message in ['初回接続', '']:
            print("📢 初回チャット開始")
            result = chat_service.start_chat(current_user)
        else:
            # 通常の会話処理
            print(f"💬 チャット処理: session={session_id[:8]}...")
            result = chat_service.process_message(
                user_id=current_user,
                user_message=message_data.message,
                session_id=session_id
            )
        
        # レスポンス構築
        recommendations = None
        if result.jobs:
            recommendations = [
                {
                    "job_id": job.job_id,
                    "job_title": job.job_title,
                    "company_name": job.company_name,
                    "match_score": job.match_score,
                    "match_percentage": round(job.match_score, 1),  # HTMLで使用
                    "match_reasoning": job.match_reasoning,
                    "matched_features": [job.match_reasoning],
                    "salary_min": job.salary_min,
                    "salary_max": job.salary_max,
                    "location": job.location,
                    "location_prefecture": job.location,
                    "remote_option": job.remote_option,
                    "id": job.job_id  # HTMLとの互換性
                }
                for job in result.jobs
            ]
        
        return ChatResponse(
            ai_message=result.ai_message,
            recommendations=recommendations,
            conversation_id=result.session_id,
            turn_number=result.turn_count,
            current_score=result.current_score  # スコアを追加
        )
        
    except Exception as e:
        print(f"❌ チャットエラー: {e}")
        import traceback
        traceback.print_exc()
        
        # フォールバック: 古いシステムを使用
        print("⚠️ 新システムエラー、フォールバックに切り替え")
        
        session_id = message_data.context.get("session_id") if message_data.context else None
        
        # 初回接続の場合
        if message_data.message == '初回接続' or not message_data.message.strip():
            return ChatResponse(
                ai_message="こんにちは！あなたにぴったりの求人を見つけるお手伝いをします。\n\nまず、どのような職種に興味がありますか？（例：Webデザイナー、エンジニア、営業など）",
                recommendations=None,
                conversation_id=session_id or "new_session",
                turn_number=1
            )
        
        # 会話処理
        result = ConversationService.process_user_message(
            user_id=current_user,
            message=message_data.message,
            session_id=session_id
        )
        
        # おすすめ求人取得
        recommendations = None
        if result.get("extracted_intent"):
            scored_jobs = MatchingService.score_jobs_for_user(
                user_id=current_user,
                user_intent=result["extracted_intent"],
                accumulated_insights={},
                limit=5,
                use_ai=False
            )
            
            recommendations = [
                {
                    "id": str(job["id"]),
                    "job_title": job["job_title"],
                    "company_name": job.get("company_name"),
                    "match_score": job["match_score"],
                    "matched_features": job.get("matched_features", [])
                }
                for job in scored_jobs[:5]
            ]
        
        return ChatResponse(
            ai_message=result["ai_message"],
            recommendations=recommendations,
            conversation_id=result["session_id"],
            turn_number=result["turn_number"]
        )


@router.get("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    limit: int = 10,
    min_score: int = 60,
    current_user: str = Depends(get_current_user)
):
    """おすすめ求人取得"""
    
    result = MatchingService.get_recommendations(
        user_id=current_user,
        limit=limit,
        min_score=min_score
    )
    
    return RecommendationResponse(**result)