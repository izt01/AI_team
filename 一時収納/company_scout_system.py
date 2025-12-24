"""
企業向けスカウトシステム
- ユーザーの会話履歴・行動データから性格・特徴を分析
- 企業の求人条件に合うユーザーを検索
- スカウトメッセージの送信・管理
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI
import os
from typing import List, Dict, Any, Optional
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from db_config import get_db_conn
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class UserProfileAnalyzer:
    """ユーザーの会話履歴・行動から性格・特徴を分析"""
    
    @staticmethod
    def analyze_user_personality(user_id: int) -> Dict[str, Any]:
        """
        ユーザーの性格・特徴を分析
        
        Args:
            user_id: ユーザーID
            
        Returns:
            分析結果（性格特性、価値観、強み、キャリア志向など）
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # チャット履歴を取得
            cur.execute("""
                SELECT message_text, extracted_intent, created_at
                FROM chat_history
                WHERE user_id = %s AND message_type = 'user'
                ORDER BY created_at DESC
                LIMIT 50
            """, (user_id,))
            chat_messages = cur.fetchall()
            
            # 質問への回答を取得
            cur.execute("""
                SELECT dq.question_text, dq.category, uqr.response_text, uqr.normalized_response
                FROM user_question_responses uqr
                JOIN dynamic_questions dq ON uqr.question_id = dq.id
                WHERE uqr.user_id = %s
                ORDER BY uqr.created_at DESC
            """, (user_id,))
            question_responses = cur.fetchall()
            
            # ユーザーの行動データを取得
            cur.execute("""
                SELECT * FROM user_interaction_summary
                WHERE user_id = %s
            """, (user_id,))
            behavior_summary = cur.fetchone()
            
            # お気に入り求人の特徴を取得
            cur.execute("""
                SELECT cp.job_title, cp.location_prefecture, cp.salary_min, cp.salary_max,
                       ja.remote_work, ja.flex_time, ja.overtime_avg,
                       cd.company_name, cd.industry, cd.company_size
                FROM user_interactions ui
                JOIN company_profile cp ON ui.job_id = cp.id
                LEFT JOIN job_attributes ja ON cp.id = ja.job_id
                LEFT JOIN company_date cd ON cp.company_id = cd.company_id
                WHERE ui.user_id = %s AND ui.interaction_type = 'favorite'
                ORDER BY ui.created_at DESC
                LIMIT 10
            """, (user_id,))
            favorite_jobs = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # GPT-4で性格分析
            analysis_prompt = f"""
あなたは人材分析の専門家です。以下のユーザーデータから、このユーザーの性格・特徴・キャリア志向を分析してください。

【チャット履歴（最近の発言）】
{chr(10).join([f"- {msg['message_text']}" for msg in chat_messages[:10]])}

【質問への回答】
{chr(10).join([f"Q: {resp['question_text']}" + chr(10) + f"A: {resp['response_text']}" for resp in question_responses[:10]])}

【行動データ】
- クリックした求人数: {behavior_summary['total_clicks'] if behavior_summary else 0}
- お気に入り登録数: {behavior_summary['total_favorites'] if behavior_summary else 0}
- 応募数: {behavior_summary['total_applies'] if behavior_summary else 0}

【お気に入り求人の傾向】
{chr(10).join([f"- {job['company_name']}: {job['job_title']} (年収{job['salary_min']}~{job['salary_max']}万)" for job in favorite_jobs[:5]])}

以下の項目についてJSON形式で分析してください：

{{
  "personality_traits": ["主要な性格特性を3〜5つ"],
  "work_values": ["仕事で重視する価値観を3〜5つ"],
  "career_orientation": "キャリア志向（安定志向/挑戦志向/バランス志向など）",
  "strengths": ["強みと思われる点を3つ"],
  "preferred_work_style": "好む働き方（リモート重視/オフィス重視/柔軟性重視など）",
  "preferred_company_culture": "好む企業文化（チームワーク重視/個人裁量重視/成長重視など）",
  "salary_importance": "年収の重要度（高/中/低）",
  "location_flexibility": "勤務地の柔軟性（高/中/低）",
  "risk_tolerance": "リスク許容度（高/中/低）",
  "growth_mindset": "成長志向の強さ（高/中/低）",
  "summary": "このユーザーの特徴を2-3文で要約"
}}
"""
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # JSON部分を抽出
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)
            
            analysis = json.loads(result_text)
            
            # 分析結果をDBに保存
            UserProfileAnalyzer.save_analysis_to_db(user_id, analysis)
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing user personality: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    @staticmethod
    def save_analysis_to_db(user_id: int, analysis: Dict[str, Any]) -> bool:
        """分析結果をDBに保存"""
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO user_personality_analysis 
                (user_id, analysis_data, created_at, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    analysis_data = EXCLUDED.analysis_data,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, json.dumps(analysis, ensure_ascii=False)))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error saving analysis: {e}")
            return False
    
    @staticmethod
    def get_cached_analysis(user_id: int) -> Optional[Dict[str, Any]]:
        """キャッシュされた分析結果を取得"""
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT analysis_data, updated_at
                FROM user_personality_analysis
                WHERE user_id = %s
            """, (user_id,))
            
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            if result:
                return json.loads(result['analysis_data'])
            return None
            
        except Exception as e:
            print(f"Error getting cached analysis: {e}")
            return None


class ScoutSearchEngine:
    """企業が条件に合うユーザーを検索"""
    
    @staticmethod
    def search_candidates(
        company_id: str,
        job_id: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        企業の求人条件に合うユーザーを検索
        
        Args:
            company_id: 企業ID
            job_id: 求人ID
            filters: 追加フィルター条件
            top_k: 取得件数
            
        Returns:
            マッチするユーザーのリスト
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 求人情報を取得
            cur.execute("""
                SELECT * FROM company_profile
                WHERE id = %s AND company_id = %s
            """, (job_id, company_id))
            job = cur.fetchone()
            
            if not job:
                return []
            
            # 求人のエンベディングを取得
            job_embedding = job['embedding']
            
            # ユーザープロファイルと性格分析データを取得
            cur.execute("""
                SELECT 
                    pd.user_id,
                    pd.user_name,
                    pd.email,
                    up.job_title,
                    up.location_prefecture,
                    up.salary_min,
                    up.embedding,
                    upa.analysis_data,
                    upa.updated_at as analysis_updated_at
                FROM personal_date pd
                JOIN user_profile up ON pd.user_id = up.user_id
                LEFT JOIN user_personality_analysis upa ON pd.user_id = upa.user_id
                WHERE up.embedding IS NOT NULL
            """)
            users = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # エンベディングでマッチング
            candidates = []
            
            for user in users:
                user_embedding = user['embedding']
                
                # 類似度を計算
                similarity = cosine_similarity(
                    [job_embedding],
                    [user_embedding]
                )[0][0]
                
                # 基本条件チェック
                job_title_match = ScoutSearchEngine._check_job_title_match(
                    job['job_title'], 
                    user['job_title']
                )
                location_match = ScoutSearchEngine._check_location_match(
                    job['location_prefecture'], 
                    user['location_prefecture']
                )
                salary_match = ScoutSearchEngine._check_salary_match(
                    job['salary_min'], 
                    job['salary_max'],
                    user['salary_min']
                )
                
                # スコア計算（加重平均）
                score = (
                    similarity * 0.4 +
                    job_title_match * 0.3 +
                    location_match * 0.15 +
                    salary_match * 0.15
                )
                
                # 性格分析データを追加
                analysis_data = None
                if user['analysis_data']:
                    try:
                        analysis_data = json.loads(user['analysis_data'])
                    except:
                        pass
                
                candidates.append({
                    'user_id': user['user_id'],
                    'user_name': user['user_name'],
                    'email': user['email'],
                    'job_title': user['job_title'],
                    'location': user['location_prefecture'],
                    'desired_salary': user['salary_min'],
                    'match_score': score,
                    'similarity': similarity,
                    'personality_analysis': analysis_data,
                    'analysis_updated_at': user['analysis_updated_at']
                })
            
            # スコアでソート
            candidates.sort(key=lambda x: x['match_score'], reverse=True)
            
            # 追加フィルターを適用
            if filters:
                candidates = ScoutSearchEngine._apply_filters(candidates, filters)
            
            return candidates[:top_k]
            
        except Exception as e:
            print(f"Error searching candidates: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def _check_job_title_match(job_title: str, user_job_title: str) -> float:
        """職種のマッチ度（0.0〜1.0）"""
        if not job_title or not user_job_title:
            return 0.5
        
        job_title_lower = job_title.lower()
        user_job_title_lower = user_job_title.lower()
        
        # 完全一致
        if job_title_lower == user_job_title_lower:
            return 1.0
        
        # 部分一致
        if job_title_lower in user_job_title_lower or user_job_title_lower in job_title_lower:
            return 0.8
        
        # キーワードベースのマッチング
        keywords = ['エンジニア', 'デザイナー', 'マーケター', 'セールス', 'マネージャー', 
                   'ディレクター', 'プランナー', 'コンサルタント', 'アナリスト']
        
        for keyword in keywords:
            if keyword in job_title and keyword in user_job_title:
                return 0.6
        
        return 0.3
    
    @staticmethod
    def _check_location_match(job_location: str, user_location: str) -> float:
        """勤務地のマッチ度（0.0〜1.0）"""
        if not job_location or not user_location:
            return 0.5
        
        # 完全一致
        if job_location == user_location:
            return 1.0
        
        # 首都圏・関西圏などの広域マッチング
        kanto_area = ['東京', '神奈川', '千葉', '埼玉']
        kansai_area = ['大阪', '京都', '兵庫']
        
        if job_location in kanto_area and user_location in kanto_area:
            return 0.8
        
        if job_location in kansai_area and user_location in kansai_area:
            return 0.8
        
        return 0.3
    
    @staticmethod
    def _check_salary_match(job_min: int, job_max: int, user_min: int) -> float:
        """年収のマッチ度（0.0〜1.0）"""
        if not user_min:
            return 0.5
        
        # ユーザーの希望年収が求人の範囲内
        if job_min <= user_min <= job_max:
            return 1.0
        
        # ユーザーの希望が求人の下限より低い（採用しやすい）
        if user_min < job_min:
            diff = job_min - user_min
            if diff <= 50:  # 50万円以内
                return 0.9
            elif diff <= 100:  # 100万円以内
                return 0.7
            else:
                return 0.5
        
        # ユーザーの希望が求人の上限より高い
        if user_min > job_max:
            diff = user_min - job_max
            if diff <= 50:
                return 0.6
            elif diff <= 100:
                return 0.4
            else:
                return 0.2
        
        return 0.5
    
    @staticmethod
    def _apply_filters(candidates: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
        """追加フィルターを適用"""
        filtered = candidates
        
        # 性格特性フィルター
        if 'personality_traits' in filters and filters['personality_traits']:
            required_traits = set(filters['personality_traits'])
            filtered = [
                c for c in filtered
                if c['personality_analysis'] and 
                len(set(c['personality_analysis'].get('personality_traits', [])) & required_traits) > 0
            ]
        
        # キャリア志向フィルター
        if 'career_orientation' in filters and filters['career_orientation']:
            filtered = [
                c for c in filtered
                if c['personality_analysis'] and
                c['personality_analysis'].get('career_orientation') == filters['career_orientation']
            ]
        
        # 最低マッチスコア
        if 'min_score' in filters:
            filtered = [c for c in filtered if c['match_score'] >= filters['min_score']]
        
        return filtered


class ScoutMessageManager:
    """スカウトメッセージの管理"""
    
    @staticmethod
    def send_scout_message(
        company_id: str,
        job_id: str,
        user_id: int,
        message_text: str,
        auto_generated: bool = False
    ) -> bool:
        """
        スカウトメッセージを送信
        
        Args:
            company_id: 企業ID
            job_id: 求人ID
            user_id: ユーザーID
            message_text: メッセージ本文
            auto_generated: AI自動生成かどうか
            
        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO scout_messages 
                (company_id, job_id, user_id, message_text, auto_generated, status, created_at)
                VALUES (%s, %s, %s, %s, %s, 'sent', CURRENT_TIMESTAMP)
            """, (company_id, job_id, user_id, message_text, auto_generated))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error sending scout message: {e}")
            return False
    
    @staticmethod
    def generate_scout_message(
        job_info: Dict[str, Any],
        user_profile: Dict[str, Any],
        user_analysis: Dict[str, Any]
    ) -> str:
        """
        AIでスカウトメッセージを生成
        
        Args:
            job_info: 求人情報
            user_profile: ユーザープロファイル
            user_analysis: ユーザー性格分析
            
        Returns:
            生成されたメッセージ
        """
        try:
            prompt = f"""
