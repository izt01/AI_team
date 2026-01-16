"""
企業向けAPIエンドポイント
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from psycopg2.extras import RealDictCursor, Json
import uuid
from datetime import datetime

from config.database import get_db_conn
from schemas.company import (
    CompanyRegister, CompanyLogin, CompanyProfile, 
    ScoutSearchRequest, ScoutSearchResponse, ScoutMessageRequest, ScoutMessageResponse
)
from schemas.job import JobCreate, JobUpdate, JobResponse, JobSearchRequest, JobSearchResponse
from schemas.user import Token
from services.auth_service import get_password_hash, verify_password, create_access_token, get_current_company
from services.matching_service import MatchingService
from utils.helpers import clean_dict_for_json

router = APIRouter(prefix="/api/company", tags=["Company"])


@router.post("/register", response_model=Token)
async def register(company_data: CompanyRegister):
    """企業登録"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # メールアドレス重複チェック
    cur.execute("SELECT company_id FROM company_date WHERE email = %s", (company_data.email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスは既に登録されています"
        )
    
    # 企業作成（company_idはUUIDで自動生成）
    hashed_password = get_password_hash(company_data.password)
    
    cur.execute("""
        INSERT INTO company_date 
        (company_name, email, password, industry, company_size, website_url, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING company_id
    """, (
        company_data.company_name,
        company_data.email,
        hashed_password,
        company_data.industry,
        company_data.company_size,
        company_data.website,
        datetime.now(),
        datetime.now()
    ))
    
    result = cur.fetchone()
    company_id = str(result['company_id'])
    
    conn.commit()
    cur.close()
    conn.close()
    
    # トークン生成
    access_token = create_access_token(data={"sub": company_id, "type": "company"})
    
    return Token(access_token=access_token, user_id=company_id)


@router.post("/login", response_model=Token)
async def login(login_data: CompanyLogin):
    """ログイン"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT company_id, password
        FROM company_date
        WHERE email = %s
    """, (login_data.email,))
    
    company = cur.fetchone()
    cur.close()
    conn.close()
    
    if not company or not verify_password(login_data.password, company['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません"
        )
    
    # トークン生成
    access_token = create_access_token(data={"sub": company['company_id'], "type": "company"})
    
    return Token(access_token=access_token, user_id=company['company_id'])


@router.get("/profile", response_model=CompanyProfile)
async def get_profile(current_company: str = Depends(get_current_company)):
    """企業プロフィール取得"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT company_id, company_name, email, industry, company_size, website, created_at, updated_at
        FROM company_date
        WHERE company_id = %s
    """, (current_company,))
    
    company = cur.fetchone()
    cur.close()
    conn.close()
    
    if not company:
        raise HTTPException(status_code=404, detail="企業が見つかりません")
    
    return CompanyProfile(**clean_dict_for_json(dict(company)))


@router.post("/jobs", response_model=JobResponse)
async def create_job(
    job_data: JobCreate,
    current_company: str = Depends(get_current_company)
):
    """求人作成"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 企業名取得
    cur.execute("SELECT company_name FROM company_date WHERE company_id = %s", (current_company,))
    company = cur.fetchone()
    
    if not company:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="企業が見つかりません")
    
    # 求人作成（idはUUIDで自動生成）
    cur.execute("""
        INSERT INTO company_profile
        (company_id, job_title, job_description, employment_type,
         location_prefecture, location_city, salary_min, salary_max, required_skills,
         benefits, remote_option, flex_time, side_job_allowed, work_style_details,
         team_culture_details, growth_opportunities_details, additional_questions,
         status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (
        current_company,
        job_data.job_title,
        job_data.job_description,
        job_data.employment_type,
        job_data.location_prefecture,
        job_data.location_city,
        job_data.salary_min,
        job_data.salary_max,
        job_data.required_skills,
        job_data.benefits,
        job_data.remote_option,
        job_data.flex_time,
        job_data.side_job_allowed,
        job_data.work_style_details,
        job_data.team_culture_details,
        job_data.growth_opportunities_details,
        Json(job_data.additional_questions) if job_data.additional_questions else None,
        'active',
        datetime.now(),
        datetime.now()
    ))
    
    new_job = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    # company_nameを追加
    job_dict = dict(new_job)
    job_dict['company_name'] = company['company_name']
    
    return JobResponse(**clean_dict_for_json(job_dict))


