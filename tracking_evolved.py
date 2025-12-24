"""
進化型AI求人マッチングシステム - ユーザー行動追跡モジュール v3.0

【主要機能】
1. スコア履歴の追跡（会話ごとのスコア変化を記録）
2. 抽出情報の蓄積（AIが抽出したユーザー情報を保存）
3. 会話ターンの管理
4. 終了条件の判定データ収集
5. 従来の行動追跡（クリック、お気に入り、応募）
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json
from typing import Optional, Dict, List, Any
from db_config import get_db_conn


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 進化型システム専用クラス
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConversationTracker:
    """会話追跡クラス（進化型システム専用）"""
    
    @staticmethod
    def save_turn_data(
        user_id: int,
        session_id: str,
        turn_number: int,
        user_message: str,
        bot_message: str,
        extracted_info: Dict[str, Any],
        top_score: float,
        top_match_percentage: float,
        candidate_count: int
    ) -> bool:
        """
        1ターン分のデータを保存
        
        Args:
            user_id: ユーザーID
            session_id: セッションID
            turn_number: ターン番号（1-10）
            user_message: ユーザーの発言
            bot_message: ボットの応答
            extracted_info: 抽出された情報
            top_score: トップスコア
            top_match_percentage: トップマッチ度（%）
            candidate_count: 候補数
            
        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            
            # conversation_turns テーブルに保存
            cur.execute("""
                INSERT INTO conversation_turns (
                    user_id, session_id, turn_number,
                    user_message, bot_message, extracted_info,
                    top_score, top_match_percentage, candidate_count,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                user_id, session_id, turn_number,
                user_message, bot_message,
                json.dumps(extracted_info, ensure_ascii=False),
                top_score, top_match_percentage, candidate_count
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"✅ ターン{turn_number}のデータを保存しました")
            return True
            
        except Exception as e:
            print(f"❌ ターンデータ保存エラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def save_extracted_insights(
        user_id: int,
        session_id: str,
        extracted_info: Dict[str, Any]
    ) -> bool:
        """
        抽出された情報を蓄積保存
        
        会話を通じて得られた情報を累積的に保存
        
        Args:
            user_id: ユーザーID
            session_id: セッションID
            extracted_info: 抽出情報
            
        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 既存の蓄積情報を取得
            cur.execute("""
                SELECT insights FROM user_insights
                WHERE user_id = %s AND session_id = %s
            """, (user_id, session_id))
            
            row = cur.fetchone()
            
            if row and row['insights']:
                # 既存情報とマージ
                existing_insights = row['insights']
                
                # explicit_preferences をマージ
                existing_prefs = existing_insights.get('explicit_preferences', {})
                new_prefs = extracted_info.get('explicit_preferences', {})
                merged_prefs = {**existing_prefs, **new_prefs}
                
                # implicit_values をマージ（最新の値で上書き）
                existing_values = existing_insights.get('implicit_values', {})
                new_values = extracted_info.get('implicit_values', {})
                merged_values = {**existing_values, **new_values}
                
                # pain_points を追加
                existing_pains = existing_insights.get('pain_points', [])
                new_pains = extracted_info.get('pain_points', [])
                merged_pains = list(set(existing_pains + new_pains))
                
                # keywords を追加
                existing_keywords = existing_insights.get('keywords', [])
                new_keywords = extracted_info.get('keywords', [])
                merged_keywords = list(set(existing_keywords + new_keywords))
                
                merged_insights = {
                    'explicit_preferences': merged_prefs,
                    'implicit_values': merged_values,
                    'pain_points': merged_pains,
                    'keywords': merged_keywords,
                    'confidence': extracted_info.get('confidence', 0.5)
                }
                
                # 更新
                cur.execute("""
                    UPDATE user_insights
                    SET insights = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND session_id = %s
                """, (json.dumps(merged_insights, ensure_ascii=False), user_id, session_id))
                
            else:
                # 新規作成
                cur.execute("""
                    INSERT INTO user_insights (user_id, session_id, insights, created_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                """, (user_id, session_id, json.dumps(extracted_info, ensure_ascii=False)))
            
            conn.commit()
            cur.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ 情報蓄積エラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def get_accumulated_insights(user_id: int, session_id: str) -> Dict[str, Any]:
        """
        蓄積された情報を取得
        
        Args:
            user_id: ユーザーID
            session_id: セッションID
            
        Returns:
            蓄積された情報
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT insights FROM user_insights
                WHERE user_id = %s AND session_id = %s
            """, (user_id, session_id))
            
            row = cur.fetchone()
            cur.close()
            conn.close()
            
            if row and row['insights']:
                return row['insights']
            else:
                return {
                    'explicit_preferences': {},
                    'implicit_values': {},
                    'pain_points': [],
                    'keywords': []
                }
                
        except Exception as e:
            print(f"❌ 情報取得エラー: {e}")
            return {}
    
    @staticmethod
    def save_session_summary(
        user_id: int,
        session_id: str,
        total_turns: int,
        end_reason: str,
        final_match_percentage: float,
        presented_jobs: List[str]
    ) -> bool:
        """
        セッション終了時のサマリーを保存
        
        Args:
            user_id: ユーザーID
            session_id: セッションID
            total_turns: 総ターン数
            end_reason: 終了理由
            final_match_percentage: 最終マッチ度
            presented_jobs: 提示した求人IDリスト
            
        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO conversation_sessions (
                    user_id, session_id, total_turns,
                    end_reason, final_match_percentage,
                    presented_jobs, ended_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                user_id, session_id, total_turns,
                end_reason, final_match_percentage,
                json.dumps(presented_jobs)
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"✅ セッションサマリーを保存: {total_turns}ターン, 理由={end_reason}")
            return True
            
        except Exception as e:
            print(f"❌ セッションサマリー保存エラー: {e}")
            return False


class ScoreHistoryTracker:
    """スコア履歴追跡クラス"""
    
    @staticmethod
    def record_score(
        user_id: int,
        session_id: str,
        turn_number: int,
        job_id: str,
        score: float,
        match_percentage: float,
        score_details: List[tuple]
    ) -> bool:
        """
        求人のスコアを記録
        
        Args:
            user_id: ユーザーID
            session_id: セッションID
            turn_number: ターン番号
            job_id: 求人ID
            score: スコア
            match_percentage: マッチ度
            score_details: スコア詳細（加点理由のリスト）
            
        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO score_history (
                    user_id, session_id, turn_number,
                    job_id, score, match_percentage,
                    score_details, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                user_id, session_id, turn_number,
                job_id, score, match_percentage,
                json.dumps(score_details, ensure_ascii=False)
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ スコア記録エラー: {e}")
            return False
    
    @staticmethod
    def get_score_history(
        user_id: int,
        session_id: str,
        job_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        スコア履歴を取得
        
        Args:
            user_id: ユーザーID
            session_id: セッションID
            job_id: 求人ID（指定しない場合は全求人）
            
        Returns:
            スコア履歴
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if job_id:
                cur.execute("""
                    SELECT * FROM score_history
                    WHERE user_id = %s AND session_id = %s AND job_id = %s
                    ORDER BY turn_number
                """, (user_id, session_id, job_id))
            else:
                cur.execute("""
                    SELECT * FROM score_history
                    WHERE user_id = %s AND session_id = %s
                    ORDER BY turn_number, score DESC
                """, (user_id, session_id))
            
            history = cur.fetchall()
            cur.close()
            conn.close()
            
            return [dict(h) for h in history]
            
        except Exception as e:
            print(f"❌ スコア履歴取得エラー: {e}")
            return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 従来の行動追跡クラス（既存機能を継承）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class UserInteractionTracker:
    """ユーザー行動追跡クラス"""

    @staticmethod
    def track_interaction(
        user_id: int,
        job_id: str,
        interaction_type: str,
        interaction_value: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        ユーザー行動を記録

        Args:
            user_id: ユーザーID
            job_id: 求人ID（UUID文字列）
            interaction_type: 行動タイプ ('click', 'favorite', 'apply', 'view')
            interaction_value: 数値（閲覧時間など）
            metadata: 追加情報（JSON）

        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO user_interactions (
                    user_id, job_id, interaction_type, 
                    interaction_value, metadata
                )
                VALUES (%s, %s::uuid, %s, %s, %s)
            """, (
                user_id, job_id, interaction_type, 
                interaction_value, 
                json.dumps(metadata) if metadata else None
            ))

            # company_profileの統計カウントも更新
            if interaction_type == 'click':
                cur.execute(
                    "UPDATE company_profile SET click_count = click_count + 1 WHERE id = %s::uuid", 
                    (job_id,)
                )
            elif interaction_type == 'favorite':
                cur.execute(
                    "UPDATE company_profile SET favorite_count = favorite_count + 1 WHERE id = %s::uuid", 
                    (job_id,)
                )
            elif interaction_type == 'apply':
                cur.execute(
                    "UPDATE company_profile SET apply_count = apply_count + 1 WHERE id = %s::uuid", 
                    (job_id,)
                )
            elif interaction_type == 'view':
                cur.execute(
                    "UPDATE company_profile SET view_count = view_count + 1 WHERE id = %s::uuid", 
                    (job_id,)
                )

            conn.commit()
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ 行動記録エラー: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def add_favorite(user_id: int, job_id: str) -> bool:
        """お気に入りに追加"""
        return UserInteractionTracker.track_interaction(user_id, job_id, 'favorite')

    @staticmethod
    def remove_favorite(user_id: int, job_id: str) -> bool:
        """お気に入りから削除"""
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            # 最新のfavorite記録を削除
            cur.execute("""
                DELETE FROM user_interactions
                WHERE id = (
                    SELECT id FROM user_interactions
                    WHERE user_id = %s AND job_id = %s::uuid AND interaction_type = 'favorite'
                    ORDER BY created_at DESC
                    LIMIT 1
                )
            """, (user_id, job_id))

            # company_profileの統計カウントも更新
            cur.execute(
                "UPDATE company_profile SET favorite_count = GREATEST(favorite_count - 1, 0) WHERE id = %s::uuid", 
                (job_id,)
            )

            conn.commit()
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ お気に入り削除エラー: {e}")
            return False

    @staticmethod
    def is_favorited(user_id: int, job_id: str) -> bool:
        """お気に入り済みかチェック"""
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            cur.execute("""
                SELECT COUNT(*) FROM user_interactions
                WHERE user_id = %s AND job_id = %s::uuid AND interaction_type = 'favorite'
            """, (user_id, job_id))

            count = cur.fetchone()[0]
            cur.close()
            conn.close()

            return count > 0
            
        except Exception as e:
            print(f"❌ お気に入りチェックエラー: {e}")
            return False

    @staticmethod
    def get_user_favorites(user_id: int) -> List[Dict[str, Any]]:
        """ユーザーのお気に入り求人一覧を取得"""
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT DISTINCT ON (ui.job_id)
                    cp.id::text as job_id, 
                    cp.job_title, 
                    cp.location_prefecture,
                    cp.salary_min, 
                    cp.salary_max,
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
            print(f"❌ お気に入り一覧取得エラー: {e}")
            return []

    @staticmethod
    def record_apply(user_id: int, job_id: str) -> bool:
        """応募を記録"""
        return UserInteractionTracker.track_interaction(user_id, job_id, 'apply')

    @staticmethod
    def has_applied(user_id: int, job_id: str) -> bool:
        """応募済みかチェック"""
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            cur.execute("""
                SELECT COUNT(*) FROM user_interactions
                WHERE user_id = %s AND job_id = %s::uuid AND interaction_type = 'apply'
            """, (user_id, job_id))

            count = cur.fetchone()[0]
            cur.close()
            conn.close()

            return count > 0
            
        except Exception as e:
            print(f"❌ 応募チェックエラー: {e}")
            return False


class ChatHistoryManager:
    """チャット履歴管理クラス"""

    @staticmethod
    def save_message(
        user_id: int,
        session_id: str,
        sender: str,
        message: str,
        extracted_intent: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        チャットメッセージを保存

        Args:
            user_id: ユーザーID
            session_id: セッションID
            sender: 送信者 ('user' or 'bot')
            message: メッセージ本文
            extracted_intent: AIが抽出した意図（JSON）

        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO chat_history (
                    user_id, session_id, sender, message, 
                    extracted_intent, created_at
                )
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                user_id, session_id, sender, message, 
                json.dumps(extracted_intent, ensure_ascii=False) if extracted_intent else None
            ))

            conn.commit()
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ チャット保存エラー: {e}")
            return False

    @staticmethod
    def get_chat_history(
        user_id: int, 
        session_id: Optional[str] = None, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
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
                    ORDER BY created_at
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
            print(f"❌ チャット履歴取得エラー: {e}")
            return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# テーブル作成（必要に応じて）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_tables_if_not_exist():
    """進化型システム用のテーブルを作成（存在しない場合）"""
    
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        
        # conversation_turns テーブル
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_id VARCHAR(100) NOT NULL,
                turn_number INTEGER NOT NULL,
                user_message TEXT,
                bot_message TEXT,
                extracted_info JSONB,
                top_score FLOAT,
                top_match_percentage FLOAT,
                candidate_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # user_insights テーブル
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_insights (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_id VARCHAR(100) NOT NULL,
                insights JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, session_id)
            )
        """)
        
        # conversation_sessions テーブル
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_id VARCHAR(100) NOT NULL UNIQUE,
                total_turns INTEGER,
                end_reason VARCHAR(50),
                final_match_percentage FLOAT,
                presented_jobs JSONB,
                ended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # score_history テーブル
        cur.execute("""
            CREATE TABLE IF NOT EXISTS score_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_id VARCHAR(100) NOT NULL,
                turn_number INTEGER NOT NULL,
                job_id VARCHAR(100) NOT NULL,
                score FLOAT,
                match_percentage FLOAT,
                score_details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # インデックス作成
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_turns_session 
            ON conversation_turns(user_id, session_id)
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_score_history_session 
            ON score_history(user_id, session_id, turn_number)
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ 進化型システム用テーブルを確認/作成しました")
        
    except Exception as e:
        print(f"❌ テーブル作成エラー: {e}")
        import traceback
        traceback.print_exc()


# モジュール読み込み時にテーブル作成
create_tables_if_not_exist()