あなたは企業の採用担当者です。以下の求人に最適な候補者を見つけたので、魅力的なスカウトメッセージを作成してください。

【求人情報】
- 企業名: {job_info.get('company_name', '')}
- 職種: {job_info.get('job_title', '')}
- 勤務地: {job_info.get('location_prefecture', '')}
- 年収: {job_info.get('salary_min', '')}万〜{job_info.get('salary_max', '')}万

【候補者のプロファイル】
- 現在の職種: {user_profile.get('job_title', '')}
- 希望勤務地: {user_profile.get('location_prefecture', '')}
- 希望年収: {user_profile.get('salary_min', '')}万〜

【候補者の性格・特徴】
- 性格特性: {', '.join(user_analysis.get('personality_traits', []))}
- 仕事の価値観: {', '.join(user_analysis.get('work_values', []))}
- キャリア志向: {user_analysis.get('career_orientation', '')}
- 強み: {', '.join(user_analysis.get('strengths', []))}
- 要約: {user_analysis.get('summary', '')}

以下の要件でメッセージを作成してください：
1. 候補者の強みや特徴を具体的に褒める
2. なぜこの求人が候補者に合うのかを説明
3. 企業の魅力をアピール
4. カジュアル面談への誘導
5. 親しみやすく、押し付けがましくないトーン
6. 300〜400文字程度

