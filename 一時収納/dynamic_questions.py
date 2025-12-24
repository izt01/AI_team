"""
動的質問生成エンジン
- 求人データから質問を自動生成
- ユーザー履歴に基づいて最適な質問を選択
- 質問の有効性を追跡・評価
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


class QuestionGenerator:
    """動的質問生成クラス"""

    @staticmethod
    def generate_questions_from_jobs() -> List[Dict[str, Any]]:
        """
        既存の求人データを分析して、新しい質問を自動生成

        Returns:
            生成された質問のリスト
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 求人属性を分析
            cur.execute("""
                SELECT
                    company_culture,
                    work_flexibility,
                    career_path
                FROM job_attributes
                LIMIT 100
            """)

            attributes = cur.fetchall()
            cur.close()
            conn.close()

            if not attributes:
                return []

            # 頻出する属性を抽出
            culture_values = {}
            flexibility_values = {}
            career_values = {}

            for attr in attributes:
                # 企業文化
                if attr['company_culture']:
                    culture = attr['company_culture']
                    for key, value in culture.items():
                        culture_values[f"{key}:{value}"] = culture_values.get(f"{key}:{value}", 0) + 1

                # 働き方
                if attr['work_flexibility']:
                    flex = attr['work_flexibility']
                    for key, value in flex.items():
                        flexibility_values[f"{key}:{value}"] = flexibility_values.get(f"{key}:{value}", 0) + 1

                # キャリアパス
                if attr['career_path']:
                    career = attr['career_path']
                    for key, value in career.items():
                        career_values[f"{key}:{value}"] = career_values.get(f"{key}:{value}", 0) + 1

            # 頻出する項目から質問を生成
            questions = []

            # 企業文化の質問
            for key_value, count in sorted(culture_values.items(), key=lambda x: x[1], reverse=True)[:3]:
                key, value = key_value.split(':', 1)
                question = QuestionGenerator._create_question_for_attribute('企業文化・雰囲気', key, value, count)
                if question:
                    questions.append(question)

            # 働き方の質問
            for key_value, count in sorted(flexibility_values.items(), key=lambda x: x[1], reverse=True)[:3]:
                key, value = key_value.split(':', 1)
                question = QuestionGenerator._create_question_for_attribute('働き方の柔軟性', key, value, count)
                if question:
                    questions.append(question)

            # キャリアパスの質問
            for key_value, count in sorted(career_values.items(), key=lambda x: x[1], reverse=True)[:3]:
                key, value = key_value.split(':', 1)
                question = QuestionGenerator._create_question_for_attribute('キャリアパス', key, value, count)
                if question:
                    questions.append(question)

            return questions

        except Exception as e:
            print(f"Error generating questions from jobs: {e}")
            return []

    @staticmethod
    def _create_question_for_attribute(category: str, key: str, value: str, frequency: int) -> Optional[Dict[str, Any]]:
        """
        属性から質問を生成

        Args:
            category: カテゴリ
            key: 属性キー
            value: 属性値
            frequency: 出現頻度

        Returns:
            質問の辞書
        """
        # 質問文のマッピング
        question_templates = {
            'remote': 'リモートワークを希望しますか？',
            'flex_time': 'フレックスタイム制度を希望しますか？',
            'side_job': '副業可能な環境を希望しますか？',
            'type': '企業の規模やタイプに希望はありますか？',
            'atmosphere': '組織の雰囲気に希望はありますか？',
            'growth_opportunities': 'キャリア成長の機会を重視しますか？',
            'training': '研修・スキルアップ支援を重視しますか？',
            'promotion_speed': '昇進スピードを重視しますか？'
        }

        question_text = question_templates.get(key)
        if not question_text:
            return None

        return {
            'question_key': key,
            'question_text': question_text,
            'category': category,
            'question_type': 'boolean' if value in ['True', 'False', 'true', 'false'] else 'choice',
            'frequency': frequency
        }

    @staticmethod
    def save_generated_questions(questions: List[Dict[str, Any]]) -> int:
        """
        生成された質問をデータベースに保存

        Args:
            questions: 質問のリスト

        Returns:
            保存された質問数
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            saved_count = 0
            for q in questions:
                try:
                    cur.execute("""
                        INSERT INTO dynamic_questions (question_key, question_text, category, question_type)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (question_key) DO NOTHING
                    """, (q['question_key'], q['question_text'], q['category'], q['question_type']))
                    saved_count += cur.rowcount
                except Exception as e:
                    print(f"Error saving question: {e}")

            conn.commit()
            cur.close()
            conn.close()
            return saved_count

        except Exception as e:
            print(f"Error in save_generated_questions: {e}")
            return 0


class QuestionSelector:
    """質問選択クラス（ユーザー履歴ベース）"""

    @staticmethod
    def select_next_question(user_id: int, search_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        次に尋ねる質問を選択（ユーザー履歴ベース）

        Args:
            user_id: ユーザーID
            search_results: 現在の検索結果

        Returns:
            選択された質問の辞書、なければNone
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 既に回答済みの質問を取得
            cur.execute("""
                SELECT question_id FROM user_question_responses
                WHERE user_id = %s
            """, (user_id,))
            answered_question_ids = [row['question_id'] for row in cur.fetchall()]

            # 検索結果から差分がある項目を分析
            relevant_categories = QuestionSelector._analyze_search_results_diff(search_results)

            # 他のユーザーが有効だと評価した質問を取得（effectiveness_scoreでソート）
            if answered_question_ids:
                cur.execute("""
                    SELECT id, question_key, question_text, category, question_type,
                           effectiveness_score, usage_count
                    FROM dynamic_questions
                    WHERE id NOT IN %s
                    ORDER BY effectiveness_score DESC, usage_count DESC
                    LIMIT 10
                """, (tuple(answered_question_ids),))
            else:
                cur.execute("""
                    SELECT id, question_key, question_text, category, question_type,
                           effectiveness_score, usage_count
                    FROM dynamic_questions
                    ORDER BY effectiveness_score DESC, usage_count DESC
                    LIMIT 10
                """)

            candidates = cur.fetchall()
            cur.close()
            conn.close()

            if not candidates:
                return None

            # 関連するカテゴリの質問を優先
            for candidate in candidates:
                if candidate['category'] in relevant_categories:
                    return dict(candidate)

            # なければeffectiveness_scoreが最も高いものを返す
            return dict(candidates[0]) if candidates else None

        except Exception as e:
            print(f"Error selecting next question: {e}")
            return None

    @staticmethod
    def _analyze_search_results_diff(search_results: List[Dict[str, Any]]) -> List[str]:
        """
        検索結果から差分がある項目を分析

        Args:
            search_results: 検索結果のリスト

        Returns:
            関連するカテゴリのリスト
        """
        if not search_results or len(search_results) < 2:
            return ['企業文化・雰囲気', '働き方の柔軟性', 'キャリアパス']

        # 求人の属性を取得して差分を分析
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            job_ids = [job['id'] for job in search_results if 'id' in job]

            if not job_ids:
                return ['企業文化・雰囲気', '働き方の柔軟性', 'キャリアパス']

            cur.execute("""
                SELECT company_culture, work_flexibility, career_path
                FROM job_attributes
                WHERE job_id IN %s
            """, (tuple(job_ids),))

            attributes = cur.fetchall()
            cur.close()
            conn.close()

            if not attributes:
                return ['企業文化・雰囲気', '働き方の柔軟性', 'キャリアパス']

            # 差分があるカテゴリを抽出
            relevant_categories = []

            # 企業文化の差分チェック
            culture_values = set()
            for attr in attributes:
                if attr['company_culture']:
                    culture_values.add(json.dumps(attr['company_culture'], sort_keys=True))
            if len(culture_values) > 1:
                relevant_categories.append('企業文化・雰囲気')

            # 働き方の差分チェック
            flex_values = set()
            for attr in attributes:
                if attr['work_flexibility']:
                    flex_values.add(json.dumps(attr['work_flexibility'], sort_keys=True))
            if len(flex_values) > 1:
                relevant_categories.append('働き方の柔軟性')

            # キャリアパスの差分チェック
            career_values = set()
            for attr in attributes:
                if attr['career_path']:
                    career_values.add(json.dumps(attr['career_path'], sort_keys=True))
            if len(career_values) > 1:
                relevant_categories.append('キャリアパス')

            return relevant_categories if relevant_categories else ['企業文化・雰囲気', '働き方の柔軟性', 'キャリアパス']

        except Exception as e:
            print(f"Error analyzing search results: {e}")
            return ['企業文化・雰囲気', '働き方の柔軟性', 'キャリアパス']

    @staticmethod
    def generate_question_with_ai(context: str, diff_info: Dict[str, Any]) -> str:
        """
        AIを使って自然な質問文を生成

        Args:
            context: コンテキスト（現在の検索状況など）
            diff_info: 差分情報

        Returns:
            生成された質問文
        """
        try:
            prompt = f"""