@router.get("/jobs", response_model=List[JobResponse])
async def get_jobs(
    status_filter: str = None,
    current_company: str = Depends(get_current_company)
):
    """求人一覧取得"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = "SELECT * FROM company_profile WHERE company_id = %s"
    params = [current_company]
    
    if status_filter:
        query += " AND status = %s"
        params.append(status_filter)
    
    query += " ORDER BY created_at DESC"
    
    cur.execute(query, tuple(params))
    jobs = cur.fetchall()
    cur.close()
    conn.close()
    
    return [JobResponse(**clean_dict_for_json(dict(job))) for job in jobs]


@router.put("/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_data: JobUpdate,
    current_company: str = Depends(get_current_company)
):
    """求人更新"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 権限確認
    cur.execute("""
        SELECT * FROM company_profile
        WHERE id = %s AND company_id = %s
    """, (job_id, current_company))
    
    existing_job = cur.fetchone()
    
    if not existing_job:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="求人が見つかりません")
    
    # 更新フィールドを構築
    update_fields = []
    params = []
    
    for field, value in job_data.dict(exclude_unset=True).items():
        if value is not None:
            update_fields.append(f"{field} = %s")
            params.append(value)
    
    if not update_fields:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="更新するデータがありません")
    
    update_fields.append("updated_at = %s")
    params.append(datetime.now())
    params.append(job_id)
    
    query = f"""
        UPDATE company_profile
        SET {', '.join(update_fields)}
        WHERE id = %s
        RETURNING *
    """
    
    cur.execute(query, tuple(params))
    updated_job = cur.fetchone()
    
    conn.commit()
    cur.close()
    conn.close()
    
    return JobResponse(**clean_dict_for_json(dict(updated_job)))


@router.post("/scout/search", response_model=ScoutSearchResponse)
async def search_scout_candidates(
    search_data: ScoutSearchRequest,
    current_company: str = Depends(get_current_company)
):
    """スカウト候補検索"""
    
    # 簡易実装（実際はより詳細なマッチングが必要）
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 求人情報取得
    cur.execute("""
        SELECT * FROM company_profile
        WHERE id = %s AND company_id = %s
    """, (search_data.job_id, current_company))
    
    job = cur.fetchone()
    
    if not job:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="求人が見つかりません")
    
    # ユーザー取得
    cur.execute("""
        SELECT pd.user_id, pd.name, upp.preferences
        FROM personal_date pd
        LEFT JOIN user_preferences_profile upp ON pd.user_id = upp.user_id
        LIMIT 100
    """)
    
    users = cur.fetchall()
    cur.close()
    conn.close()
    
    # スコアリング（簡易版）
    from schemas.matching import ScoutCandidate
    
    candidates = []
    for user in users:
        # 仮のマッチスコア
        match_score = 75  # 実際はスコアリング関数を使用
        
        if match_score >= search_data.min_match_score:
            candidates.append({
                "user_id": user['user_id'],
                "name": user['name'],
                "match_score": match_score,
                "matched_features": ["スキルマッチ", "希望条件一致"],
                "profile_summary": f"{user['name']}さん"
            })
    
    candidates.sort(key=lambda x: x['match_score'], reverse=True)
    
    return ScoutSearchResponse(
        job_id=search_data.job_id,
        candidates=candidates[:search_data.limit],
        total_count=len(candidates)
    )


@router.post("/scout/send", response_model=ScoutMessageResponse)
async def send_scout_message(
    scout_data: ScoutMessageRequest,
    current_company: str = Depends(get_current_company)
):
    """スカウトメッセージ送信"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    scout_id = str(uuid.uuid4())
    
    cur.execute("""
        INSERT INTO scout_messages
        (scout_id, company_id, user_id, job_id, message, status, sent_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING scout_id, status, sent_at
    """, (
        scout_id,
        current_company,
        scout_data.user_id,
        scout_data.job_id,
        scout_data.message or "あなたのプロフィールを拝見し、ぜひご応募いただきたいと思いました。",
        'sent',
        datetime.now(),
        datetime.now()
    ))
    
    scout = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    return ScoutMessageResponse(**clean_dict_for_json(dict(scout)))
