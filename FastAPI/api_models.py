"""
Pydanticモデル - ユーザー・求人関連
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================
# ユーザープロファイル関連
# ============================================

class UserProfileUpdateRequest(BaseModel):
    """ユーザープロファイル更新リクエスト"""
    job_title: Optional[str] = Field(None, max_length=100, description="希望職種")
    location_prefecture: Optional[str] = Field(None, max_length=50, description="希望勤務地（都道府県）")
    salary_min: Optional[int] = Field(None, ge=0, description="希望最低年収（万円）")
    intent_label: Optional[str] = Field(None, description="意図ラベル（カンマ区切り）")

    class Config:
        json_schema_extra = {
            "example": {
                "job_title": "Webエンジニア",
                "location_prefecture": "東京都",
                "salary_min": 500,
                "intent_label": "リモートワーク,フレックス"
            }
        }


class UserProfileResponse(BaseModel):
    """ユーザープロファイルレスポンス"""
    user_id: int
    job_title: Optional[str]
    location_prefecture: Optional[str]
    salary_min: Optional[int]
    intent_label: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# 求人関連
# ============================================

class JobCreateRequest(BaseModel):
    """求人登録リクエスト"""
    job_title: str = Field(..., min_length=1, max_length=200, description="職種名")
    salary_min: int = Field(..., ge=0, description="最低年収（万円）")
    salary_max: int = Field(..., ge=0, description="最高年収（万円）")
    location_prefecture: Optional[str] = Field(None, max_length=50, description="勤務地（都道府県）")
    bonus: Optional[str] = Field(None, description="ボーナス情報")
    overtime: Optional[str] = Field(None, description="残業情報")
    workplace_atmosphere: Optional[str] = Field(None, description="職場雰囲気")

    class Config:
        json_schema_extra = {
            "example": {
                "job_title": "バックエンドエンジニア",
                "salary_min": 500,
                "salary_max": 800,
                "location_prefecture": "東京都",
                "bonus": "年2回",
                "overtime": "月20時間以内",
                "workplace_atmosphere": "フラットな組織"
            }
        }


class JobResponse(BaseModel):
    """求人情報レスポンス"""
    id: str
    company_id: str
    company_name: Optional[str] = None
    job_title: str
    salary_min: int
    salary_max: int
    location_prefecture: Optional[str]
    intent_labels: Optional[str]
    click_count: Optional[int] = 0
    favorite_count: Optional[int] = 0
    apply_count: Optional[int] = 0
    view_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """求人一覧レスポンス"""
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int


# ============================================
# チャット関連
# ============================================

class ChatMessageRequest(BaseModel):
    """チャットメッセージ送信リクエスト"""
    message: str = Field(..., min_length=1, description="メッセージ本文")
    session_id: Optional[str] = Field(None, description="セッションID")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "リモートワーク可能な求人を探しています",
                "session_id": "a1b2c3d4-e5f6-7890"
            }
        }


class ChatMessageResponse(BaseModel):
    """チャットメッセージレスポンス"""
    bot_message: str = Field(..., description="ボットの応答")
    extracted_intent: Optional[Dict[str, Any]] = Field(None, description="抽出された意図")
    recommendations: Optional[List[JobResponse]] = Field(None, description="推薦求人リスト")
    next_question: Optional[str] = Field(None, description="次の質問")
    session_id: str = Field(..., description="セッションID")


class ChatHistoryResponse(BaseModel):
    """チャット履歴レスポンス"""
    id: int
    user_id: int
    message_type: str
    message_text: str
    extracted_intent: Optional[Dict[str, Any]]
    session_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# 推薦関連
# ============================================

class RecommendationRequest(BaseModel):
    """推薦リクエスト"""
    user_id: int = Field(..., description="ユーザーID")
    top_k: Optional[int] = Field(10, ge=1, le=100, description="推薦件数")
    exclude_job_ids: Optional[List[str]] = Field(None, description="除外する求人IDリスト")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "top_k": 10,
                "exclude_job_ids": []
            }
        }


class RecommendationResponse(BaseModel):
    """推薦レスポンス"""
    job: JobResponse
    score: float = Field(..., description="推薦スコア")
    reason: Optional[str] = Field(None, description="推薦理由")
    match_type: str = Field(..., description="マッチングタイプ（collaborative/content/hybrid）")


class RecommendationListResponse(BaseModel):
    """推薦リスト応答"""
    recommendations: List[RecommendationResponse]
    total: int
    user_id: int


# ============================================
# 行動追跡関連
# ============================================

class InteractionRequest(BaseModel):
    """行動記録リクエスト"""
    user_id: int = Field(..., description="ユーザーID")
    job_id: str = Field(..., description="求人ID")
    interaction_type: str = Field(..., description="行動タイプ（click/favorite/apply/view）")
    interaction_value: Optional[float] = Field(0.0, description="行動値（閲覧時間など）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="追加情報")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "interaction_type": "click",
                "interaction_value": 0.0,
                "metadata": {"from": "recommendation"}
            }
        }


class InteractionResponse(BaseModel):
    """行動記録レスポンス"""
    success: bool
    message: str


class FavoriteResponse(BaseModel):
    """お気に入り求人レスポンス"""
    id: str
    job_title: str
    location_prefecture: Optional[str]
    salary_min: int
    salary_max: int
    company_name: str
    favorited_at: datetime

    class Config:
        from_attributes = True


# ============================================
# 動的質問関連
# ============================================

class QuestionResponse(BaseModel):
    """質問レスポンス"""
    id: int
    question_key: str
    question_text: str
    category: str
    question_type: Optional[str]
    usage_count: Optional[int] = 0
    effectiveness_score: Optional[float] = 0.0

    class Config:
        from_attributes = True


class QuestionAnswerRequest(BaseModel):
    """質問回答リクエスト"""
    user_id: int = Field(..., description="ユーザーID")
    question_id: int = Field(..., description="質問ID")
    response_text: str = Field(..., description="ユーザーの回答")
    normalized_response: Optional[str] = Field(None, description="正規化された回答")
    confidence_score: Optional[float] = Field(0.0, ge=0.0, le=1.0, description="確信度スコア")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "question_id": 5,
                "response_text": "はい、リモートワークを希望します",
                "normalized_response": "true",
                "confidence_score": 0.95
            }
        }


class QuestionAnswerResponse(BaseModel):
    """質問回答レスポンス"""
    success: bool
    message: str


class UserResponseResponse(BaseModel):
    """ユーザー回答履歴レスポンス"""
    id: int
    user_id: int
    question_id: int
    question_text: str
    category: str
    response_text: str
    normalized_response: Optional[str]
    confidence_score: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True