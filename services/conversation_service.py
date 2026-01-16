"""
会話管理サービス
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from psycopg2.extras import RealDictCursor, Json
from config.database import get_db_conn
from utils.ai_utils import extract_user_intent, generate_ai_response
from utils.helpers import merge_accumulated_insights
import uuid
import json


class ConversationService:
    """会話管理サービスクラス"""
    
    @staticmethod
    def create_conversation(user_id: str) -> str:
        """
        新しい会話セッションを作成
        
        Args:
            user_id: ユーザーID
            
        Returns:
            会話ID
        """
        import uuid
        session_id = str(uuid.uuid4())
        conn = get_db_conn()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO conversation_sessions 
            (user_id, session_id, started_at, ended_at)
            VALUES (%s, %s, %s, %s)
        """, (
            user_id,
            session_id,
            datetime.now(),
            datetime.now()
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return session_id
    
    @staticmethod
    def get_conversation(session_id: str) -> Optional[Dict[str, Any]]:
        """
        会話セッション取得
        
        Args:
            session_id: 会話ID
            
        Returns:
            会話データ
        """
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM conversation_sessions
            WHERE session_id = %s
        """, (session_id,))
        
        session = cur.fetchone()
        cur.close()
        conn.close()
        
        return dict(session) if session else None
    
    @staticmethod
    def add_message(
        session_id: str,
        user_id: str,
        role: str,
        message: str,
        extracted_info: Optional[Dict[str, Any]] = None,
        turn_number: int = 1
    ) -> Dict[str, Any]:
        """
        メッセージを追加
        
        Args:
            session_id: 会話ID
            user_id: ユーザーID
            role: ロール（user/assistant）
            message: メッセージ
            extracted_info: 抽出情報
            turn_number: ターン番号
            
        Returns:
            追加されたメッセージ
        """
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # メッセージ挿入
        if role == "user":
            cur.execute("""
                INSERT INTO conversation_logs
                (session_id, user_id, turn_number, user_message, extracted_intent, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                session_id,
                user_id,
                turn_number,
                message,
                Json(extracted_info) if extracted_info else None,
                datetime.now()
            ))
        else:
            cur.execute("""
                UPDATE conversation_logs
                SET ai_response = %s
                WHERE session_id = %s AND turn_number = %s
                RETURNING *
            """, (
                message,
                session_id,
                turn_number
            ))
        
        new_message = cur.fetchone()
        
        # セッションの更新日時を更新
        cur.execute("""
            UPDATE conversation_sessions
            SET ended_at = %s
            WHERE session_id = %s
        """, (datetime.now(), session_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return dict(new_message) if new_message else {}
    
    @staticmethod
    def get_conversation_history(
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        会話履歴を取得
        
        Args:
            session_id: 会話ID
            limit: 取得件数
            
        Returns:
            メッセージリスト
        """
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM conversation_logs
            WHERE session_id = %s
            ORDER BY turn_number ASC
            LIMIT %s
        """, (session_id, limit))
        
        messages = cur.fetchall()
        cur.close()
        conn.close()
        
        return [dict(msg) for msg in messages]
    
    @staticmethod
    def process_user_message(
        user_id: str,
        message: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ユーザーメッセージを処理
        
        Args:
            user_id: ユーザーID
            message: ユーザーメッセージ
            session_id: 会話ID（なければ新規作成）
            
        Returns:
            処理結果（AIレスポンス、抽出情報など）
        """
        
        # 会話セッション確認/作成
        if not session_id:
            session_id = ConversationService.create_conversation(user_id)
        
        # 会話履歴取得
        history = ConversationService.get_conversation_history(session_id, limit=10)
        
        # 現在のターン番号
        turn_number = len([h for h in history if h.get('user_message')]) + 1
        
        # ユーザー意図抽出
        extracted_intent = extract_user_intent(
            message,
            conversation_history=[
                {
                    "role": "user" if h.get("user_message") else "assistant",
                    "message": h.get("user_message") or h.get("ai_response")
                }
                for h in history
            ]
        )
        
        # メッセージ保存（ユーザーメッセージ）
        ConversationService.add_message(
            session_id=session_id,
            user_id=user_id,
            role="user",
            message=message,
            extracted_info=extracted_intent,
            turn_number=turn_number
        )
        
        # AIレスポンス生成
        ai_response = generate_ai_response(
            user_message=message,
            context={
                "turn_number": turn_number
            },
            conversation_history=[
                {
                    "role": "user" if h.get("user_message") else "assistant",
                    "message": h.get("user_message") or h.get("ai_response")
                }
                for h in history
            ]
        )
        
        # AIメッセージ保存
        ConversationService.add_message(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            message=ai_response,
            turn_number=turn_number
        )
        
        return {
            "session_id": session_id,
            "ai_message": ai_response,
            "extracted_intent": extracted_intent,
            "turn_number": turn_number
        }
