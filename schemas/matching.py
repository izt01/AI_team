"""
マッチング関連のPydanticスキーマ
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ChatMessage(BaseModel):
    """チャットメッセージ"""
    message: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """チャットレスポンス"""
    ai_message: str
    recommendations: Optional[List[Dict[str, Any]]] = None
    next_question: Optional[str] = None
    conversation_id: Optional[str] = None
    turn_number: int
    current_score: Optional[float] = 0.0  # マッチ度スコアを追加


class MatchingScore(BaseModel):
    """マッチングスコア"""
    job_id: str
    score: int = Field(..., ge=0, le=100)
    reasoning: str
    matched_features: List[str]
    concerns: List[str]


class RecommendationRequest(BaseModel):
    """おすすめ求人リクエスト"""
    limit: int = Field(10, ge=1, le=50)
    min_score: int = Field(60, ge=0, le=100)


class RecommendationResponse(BaseModel):
    """おすすめ求人レスポンス"""
    recommendations: List[Dict[str, Any]]
    total_count: int
    user_preferences: Optional[Dict[str, Any]] = None


class UserIntent(BaseModel):
    """ユーザー意図"""
    keywords: List[str]
    pain_points: List[str]
    flexible_needs: List[str]
    explicit_preferences: Dict[str, Any]
    implicit_values: Dict[str, Any]
    confidence: float = Field(..., ge=0.0, le=1.0)


class ConversationHistory(BaseModel):
    """会話履歴"""
    conversation_id: str
    user_id: str
    messages: List[Dict[str, Any]]
    accumulated_insights: Dict[str, Any]
    created_at: datetime
    updated_at: datetime