メッセージのみを出力してください（挨拶から結びまで）。
"""
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating scout message: {e}")
            return "ご経歴を拝見し、ぜひ一度お話しさせていただきたくご連絡いたしました。"
    
    @staticmethod
    def get_scout_history(company_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """企業のスカウト送信履歴を取得"""
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT 
                    sm.*,
                    pd.user_name,
                    cp.job_title,
                    cd.company_name
                FROM scout_messages sm
                JOIN personal_date pd ON sm.user_id = pd.user_id
                JOIN company_profile cp ON sm.job_id = cp.id
                JOIN company_date cd ON sm.company_id = cd.company_id
                WHERE sm.company_id = %s
                ORDER BY sm.created_at DESC
                LIMIT %s
            """, (company_id, limit))
            
            history = cur.fetchall()
            cur.close()
            conn.close()
            
            return [dict(h) for h in history]
            
        except Exception as e:
            print(f"Error getting scout history: {e}")
            return []
    
    @staticmethod
    def mark_as_read(scout_message_id: int) -> bool:
        """スカウトを既読にする"""
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            
            cur.execute("""
                UPDATE scout_messages
                SET status = 'read', read_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (scout_message_id,))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error marking scout as read: {e}")
            return False
    
    @staticmethod
    def mark_as_replied(scout_message_id: int) -> bool:
        """スカウトに返信があったことを記録"""
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            
            cur.execute("""
                UPDATE scout_messages
                SET status = 'replied', replied_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (scout_message_id,))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error marking scout as replied: {e}")
            return False


