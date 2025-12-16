"""
求人関連APIルーター
- 求人登録・取得・一覧・検索
"""

from fastapi import APIRouter, HTTPException, status, Query
from psycopg2.extras import RealDictCursor
from openai import OpenAI
import uuid
import os
from typing import Optional, List

from models.api_models import (
    JobCreateRequest,
    JobResponse,
    JobListResponse,
)
from db_config import get_db_conn

router = APIRouter()

# OpenAI クライアントの初期化
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embedding(text: str) -> list[float]:
    """テキストのエンベディングを生成"""
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(company_id: str, request: JobCreateRequest):
    """
    求人登録
    
    新しい求人情報を登録し、エンベディングを自動生成します。
    """
    try:
        # intent_labelsを生成
        labels = []
        if request.bonus:
            labels.append(request.bonus)
        if request.overtime:
            labels.append(request.overtime)
        if request.workplace_atmosphere:
            labels.append(request.workplace_atmosphere)
        intent_labels = ",".join(labels) if labels else None
        
        # エンベディング用のテキストを生成
        profile_text = " ".join([
            request.job_title,
            str(request.salary_min),
            str(request.salary_max),
            intent_labels or ""
        ])
        
        # エンベディングを生成
        embedding = get_embedding(profile_text)
        
        # UUIDを生成
        job_id = str(uuid.uuid4())
        
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 求人を登録
        cur.execute("""
            INSERT INTO company_profile (
                id, company_id, job_title, salary_min, salary_max,
                location_prefecture, intent_labels, embedding,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, company_id, job_title, salary_min, salary_max,
                      location_prefecture, intent_labels, click_count, 
                      favorite_count, apply_count, view_count,
                      created_at, updated_at
        """, (
            job_id,
            company_id,
            request.job_title,
            request.salary_min,
            request.salary_max,
            request.location_prefecture,
            intent_labels,
            embedding,
        ))
        
        job = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return JobResponse(**dict(job))
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"求人登録エラー: {str(e)}"
        )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    求人詳細取得
    
    指定した求人の詳細情報を取得します。
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT cp.id, cp.company_id, cp.job_title, cp.salary_min, cp.salary_max,
                   cp.location_prefecture, cp.intent_labels, cp.click_count,
                   cp.favorite_count, cp.apply_count, cp.view_count,
                   cp.created_at, cp.updated_at, cd.company_name
            FROM company_profile cp
            LEFT JOIN company_date cd ON cp.company_id = cd.company_id
            WHERE cp.id = %s
        """, (job_id,))
        
        job = cur.fetchone()
        cur.close()
        conn.close()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="求人が見つかりません"
            )
        
        return JobResponse(**dict(job))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"求人取得エラー: {str(e)}"
        )


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    company_id: Optional[str] = Query(None, description="企業IDでフィルタ"),
    location: Optional[str] = Query(None, description="勤務地でフィルタ"),
    salary_min: Optional[int] = Query(None, ge=0, description="最低年収でフィルタ"),
):
    """
    求人一覧取得
    
    求人一覧をページネーション付きで取得します。
    各種フィルタ条件を指定できます。
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # WHERE句を動的に構築
        where_clauses = []
        params = []
        
        if company_id:
            where_clauses.append("cp.company_id = %s")
            params.append(company_id)
        
        if location:
            where_clauses.append("cp.location_prefecture = %s")
            params.append(location)
        
        if salary_min is not None:
            where_clauses.append("cp.salary_min >= %s")
            params.append(salary_min)
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # 総件数を取得
        count_query = f"SELECT COUNT(*) FROM company_profile cp {where_sql}"
        cur.execute(count_query, params)
        total = cur.fetchone()['count']
        
        # ページネーション用のOFFSETとLIMITを計算
        offset = (page - 1) * page_size
        params.extend([page_size, offset])
        
        # 求人一覧を取得
        list_query = f"""
            SELECT cp.id, cp.company_id, cp.job_title, cp.salary_min, cp.salary_max,
                   cp.location_prefecture, cp.intent_labels, cp.click_count,
                   cp.favorite_count, cp.apply_count, cp.view_count,
                   cp.created_at, cp.updated_at, cd.company_name
            FROM company_profile cp
            LEFT JOIN company_date cd ON cp.company_id = cd.company_id
            {where_sql}
            ORDER BY cp.created_at DESC
            LIMIT %s OFFSET %s
        """
        
        cur.execute(list_query, params)
        jobs = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return JobListResponse(
            jobs=[JobResponse(**dict(job)) for job in jobs],
            total=total,
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"求人一覧取得エラー: {str(e)}"
        )


@router.delete("/{job_id}")
async def delete_job(job_id: str, company_id: str):
    """
    求人削除
    
    指定した求人を削除します。
    企業IDによる権限チェックを行います。
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        
        # 求人の存在と企業IDの確認
        cur.execute("""
            SELECT company_id FROM company_profile
            WHERE id = %s
        """, (job_id,))
        
        job = cur.fetchone()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="求人が見つかりません"
            )
        
        if job[0] != company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この求人を削除する権限がありません"
            )
        
        # 求人を削除
        cur.execute("DELETE FROM company_profile WHERE id = %s", (job_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"message": "求人を削除しました", "job_id": job_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"求人削除エラー: {str(e)}"
        )