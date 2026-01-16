"""
求人推薦サービス
"""

from typing import List, Dict, Any
from config.database import get_db_conn
from models.chat_models import JobRecommendation


class JobRecommender:
    """求人推薦ロジック"""
    
    @staticmethod
    def should_show_jobs(
        turn_count: int,
        current_score: float,
        user_message: str,
        score_history: List[float] = None
    ) -> tuple[bool, str]:
        """
        求人を表示すべきかを判定
        
        Args:
            turn_count: 現在のターン数
            current_score: 現在のマッチ度スコア
            user_message: ユーザーの最新メッセージ
            score_history: 過去のスコア履歴（オプション）
            
        Returns:
            (bool, str): (表示すべきか, 理由)
        """
        
        # トリガー1: スコアが80%以上
        if current_score >= 80.0:
            return True, "match_score_high"
        
        # トリガー2: ユーザーが明示的にリクエスト
        request_keywords = [
            '求人', '案件', '仕事', '見せて', '教えて', '出して',
            '紹介', 'おすすめ', '探して', '検索', '提案'
        ]
        
        if any(keyword in user_message for keyword in request_keywords):
            return True, "user_request"
        
        # トリガー3: 10ターン経過
        if turn_count >= 10:
            return True, "turn_limit"
        
        # トリガー4: スコアが3ターン連続で停滞（±5%以内の変動）
        if score_history and len(score_history) >= 4:
            recent_scores = score_history[-4:]  # 直近4ターン
            
            # 全てのスコアが±5%以内に収まっているか
            max_score = max(recent_scores)
            min_score = min(recent_scores)
            
            if max_score - min_score <= 5.0 and turn_count >= 5:
                return True, "score_stagnant"
        
        return False, "continue_chat"
    
    @staticmethod
    def get_recommendations(
        user_preferences: Dict[str, Any],
        conversation_keywords: List[str],
        limit: int = 5
    ) -> List[JobRecommendation]:
        """
        求人を推薦
        
        Args:
            user_preferences: ユーザーの希望（Step2の情報）
            conversation_keywords: 会話から抽出されたキーワード
            limit: 取得件数
            
        Returns:
            List[JobRecommendation]: 推薦求人リスト
        """
        
        conn = get_db_conn()
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # 基本的な条件でフィルタリング
            job_title = user_preferences.get('job_title', '')
            location = user_preferences.get('location', '')
            salary_min = user_preferences.get('salary_min', 0)
            
            # SQLクエリ構築（company_profileに全データがある）
            query = """
                SELECT 
                    id as job_id,
                    job_title,
                    COALESCE(cd.company_name, '非公開') as company_name,
                    salary_min,
                    salary_max,
                    location_prefecture,
                    location_city,
                    remote_option,
                    employment_type,
                    '' as required_skills
                FROM company_profile cp
                LEFT JOIN company_date cd ON cp.company_id = cd.company_id
                WHERE cp.status = 'active'
            """
            
            params = []
            
            print(f"📝 SQLクエリ: {query[:100]}...")
            
            # 職種フィルタ（job_titleを使用）
            if job_title:
                query += " AND job_title ILIKE %s"
                params.append(f"%{job_title}%")
            
            # 勤務地フィルタ
            if location:
                query += " AND (location_prefecture ILIKE %s OR location_city ILIKE %s)"
                params.extend([f"%{location}%", f"%{location}%"])
            
            # 年収フィルタ
            if salary_min and salary_min > 0:
                query += " AND salary_max >= %s"
                params.append(salary_min)
            
            query += f" ORDER BY id DESC LIMIT {limit * 2}"
            
            print(f"🔍 最終クエリ: {query}")
            print(f"🔍 パラメータ: {params}")
            
            cur.execute(query, params)
            jobs = cur.fetchall()
            
            print(f"📊 取得した求人数: {len(jobs)}")
            if jobs:
                print(f"📊 最初の求人: {dict(jobs[0])}")
            
            # スコアリング
            scored_jobs = []
            for job in jobs:
                score = JobRecommender._calculate_job_score(
                    job,
                    user_preferences,
                    conversation_keywords
                )
                
                scored_jobs.append({
                    'job': job,
                    'score': score
                })
            
            # スコア順にソート
            scored_jobs.sort(key=lambda x: x['score'], reverse=True)
            
            # 上位N件を取得
            recommendations = []
            for item in scored_jobs[:limit]:
                job = item['job']
                score = item['score']
                
                recommendations.append(JobRecommendation(
                    job_id=str(job['job_id']),
                    job_title=job['job_title'],
                    company_name=job.get('company_name', '非公開'),
                    match_score=score,
                    match_reasoning=JobRecommender._generate_reasoning(job, conversation_keywords),
                    salary_min=job.get('salary_min', 0),
                    salary_max=job.get('salary_max', 0),
                    location=f"{job.get('location_prefecture', '未設定')} {job.get('location_city', '')}".strip(),
                    remote_option=job.get('remote_option', 'なし')
                ))
            
            return recommendations
            
        except Exception as e:
            print(f"❌ 求人推薦エラー: {e}")
            return []
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def _calculate_job_score(
        job: Dict[str, Any],  # tuple → Dict
        user_preferences: Dict[str, Any],
        keywords: List[str]
    ) -> float:
        """求人のマッチ度スコアを計算"""
        
        score = 50.0  # ベーススコア
        
        # 辞書から値を取得
        job_title = job.get('job_title', '')
        description = job.get('required_skills', '') or job.get('job_description', '')
        salary_min = job.get('salary_min', 0)
        salary_max = job.get('salary_max', 0)
        location = job.get('location_prefecture', '')
        remote = job.get('remote_option', '')
        
        # 職種マッチ
        if user_preferences.get('job_title', '').lower() in job_title.lower():
            score += 15
        
        # 勤務地マッチ
        if user_preferences.get('location', '').lower() in location.lower():
            score += 10
        elif 'リモート' in remote or '在宅' in remote:
            score += 8
        
        # 年収マッチ
        user_salary = user_preferences.get('salary_min', 0)
        if user_salary > 0 and salary_max >= user_salary:
            if salary_min >= user_salary * 0.9:  # 希望の90%以上
                score += 10
            else:
                score += 5
        
        # キーワードマッチ
        matched_keywords = 0
        for keyword in keywords:
            if keyword.lower() in description.lower() or keyword.lower() in job_title.lower():
                matched_keywords += 1
        
        score += min(matched_keywords * 3, 15)  # 最大15点
        
        return min(score, 95.0)  # 上限95点
    
    @staticmethod
    def _generate_reasoning(job: Dict[str, Any], keywords: List[str]) -> str:  # tuple → Dict
        """マッチ理由を生成"""
        
        reasons = []
        
        # 辞書から値を取得
        job_title = job.get('job_title', '')
        description = job.get('required_skills', '') or job.get('job_description', '')
        remote = job.get('remote_option', '')
        
        # キーワードマッチ
        matched = [k for k in keywords if k.lower() in description.lower() or k.lower() in job_title.lower()]
        if matched:
            reasons.append(f"スキルマッチ: {', '.join(matched[:3])}")
        
        # リモート
        if 'リモート' in remote or '在宅' in remote:
            reasons.append("リモートワーク可")
        
        # デフォルト
        if not reasons:
            reasons.append("条件に合致")
        
        return " / ".join(reasons)