"""
推薦関連APIルーター
- ハイブリッド推薦（協調フィルタリング + コンテンツベース）
- エンベディング類似度検索
"""

from fastapi import APIRouter, HTTPException, status, Query
from psycopg2.extras import RealDictCursor
from typing import Optional, List

from models.api_models import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationListResponse,
    JobResponse,
)
from db_config import get_db_conn
from hybrid_recommender import HybridRecommender

router = APIRouter()


@router.post("/hybrid", response_model=RecommendationListResponse)
async def get_hybrid_recommendations(request: RecommendationRequest):
    """
    ハイブリッド推薦
    
    協調フィルタリングとコンテンツベースフィルタリングを組み合わせた
    ハイブリッド推薦アルゴリズムで求人を推薦します。
    """
    try:
        # 推薦を取得
        recommendations = HybridRecommender.get_hybrid_recommendations(
            user_id=request.user_id,
            top_k=request.top_k,
            previous_job_ids=request.exclude_job_ids,
        )
        
        # レスポンス形式に変換
        recommendation_list = []
        for rec in recommendations:
            job_response = JobResponse(
                id=rec['id'],
                company_id=rec.get('company_id', ''),
                company_name=rec.get('company_name'),
                job_title=rec['job_title'],
                salary_min=rec['salary_min'],
                salary_max=rec['salary_max'],
                location_prefecture=rec.get('location_prefecture'),
                intent_labels=rec.get('intent_labels'),
                click_count=rec.get('click_count', 0),
                favorite_count=rec.get('favorite_count', 0),
                apply_count=rec.get('apply_count', 0),
                view_count=rec.get('view_count', 0),
                created_at=rec.get('created_at'),
                updated_at=rec.get('updated_at'),
            )
            
            recommendation_list.append(RecommendationResponse(
                job=job_response,
                score=rec.get('score', 0.0),
                match_type='hybrid'
            ))
        
        return RecommendationListResponse(
            recommendations=recommendation_list,
            total=len(recommendation_list),
            user_id=request.user_id,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推薦エラー: {str(e)}"
        )


@router.get("/collaborative/{user_id}", response_model=RecommendationListResponse)
async def get_collaborative_recommendations(
    user_id: int,
    top_k: int = Query(10, ge=1, le=100, description="推薦件数")
):
    """
    協調フィルタリング推薦
    
    類似ユーザーの行動履歴を基にした協調フィルタリングで
    求人を推薦します。
    """
    try:
        from hybrid_recommender import CollaborativeFiltering
        
        # 協調フィルタリングで推薦を取得
        job_scores = CollaborativeFiltering.get_recommendations_from_similar_users(
            user_id=user_id,
            top_k=top_k
        )
        
        if not job_scores:
            return RecommendationListResponse(
                recommendations=[],
                total=0,
                user_id=user_id,
            )
        
        # 求人情報を取得
        job_ids = [job_id for job_id, _ in job_scores]
        
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # PostgreSQLのUUID型として扱う
        cur.execute("""
            SELECT cp.id, cp.company_id, cp.job_title, cp.salary_min, cp.salary_max,
                   cp.location_prefecture, cp.intent_labels, cp.click_count,
                   cp.favorite_count, cp.apply_count, cp.view_count,
                   cp.created_at, cp.updated_at, cd.company_name
            FROM company_profile cp
            LEFT JOIN company_date cd ON cp.company_id = cd.company_id
            WHERE cp.id = ANY(%s::uuid[])
        """, (job_ids,))
        
        jobs = {str(job['id']): dict(job) for job in cur.fetchall()}
        
        cur.close()
        conn.close()
        
        # スコアと結合
        recommendation_list = []
        for job_id, score in job_scores:
            if job_id in jobs:
                job_data = jobs[job_id]
                job_response = JobResponse(**job_data)
                
                recommendation_list.append(RecommendationResponse(
                    job=job_response,
                    score=score,
                    match_type='collaborative'
                ))
        
        return RecommendationListResponse(
            recommendations=recommendation_list,
            total=len(recommendation_list),
            user_id=user_id,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"協調フィルタリング推薦エラー: {str(e)}"
        )


@router.get("/content-based/{user_id}", response_model=RecommendationListResponse)
async def get_content_based_recommendations(
    user_id: int,
    top_k: int = Query(10, ge=1, le=100, description="推薦件数")
):
    """
    コンテンツベース推薦
    
    ユーザーの過去の選好（お気に入りや応募）から
    類似した求人を推薦します。
    """
    try:
        from hybrid_recommender import ContentBasedFiltering
        
        # コンテンツベースフィルタリングで推薦を取得
        job_scores = ContentBasedFiltering.get_content_based_recommendations(
            user_id=user_id,
            top_k=top_k
        )
        
        if not job_scores:
            return RecommendationListResponse(
                recommendations=[],
                total=0,
                user_id=user_id,
            )
        
        # 求人情報を取得
        job_ids = [job_id for job_id, _ in job_scores]
        
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT cp.id, cp.company_id, cp.job_title, cp.salary_min, cp.salary_max,
                   cp.location_prefecture, cp.intent_labels, cp.click_count,
                   cp.favorite_count, cp.apply_count, cp.view_count,
                   cp.created_at, cp.updated_at, cd.company_name
            FROM company_profile cp
            LEFT JOIN company_date cd ON cp.company_id = cd.company_id
            WHERE cp.id = ANY(%s::uuid[])
        """, (job_ids,))
        
        jobs = {str(job['id']): dict(job) for job in cur.fetchall()}
        
        cur.close()
        conn.close()
        
        # スコアと結合
        recommendation_list = []
        for job_id, score in job_scores:
            if job_id in jobs:
                job_data = jobs[job_id]
                job_response = JobResponse(**job_data)
                
                recommendation_list.append(RecommendationResponse(
                    job=job_response,
                    score=score,
                    match_type='content-based'
                ))
        
        return RecommendationListResponse(
            recommendations=recommendation_list,
            total=len(recommendation_list),
            user_id=user_id,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"コンテンツベース推薦エラー: {str(e)}"
        )