# ユーティリティ関数
def batch_analyze_users(user_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """複数ユーザーをバッチで分析"""
    results = {}
    
    for user_id in user_ids:
        print(f"Analyzing user {user_id}...")
        analysis = UserProfileAnalyzer.analyze_user_personality(user_id)
        results[user_id] = analysis
    
    return results


def get_top_candidates_for_job(company_id: str, job_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    求人に最適な候補者を取得（フルパイプライン）
    
    1. スカウト検索で候補者を取得
    2. 性格分析が古い/ない場合は再分析
    3. スカウトメッセージを自動生成
    """
    # 候補者を検索
    candidates = ScoutSearchEngine.search_candidates(company_id, job_id, top_k=limit)
    
    # 性格分析を更新（必要に応じて）
    for candidate in candidates:
        user_id = candidate['user_id']
        
        # 分析が7日以上古い、または存在しない場合は再分析
        from datetime import datetime, timedelta
        
        needs_update = False
        if not candidate['analysis_updated_at']:
            needs_update = True
        else:
            last_update = candidate['analysis_updated_at']
            if isinstance(last_update, str):
                last_update = datetime.fromisoformat(last_update)
            
            if datetime.now() - last_update > timedelta(days=7):
                needs_update = True
        
        if needs_update:
            print(f"Updating analysis for user {user_id}...")
            analysis = UserProfileAnalyzer.analyze_user_personality(user_id)
            candidate['personality_analysis'] = analysis
    
    return candidates