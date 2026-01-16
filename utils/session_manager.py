"""
チャットセッション管理サービス
"""

from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import json

from models.chat_models import ChatSession
from config.database import get_db_conn


class SessionManager:
    """セッション管理（DBベース）"""
    
    @staticmethod
    def create_session(user_id: str, user_preferences: Dict[str, Any]) -> ChatSession:
        """新しいセッションを作成"""
        session_id = str(uuid.uuid4())
        
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            turn_count=0,
            current_score=0.0,
            is_deep_dive_previous=False,
            deep_dive_count=0,
            conversation_history=[],
            user_preferences=user_preferences
        )
        
        # DBに保存
        SessionManager._save_to_db(session)
        
        return session
    
    @staticmethod
    def get_session(session_id: str) -> Optional[ChatSession]:
        """セッションを取得"""
        conn = get_db_conn()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT session_data FROM chat_sessions
                WHERE session_id = %s
            """, (session_id,))
            
            result = cur.fetchone()
            
            if result:
                # PostgreSQLのJSONBフィールドは既にdictとして返される
                session_data = result[0]
                if isinstance(session_data, str):
                    # 万が一文字列の場合のみパース
                    session_data = json.loads(session_data)
                return ChatSession(**session_data)
            
            return None
            
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def update_session(session: ChatSession) -> None:
        """セッションを更新"""
        session.updated_at = datetime.now()
        SessionManager._save_to_db(session)
    
    @staticmethod
    def add_turn(
        session: ChatSession,
        user_message: str,
        ai_message: str,
        is_deep_dive: bool,
        new_score: float
    ) -> None:
        """ターンを追加"""
        # ターン数を増やす
        session.turn_count += 1
        
        # 会話履歴に追加
        session.conversation_history.append({
            "role": "user",
            "content": user_message,
            "turn": str(session.turn_count)  # 文字列に変換
        })
        session.conversation_history.append({
            "role": "assistant",
            "content": ai_message,
            "turn": str(session.turn_count)  # 文字列に変換
        })
        
        # スコア更新
        session.current_score = new_score
        
        # 深掘りフラグ更新
        if is_deep_dive:
            session.deep_dive_count += 1
        else:
            session.deep_dive_count = 0  # リセット
        
        session.is_deep_dive_previous = is_deep_dive
        
        # DBに保存
        SessionManager.update_session(session)
    
    @staticmethod
    def _save_to_db(session: ChatSession) -> None:
        """DBに保存"""
        conn = get_db_conn()
        cur = conn.cursor()
        
        try:
            session_data = session.model_dump()
            session_data['created_at'] = session_data['created_at'].isoformat()
            session_data['updated_at'] = session_data['updated_at'].isoformat()
            
            cur.execute("""
                INSERT INTO chat_sessions (session_id, user_id, session_data, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (session_id) 
                DO UPDATE SET 
                    session_data = EXCLUDED.session_data,
                    updated_at = EXCLUDED.updated_at
            """, (
                session.session_id,
                session.user_id,
                json.dumps(session_data),
                session.updated_at
            ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            print(f"❌ セッション保存エラー: {e}")
            raise
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_user_preferences(user_id: str) -> Dict[str, Any]:
        """ユーザーのStep2情報を取得"""
        conn = get_db_conn()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT job_title, location_prefecture, salary_min
                FROM user_preferences_profile
                WHERE user_id = %s
            """, (user_id,))
            
            result = cur.fetchone()
            
            if result:
                return {
                    'job_title': result[0],
                    'location': result[1],
                    'salary_min': result[2]
                }
            
            return {}
            
        finally:
            cur.close()
            conn.close()


# chat_sessionsテーブルのスキーマ（必要に応じて実行）
"""
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at);
"""