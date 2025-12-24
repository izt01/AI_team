"""
多軸評価システムモジュール
- 求人情報から多軸属性を自動抽出（AI使用）
- ユーザープロファイルの多軸評価を管理
- 多軸マッチングスコアの計算
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import openai
import json
from typing import Dict, Any, Optional, List
import re


def get_db_conn():
    """データベース接続を取得"""
    return psycopg2.connect(
        host="localhost", port=5432, dbname="jobmatch",
        user="devuser", password="devpass"
    )


class JobAttributeExtractor:
    """求人の多軸属性抽出クラス"""

    @staticmethod
    def extract_attributes_with_ai(job_text: str) -> Dict[str, Any]:
        """
        AIを使って求人情報から多軸属性を抽出

        Args:
            job_text: 求人情報のテキスト

        Returns:
            抽出された属性（JSON形式）
        """
        prompt = f"""
以下の求人情報から、3つの軸で特徴を抽出してJSON形式で返してください。

求人情報:
{job_text}

抽出する軸:
1. company_culture (企業文化・雰囲気):
   - type: "startup" / "venture" / "mid-size" / "large-enterprise"
   - atmosphere: "flat" / "hierarchical" / "challenging" / "stable"
   - size: "small" / "medium" / "large"

2. work_flexibility (働き方の柔軟性):
   - remote: true / false
   - flex_time: true / false
   - side_job: true / false
   - overtime: "low" / "medium" / "high"

3. career_path (キャリアパス):
   - growth_opportunities: true / false
   - training: true / false
   - promotion_speed: "fast" / "normal" / "slow"
   - skill_support: true / false

出力形式:
{{
  "company_culture": {{"type": "...", "atmosphere": "...", "size": "..."}},
  "work_flexibility": {{"remote": true/false, "flex_time": true/false, "side_job": true/false, "overtime": "..."}},
  "career_path": {{"growth_opportunities": true/false, "training": true/false, "promotion_speed": "...", "skill_support": true/false}}
}}

