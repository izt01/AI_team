"""
チャット関連APIルーター
- チャットメッセージ送受信
- チャット履歴管理
"""

from fastapi import APIRouter, HTTPException, status, Query
from psycopg2.extras import RealDictCursor
from openai import OpenAI
import uuid
import json
import os
from typing import Optional, List

from models.api_models import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
)
from db_config import get_db_conn
from tracking import ChatHistoryManager

router = APIRouter()

# OpenAI クライアントの初期化
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_intent_with_ai(user_message: str) -> dict:
    """AIでユーザーの意図を抽出"""
    prompt = f"""
ユーザーの発言から以下の情報を抽出してJSON形式で返してください:

ユーザー発言: {user_message}

抽出する情報:
- job_title: 職種
- location_prefecture: 勤務地（都道府県のみ）
- salary_min: 最低年収（数値）
- その他、ユーザーが言及した条件

出力はJSON形式のみ返してください。
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        result_text = response.choices[0].message.content.strip()

        # JSON部分を抽出
        import re
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(0)

        intent = json.loads(result_text)
        return intent

    except Exception as e:
        print(f"Error extracting intent: {e}")
        return {}


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(user_id: int, request: ChatMessageRequest):
    """
    チャットメッセージ送信
    
    ユーザーのメッセージを受け取り、AIが応答を生成します。
    必要に応じて意図抽出や求人推薦も行います。
    """
    try:
        # セッションIDの生成または使用
        session_id = request.session_id or str(uuid.uuid4())
        
        # ユーザーメッセージを保存
        ChatHistoryManager.save_message(
            user_id=user_id,
            message_type='user',
            message_text=request.message,
            session_id=session_id
        )
        
        # AIで意図を抽出
        intent = extract_intent_with_ai(request.message)
        
        # 簡単な応答を生成（実際の実装ではより高度な処理）
        bot_response = "メッセージを受け取りました。"
        
        if intent:
            bot_response = f"以下の条件で求人を検索します:\n"
            if 'job_title' in intent:
                bot_response += f"- 職種: {intent['job_title']}\n"
            if 'location_prefecture' in intent:
                bot_response += f"- 勤務地: {intent['location_prefecture']}\n"
            if 'salary_min' in intent:
                bot_response += f"- 希望年収: {intent['salary_min']}万円以上\n"
        
        # ボット応答を保存
        ChatHistoryManager.save_message(
            user_id=user_id,
            message_type='bot',
            message_text=bot_response,
            extracted_intent=intent,
            session_id=session_id
        )
        
        return ChatMessageResponse(
            bot_message=bot_response,
            extracted_intent=intent,
            session_id=session_id,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"チャット処理エラー: {str(e)}"
        )


@router.get("/history/{user_id}", response_model=List[ChatHistoryResponse])
async def get_chat_history(
    user_id: int,
    session_id: Optional[str] = Query(None, description="セッションID"),
    limit: int = Query(50, ge=1, le=200, description="取得件数")
):
    """
    チャット履歴取得
    
    ユーザーのチャット履歴を取得します。
    セッションIDを指定すると特定セッションの履歴のみ取得できます。
    """
    try:
        history = ChatHistoryManager.get_chat_history(
            user_id=user_id,
            session_id=session_id,
            limit=limit
        )
        
        return [ChatHistoryResponse(**msg) for msg in history]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"チャット履歴取得エラー: {str(e)}"
        )


@router.delete("/history/{user_id}/session/{session_id}")
async def delete_chat_session(user_id: int, session_id: str):
    """
    チャットセッション削除
    
    指定したセッションのチャット履歴を削除します。
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        
        cur.execute("""
            DELETE FROM chat_history
            WHERE user_id = %s AND session_id = %s
        """, (user_id, session_id))
        
        deleted_count = cur.rowcount
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {
            "message": f"{deleted_count}件のメッセージを削除しました",
            "session_id": session_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"チャット履歴削除エラー: {str(e)}"
        )