以下の状況で、ユーザーに次に聞くべき質問を1つ生成してください。

状況:
{context}

差分がある項目:
{json.dumps(diff_info, ensure_ascii=False, indent=2)}

要件:
- 自然で会話的な質問文にしてください
- ユーザーが答えやすい形式にしてください
- 1つの質問に絞ってください

質問文のみを返してください。
"""

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            question = response.choices[0].message.content.strip()
            return question

        except Exception as e:
            print(f"Error generating question with AI: {e}")
            return "他に重視する条件はありますか？"

    @staticmethod
    def get_all_questions() -> List[Dict[str, Any]]:
        """全質問を取得"""
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT id, question_key, question_text, category, question_type,
                       usage_count, effectiveness_score
                FROM dynamic_questions
                ORDER BY effectiveness_score DESC, usage_count DESC
            """)

            questions = cur.fetchall()
            cur.close()
            conn.close()

            return [dict(q) for q in questions]

        except Exception as e:
            print(f"Error getting all questions: {e}")
            return []

    @staticmethod
    def get_question_by_id(question_id: int) -> Optional[Dict[str, Any]]:
        """IDから質問を取得"""
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT id, question_key, question_text, category, question_type,
                       usage_count, effectiveness_score
                FROM dynamic_questions
                WHERE id = %s
            """, (question_id,))

            question = cur.fetchone()
            cur.close()
            conn.close()

            return dict(question) if question else None

        except Exception as e:
            print(f"Error getting question by id: {e}")
            return None

    @staticmethod
    def get_question_by_key(question_key: str) -> Optional[Dict[str, Any]]:
        """キーから質問を取得"""
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT id, question_key, question_text, category, question_type,
                       usage_count, effectiveness_score
                FROM dynamic_questions
                WHERE question_key = %s
            """, (question_key,))

            question = cur.fetchone()
            cur.close()
            conn.close()

            return dict(question) if question else None

        except Exception as e:
            print(f"Error getting question by key: {e}")
            return None
