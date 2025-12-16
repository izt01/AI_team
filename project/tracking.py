"""
ユーザー行動追跡モジュール
- 求人クリック、閲覧、お気に入り、応募の記録
- チャット履歴の保存
- 行動データの分析
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json
from typing import Optional, Dict, List, Any
from db_config import get_db_conn


class UserInteractionTracker:
    """ユーザー行動追跡クラス"""

    @staticmethod
    def track_interaction(
        user_id: int,
        job_id: int,
        interaction_type: str,
        interaction_value: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        ユーザー行動を記録

        Args:
            user_id: ユーザーID
            job_id: 求人ID
            interaction_type: 行動タイプ ('click', 'favorite', 'apply', 'view', 'chat_mention')
            interaction_value: 数値（閲覧時間など）
            metadata: 追加情報（JSON）

        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO user_interactions (user_id, job_id, interaction_type, interaction_value, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, job_id, interaction_type, interaction_value, json.dumps(metadata) if metadata else None))

            # company_profileの統計カウントも更新
            if interaction_type == 'click':
                cur.execute("UPDATE company_profile SET click_count = click_count + 1 WHERE id = %s", (job_id,))
            elif interaction_type == 'favorite':
                cur.execute("UPDATE company_profile SET favorite_count = favorite_count + 1 WHERE id = %s", (job_id,))
            elif interaction_type == 'apply':
                cur.execute("UPDATE company_profile SET apply_count = apply_count + 1 WHERE id = %s", (job_id,))
            elif interaction_type == 'view':
                cur.execute("UPDATE company_profile SET view_count = view_count + 1 WHERE id = %s", (job_id,))

            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error tracking interaction: {e}")
            return False

    @staticmethod
    def add_favorite(user_id: int, job_id: int) -> bool:
        """お気に入りに追加"""
        return UserInteractionTracker.track_interaction(user_id, job_id, 'favorite')

    @staticmethod
    def remove_favorite(user_id: int, job_id: int) -> bool:
        """お気に入りから削除"""
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            # 最新のfavorite記録を削除
            cur.execute("""
                DELETE FROM user_interactions
                WHERE id = (
                    SELECT id FROM user_interactions
                    WHERE user_id = %s AND job_id = %s AND interaction_type = 'favorite'
                    ORDER BY created_at DESC
                    LIMIT 1
                )
            """, (user_id, job_id))

            # company_profileの統計カウントも更新
            cur.execute("UPDATE company_profile SET favorite_count = GREATEST(favorite_count - 1, 0) WHERE id = %s", (job_id,))

            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error removing favorite: {e}")
            return False

    @staticmethod
    def is_favorited(user_id: int, job_id: int) -> bool:
        """お気に入り済みかチェック"""
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            cur.execute("""
                SELECT COUNT(*) FROM user_interactions
                WHERE user_id = %s AND job_id = %s AND interaction_type = 'favorite'
            """, (user_id, job_id))

            count = cur.fetchone()[0]
            cur.close()
            conn.close()

            return count > 0
        except Exception as e:
            print(f"Error checking favorite: {e}")
            return False

    @staticmethod
    def get_user_favorites(user_id: int) -> List[Dict[str, Any]]:
        """ユーザーのお気に入り求人一覧を取得"""
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT DISTINCT ON (ui.job_id)
                    cp.id, cp.job_title, cp.location_prefecture,
                    cp.salary_min, cp.salary_max,
                    cd.company_name,
                    ui.created_at as favorited_at
                FROM user_interactions ui
                JOIN company_profile cp ON ui.job_id = cp.id
                JOIN company_date cd ON cp.company_id = cd.company_id
                WHERE ui.user_id = %s AND ui.interaction_type = 'favorite'
                ORDER BY ui.job_id, ui.created_at DESC
            """, (user_id,))

            favorites = cur.fetchall()
            cur.close()
            conn.close()

            return [dict(fav) for fav in favorites]
        except Exception as e:
            print(f"Error getting favorites: {e}")
            return []

    @staticmethod
    def record_apply(user_id: int, job_id: int) -> bool:
        """応募を記録"""
        return UserInteractionTracker.track_interaction(user_id, job_id, 'apply')

    @staticmethod
    def has_applied(user_id: int, job_id: int) -> bool:
        """応募済みかチェック"""
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            cur.execute("""
                SELECT COUNT(*) FROM user_interactions
                WHERE user_id = %s AND job_id = %s AND interaction_type = 'apply'
            """, (user_id, job_id))

            count = cur.fetchone()[0]
            cur.close()
            conn.close()

            return count > 0
        except Exception as e:
            print(f"Error checking apply: {e}")
            return False

    @staticmethod
    def get_user_interaction_summary(user_id: int) -> Dict[str, Any]:
        """ユーザーの行動サマリーを取得"""
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT * FROM user_interaction_summary
                WHERE user_id = %s
            """, (user_id,))

            summary = cur.fetchone()
            cur.close()
            conn.close()

            return dict(summary) if summary else {}
        except Exception as e:
            print(f"Error getting interaction summary: {e}")
            return {}


class ChatHistoryManager:
    """チャット履歴管理クラス"""

    @staticmethod
    def save_message(
        user_id: int,
        message_type: str,
        message_text: str,
        extracted_intent: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        チャットメッセージを保存

        Args:
            user_id: ユーザーID
            message_type: メッセージタイプ ('user' or 'bot')
            message_text: メッセージ本文
            extracted_intent: AIが抽出した意図（JSON）
            session_id: セッションID

        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO chat_history (user_id, message_type, message_text, extracted_intent, session_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, message_type, message_text, json.dumps(extracted_intent) if extracted_intent else None, session_id))

            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving chat message: {e}")
            return False

    @staticmethod
    def get_chat_history(user_id: int, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        チャット履歴を取得

        Args:
            user_id: ユーザーID
            session_id: セッションID（指定しない場合は全履歴）
            limit: 取得件数

        Returns:
            チャット履歴のリスト
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            if session_id:
                cur.execute("""
                    SELECT * FROM chat_history
                    WHERE user_id = %s AND session_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, session_id, limit))
            else:
                cur.execute("""
                    SELECT * FROM chat_history
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, limit))

            history = cur.fetchall()
            cur.close()
            conn.close()

            return [dict(msg) for msg in history]
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return []

    @staticmethod
    def get_user_mentioned_jobs(user_id: int, limit: int = 20) -> List[int]:
        """
        ユーザーがチャットで言及した求人IDを取得

        Args:
            user_id: ユーザーID
            limit: 取得件数

        Returns:
            求人IDのリスト
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            cur.execute("""
                SELECT DISTINCT job_id
                FROM user_interactions
                WHERE user_id = %s AND interaction_type = 'chat_mention'
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, limit))

            job_ids = [row[0] for row in cur.fetchall()]
            cur.close()
            conn.close()

            return job_ids
        except Exception as e:
            print(f"Error getting mentioned jobs: {e}")
            return []


class QuestionResponseManager:
    """動的質問への回答管理クラス"""

    @staticmethod
    def save_response(
        user_id: int,
        question_id: int,
        response_text: str,
        normalized_response: Optional[str] = None,
        confidence_score: float = 0.0
    ) -> bool:
        """
        ユーザーの質問への回答を保存

        Args:
            user_id: ユーザーID
            question_id: 質問ID
            response_text: ユーザーの回答
            normalized_response: 正規化された回答
            confidence_score: 確信度スコア

        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            # UPSERT (既に回答がある場合は更新)
            cur.execute("""
                INSERT INTO user_question_responses (user_id, question_id, response_text, normalized_response, confidence_score)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, question_id)
                DO UPDATE SET
                    response_text = EXCLUDED.response_text,
                    normalized_response = EXCLUDED.normalized_response,
                    confidence_score = EXCLUDED.confidence_score,
                    created_at = CURRENT_TIMESTAMP
            """, (user_id, question_id, response_text, normalized_response, confidence_score))

            # 質問の使用回数を増やす
            cur.execute("""
                UPDATE dynamic_questions
                SET usage_count = usage_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (question_id,))

            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving question response: {e}")
            return False

    @staticmethod
    def get_user_responses(user_id: int) -> List[Dict[str, Any]]:
        """ユーザーの質問への回答一覧を取得"""
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT uqr.*, dq.question_text, dq.category
                FROM user_question_responses uqr
                JOIN dynamic_questions dq ON uqr.question_id = dq.id
                WHERE uqr.user_id = %s
                ORDER BY uqr.created_at DESC
            """, (user_id,))

            responses = cur.fetchall()
            cur.close()
            conn.close()

            return [dict(resp) for resp in responses]
        except Exception as e:
            print(f"Error getting user responses: {e}")
            return []

    @staticmethod
    def mark_question_as_effective(question_id: int) -> bool:
        """
        質問が有効だったことを記録（お気に入りや応募があった場合）

        Args:
            question_id: 質問ID

        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            cur.execute("""
                UPDATE dynamic_questions
                SET positive_response_count = positive_response_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (question_id,))

            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error marking question as effective: {e}")
            return False