JSON形式のみ返してください。説明は不要です。
"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            result_text = response.choices[0].message.content.strip()

            # JSON部分を抽出（```json と ``` で囲まれている場合）
            json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)

            # JSONをパース
            attributes = json.loads(result_text)
            return attributes

        except Exception as e:
            print(f"Error extracting attributes with AI: {e}")
            # デフォルト値を返す
            return {
                "company_culture": {"type": "unknown", "atmosphere": "unknown", "size": "unknown"},
                "work_flexibility": {"remote": False, "flex_time": False, "side_job": False, "overtime": "unknown"},
                "career_path": {"growth_opportunities": False, "training": False, "promotion_speed": "unknown", "skill_support": False}
            }

    @staticmethod
    def save_job_attributes(job_id: int, attributes: Dict[str, Any]) -> bool:
        """
        求人の多軸属性をデータベースに保存

        Args:
            job_id: 求人ID
            attributes: 抽出された属性

        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO job_attributes (job_id, company_culture, work_flexibility, career_path)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (job_id)
                DO UPDATE SET
                    company_culture = EXCLUDED.company_culture,
                    work_flexibility = EXCLUDED.work_flexibility,
                    career_path = EXCLUDED.career_path,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                job_id,
                json.dumps(attributes.get('company_culture', {})),
                json.dumps(attributes.get('work_flexibility', {})),
                json.dumps(attributes.get('career_path', {}))
            ))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            print(f"Error saving job attributes: {e}")
            return False

    @staticmethod
    def extract_and_save_job_attributes(job_id: int) -> bool:
        """
        求人情報を取得し、属性を抽出してDBに保存

        Args:
            job_id: 求人ID

        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 求人情報を取得
            cur.execute("""
                SELECT cp.id, cp.job_title, cp.location_prefecture,
                       cp.salary_min, cp.salary_max, cp.intent_labels,
                       cd.company_name
                FROM company_profile cp
                JOIN company_date cd ON cp.company_id = cd.company_id
                WHERE cp.id = %s
            """, (job_id,))

            job = cur.fetchone()
            cur.close()
            conn.close()

            if not job:
                print(f"Job {job_id} not found")
                return False

            # 求人情報をテキスト化
            job_text = f"""
会社名: {job['company_name']}
職種: {job['job_title']}
勤務地: {job['location_prefecture']}
年収: {job['salary_min']}万〜{job['salary_max']}万
その他: {job.get('intent_labels', '')}
"""

            # AIで属性を抽出
            attributes = JobAttributeExtractor.extract_attributes_with_ai(job_text)

            # DBに保存
            return JobAttributeExtractor.save_job_attributes(job_id, attributes)

        except Exception as e:
            print(f"Error in extract_and_save_job_attributes: {e}")
            return False

    @staticmethod
    def get_job_attributes(job_id: int) -> Optional[Dict[str, Any]]:
        """
        求人の多軸属性を取得

        Args:
            job_id: 求人ID

        Returns:
            属性の辞書、存在しない場合はNone
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT company_culture, work_flexibility, career_path
                FROM job_attributes
                WHERE job_id = %s
            """, (job_id,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if not result:
                return None

            return {
                'company_culture': result['company_culture'],
                'work_flexibility': result['work_flexibility'],
                'career_path': result['career_path']
            }

        except Exception as e:
            print(f"Error getting job attributes: {e}")
            return None


class UserPreferenceManager:
    """ユーザーの多軸評価プロファイル管理クラス"""

    @staticmethod
    def build_preference_text(user_id: int) -> str:
        """
        ユーザーの回答履歴と行動履歴から、好みのテキスト表現を生成

        Args:
            user_id: ユーザーID

        Returns:
            プロファイルのテキスト
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # ユーザープロファイルを取得
            cur.execute("""
                SELECT job_title, location_prefecture, salary_min, intent_label
                FROM user_profile
                WHERE user_id = %s
            """, (user_id,))
            profile = cur.fetchone()

            # 質問への回答を取得
            cur.execute("""
                SELECT dq.question_key, dq.category, uqr.normalized_response
                FROM user_question_responses uqr
                JOIN dynamic_questions dq ON uqr.question_id = dq.id
                WHERE uqr.user_id = %s
            """, (user_id,))
            responses = cur.fetchall()

            # お気に入りの求人を取得
            cur.execute("""
                SELECT cp.job_title, cp.location_prefecture, cd.company_name
                FROM user_interactions ui
                JOIN company_profile cp ON ui.job_id = cp.id
                JOIN company_date cd ON cp.company_id = cd.company_id
                WHERE ui.user_id = %s AND ui.interaction_type = 'favorite'
                LIMIT 5
            """, (user_id,))
            favorites = cur.fetchall()

            cur.close()
            conn.close()

            # テキストを構築
            text_parts = []

            if profile:
                text_parts.append(f"希望職種: {profile['job_title']}")
                text_parts.append(f"希望勤務地: {profile['location_prefecture']}")
                text_parts.append(f"希望年収: {profile['salary_min']}万円以上")

            if responses:
                response_texts = [f"{r['category']}: {r['normalized_response']}" for r in responses]
                text_parts.append("回答: " + ", ".join(response_texts))

            if favorites:
                fav_texts = [f"{f['company_name']}の{f['job_title']}" for f in favorites]
                text_parts.append("お気に入り: " + ", ".join(fav_texts))

            return "\n".join(text_parts)

        except Exception as e:
            print(f"Error building preference text: {e}")
            return ""

    @staticmethod
    def generate_preference_embedding(user_id: int) -> Optional[List[float]]:
        """
        ユーザープロファイルのEmbeddingを生成

        Args:
            user_id: ユーザーID

        Returns:
            Embeddingベクトル
        """
        try:
            # プロファイルテキストを生成
            preference_text = UserPreferenceManager.build_preference_text(user_id)

            if not preference_text:
                return None

            # OpenAI Embeddingで埋め込み
            response = openai.Embedding.create(
                input=preference_text,
                model="text-embedding-ada-002"
            )

            embedding = response['data'][0]['embedding']
            return embedding

        except Exception as e:
            print(f"Error generating preference embedding: {e}")
            return None

    @staticmethod
    def update_user_preferences(user_id: int) -> bool:
        """
        ユーザーの多軸評価プロファイルを更新

        Args:
            user_id: ユーザーID

        Returns:
            成功したかどうか
        """
        try:
            # プロファイルテキストを生成
            preference_text = UserPreferenceManager.build_preference_text(user_id)

            # Embeddingを生成
            embedding = UserPreferenceManager.generate_preference_embedding(user_id)

            if not embedding:
                return False

            # 多軸評価の好みを抽出（質問への回答から）
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 質問への回答から好みを抽出
            cur.execute("""
                SELECT dq.question_key, dq.category, uqr.normalized_response
                FROM user_question_responses uqr
                JOIN dynamic_questions dq ON uqr.question_id = dq.id
                WHERE uqr.user_id = %s
            """, (user_id,))
            responses = cur.fetchall()

            # カテゴリ別に整理
            company_culture_pref = {}
            work_flexibility_pref = {}
            career_path_pref = {}

            for resp in responses:
                key = resp['question_key']
                value = resp['normalized_response']
                category = resp['category']

                if category == '企業文化・雰囲気':
                    company_culture_pref[key] = value
                elif category == '働き方の柔軟性':
                    work_flexibility_pref[key] = value
                elif category == 'キャリアパス':
                    career_path_pref[key] = value

            # データベースに保存
            cur.execute("""
                INSERT INTO user_preferences (
                    user_id, preference_vector, preference_text,
                    company_culture_pref, work_flexibility_pref, career_path_pref
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    preference_vector = EXCLUDED.preference_vector,
                    preference_text = EXCLUDED.preference_text,
                    company_culture_pref = EXCLUDED.company_culture_pref,
                    work_flexibility_pref = EXCLUDED.work_flexibility_pref,
                    career_path_pref = EXCLUDED.career_path_pref,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                user_id,
                str(embedding),  # pgvectorに保存する場合は適切な形式に変換が必要
                preference_text,
                json.dumps(company_culture_pref),
                json.dumps(work_flexibility_pref),
                json.dumps(career_path_pref)
            ))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            print(f"Error updating user preferences: {e}")
            return False

    @staticmethod
    def calculate_multi_axis_score(user_id: int, job_id: int) -> float:
        """
        ユーザーと求人の多軸マッチングスコアを計算

        Args:
            user_id: ユーザーID
            job_id: 求人ID

        Returns:
            マッチングスコア（0.0〜1.0）
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # ユーザーの好みを取得
            cur.execute("""
                SELECT company_culture_pref, work_flexibility_pref, career_path_pref
                FROM user_preferences
                WHERE user_id = %s
            """, (user_id,))
            user_pref = cur.fetchone()

            # 求人の属性を取得
            cur.execute("""
                SELECT company_culture, work_flexibility, career_path
                FROM job_attributes
                WHERE job_id = %s
            """, (job_id,))
            job_attr = cur.fetchone()

            cur.close()
            conn.close()

            if not user_pref or not job_attr:
                return 0.0

            # スコア計算（簡易版）
            total_score = 0.0
            count = 0

            # 企業文化のマッチング
            if user_pref['company_culture_pref'] and job_attr['company_culture']:
                culture_score = UserPreferenceManager._compare_dicts(
                    user_pref['company_culture_pref'],
                    job_attr['company_culture']
                )
                total_score += culture_score
                count += 1

            # 働き方の柔軟性のマッチング
            if user_pref['work_flexibility_pref'] and job_attr['work_flexibility']:
                flex_score = UserPreferenceManager._compare_dicts(
                    user_pref['work_flexibility_pref'],
                    job_attr['work_flexibility']
                )
                total_score += flex_score
                count += 1

            # キャリアパスのマッチング
            if user_pref['career_path_pref'] and job_attr['career_path']:
                career_score = UserPreferenceManager._compare_dicts(
                    user_pref['career_path_pref'],
                    job_attr['career_path']
                )
                total_score += career_score
                count += 1

            return total_score / count if count > 0 else 0.0

        except Exception as e:
            print(f"Error calculating multi-axis score: {e}")
            return 0.0

    @staticmethod
    def _compare_dicts(user_dict: Dict, job_dict: Dict) -> float:
        """
        2つの辞書を比較してスコアを計算

        Args:
            user_dict: ユーザーの好み
            job_dict: 求人の属性

        Returns:
            マッチングスコア（0.0〜1.0）
        """
        if not user_dict or not job_dict:
            return 0.0

        matches = 0
        total = 0

        for key, user_value in user_dict.items():
            if key in job_dict:
                job_value = job_dict[key]
                total += 1

                # 値を比較
                if isinstance(user_value, bool) and isinstance(job_value, bool):
                    if user_value == job_value:
                        matches += 1
                elif str(user_value).lower() == str(job_value).lower():
                    matches += 1

        return matches / total if total > 0 else 0.0
