"""
企業関連APIルーター
- 企業情報取得・更新
"""

from fastapi import APIRouter, HTTPException, status
from psycopg2.extras import RealDictCursor

from db_config import get_db_conn

router = APIRouter()


@router.get("/{company_id}")
async def get_company_info(company_id: str):
    """
    企業情報取得
    
    指定した企業の基本情報を取得します（パスワードは除く）。
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, company_id, email, company_name, address,
                   phone_number, website_url, created_at, updated_at
            FROM company_date
            WHERE company_id = %s
        """, (company_id,))
        
        company = cur.fetchone()
        cur.close()
        conn.close()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="企業が見つかりません"
            )
        
        return dict(company)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"企業情報取得エラー: {str(e)}"
        )


@router.get("/{company_id}/jobs/count")
async def get_company_jobs_count(company_id: str):
    """
    企業の求人数取得
    
    指定した企業が登録している求人の総数を返します。
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT COUNT(*) FROM company_profile
            WHERE company_id = %s
        """, (company_id,))
        
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        return {
            "company_id": company_id,
            "job_count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"求人数取得エラー: {str(e)}"
        )