"""
マッチングサービス
"""

from typing import List, Dict, Any, Optional
from psycopg2.extras import RealDictCursor
from config.database import get_db_conn
from utils.scoring_utils import hybrid_scoring
from utils.helpers import clean_dict_for_json, merge_accumulated_insights
from utils.ai_utils import extract_user_intent
import json


class MatchingService:
    """マッチングサービスクラス"""
    
    @staticmethod
    def search_jobs(
        criteria: Dict[str, Any],
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        求人検索
        
        Args:
            criteria: 検索条件
            limit: 取得件数
            offset: オフセット
            
        Returns:
            求人リスト
        """
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT cp.*
            FROM company_profile cp
            WHERE cp.status = 'active'
        """
        
        params = []
        
        # 職種
        if criteria.get("job_title"):
            query += " AND cp.job_title ILIKE %s"
            params.append(f"%{criteria['job_title']}%")
        
        # 勤務地
        if criteria.get("location_prefecture"):
            query += " AND cp.location_prefecture = %s"
            params.append(criteria["location_prefecture"])
        
        # 年収
        if criteria.get("salary_min"):
            query += " AND cp.salary_max >= %s"
            params.append(criteria["salary_min"])
        
        # リモート
        if criteria.get("remote_option"):
            query += " AND cp.remote_option = %s"
            params.append(criteria["remote_option"])
        
        query += f" ORDER BY cp.created_at DESC LIMIT {limit} OFFSET {offset}"
        
        cur.execute(query, tuple(params))
        jobs = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return [clean_dict_for_json(dict(job)) for job in jobs]
    
    @staticmethod
    def get_recommendations(
        user_id: str,
        limit: int = 10,
        min_score: int = 60
    ) -> Dict[str, Any]:
        """
        ユーザーへのおすすめ求人を取得
        
        Args:
            user_id: ユーザーID
            limit: 取得件数
            min_score: 最小スコア
            
        Returns:
            おすすめ求人と情報
        """
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # ユーザープロフィール取得
        cur.execute("""
            SELECT preferences
            FROM user_preferences_profile
            WHERE user_id = %s
        """, (user_id,))
        
        profile_row = cur.fetchone()
        user_preferences = profile_row['preferences'] if profile_row else {}
        
        # 求人取得
        cur.execute("""
            SELECT cp.*
            FROM company_profile cp
            WHERE cp.status = 'active'
            ORDER BY cp.created_at DESC
            LIMIT 100
        """)
        
        jobs = cur.fetchall()
        cur.close()
        conn.close()
        
        # スコアリング
        scored_jobs = []
        for job in jobs:
            job_dict = clean_dict_for_json(dict(job))
            
            # 簡易スコアリング（実際はより詳細に）
            score_result = hybrid_scoring(
                user_intent=user_preferences,
                job=job_dict,
                use_ai=False  # 高速化のためルールベースのみ
            )
            
            if score_result['score'] >= min_score:
                scored_jobs.append({
                    **job_dict,
                    "match_score": score_result['score'],
                    "matched_features": score_result.get('matched_features', []),
                    "concerns": score_result.get('concerns', [])
                })
        
        # スコア順にソート
        scored_jobs.sort(key=lambda x: x['match_score'], reverse=True)
        
        return {
            "recommendations": scored_jobs[:limit],
            "total_count": len(scored_jobs),
            "user_preferences": user_preferences
        }
    
    @staticmethod
    def score_jobs_for_user(
        user_id: str,
        user_intent: Dict[str, Any],
        accumulated_insights: Dict[str, Any],
        job_ids: Optional[List[str]] = None,
        limit: int = 20,
        use_ai: bool = True
    ) -> List[Dict[str, Any]]:
        """
        ユーザーに対して求人をスコアリング
        
        Args:
            user_id: ユーザーID
            user_intent: ユーザー意図
            accumulated_insights: 蓄積された洞察
            job_ids: スコアリングする求人IDリスト（Noneなら全件）
            limit: 取得件数
            use_ai: AIスコアリングを使用するか
            
        Returns:
            スコア付き求人リスト
        """
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 求人取得
        if job_ids:
            placeholders = ','.join(['%s'] * len(job_ids))
            query = f"""
                SELECT cp.*
                FROM company_profile cp
                WHERE cp.id IN ({placeholders})
                AND cp.status = 'active'
            """
            cur.execute(query, tuple(job_ids))
        else:
            cur.execute("""
                SELECT cp.*
                FROM company_profile cp
                WHERE cp.status = 'active'
                ORDER BY cp.created_at DESC
                LIMIT 100
            """)
        
        jobs = cur.fetchall()
        cur.close()
        conn.close()
        
        # スコアリング
        scored_jobs = []
        for job in jobs:
            job_dict = clean_dict_for_json(dict(job))
            
            score_result = hybrid_scoring(
                user_intent=user_intent,
                job=job_dict,
                accumulated_insights=accumulated_insights,
                use_ai=use_ai
            )
            
            scored_jobs.append({
                **job_dict,
                "match_score": score_result['score'],
                "reasoning": score_result.get('reasoning', ''),
                "matched_features": score_result.get('matched_features', []),
                "concerns": score_result.get('concerns', [])
            })
        
        # スコア順にソート
        scored_jobs.sort(key=lambda x: x['match_score'], reverse=True)
        
        return scored_jobs[:limit]
    
    @staticmethod
    def find_alternative_jobs(
        original_job_title: str,
        user_preferences: Dict[str, Any],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        代替求人を検索
        
        Args:
            original_job_title: 元の職種
            user_preferences: ユーザー設定
            limit: 取得件数
            
        Returns:
            代替求人リスト
        """
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 類似職種を検索（簡易版）
        cur.execute("""
            SELECT cp.*
            FROM company_profile cp
            WHERE cp.status = 'active'
            AND cp.job_title ILIKE %s
            ORDER BY cp.created_at DESC
            LIMIT %s
        """, (f"%{original_job_title}%", limit))
        
        jobs = cur.fetchall()
        cur.close()
        conn.close()
        
        return [clean_dict_for_json(dict(job)) for job in jobs]
