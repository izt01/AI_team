"""
企業関連のPydanticスキーマ
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class CompanyRegister(BaseModel):
    """企業登録リクエスト"""
    company_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=6)
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None


class CompanyLogin(BaseModel):
    """企業ログインリクエスト"""
    email: EmailStr
    password: str


class CompanyProfile(BaseModel):
    """企業プロフィール"""
    company_id: str
    company_name: str
    email: str
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ScoutSearchRequest(BaseModel):
    """スカウト候補検索リクエスト"""
    job_id: str
    limit: int = Field(20, ge=1, le=100)
    min_match_score: int = Field(70, ge=0, le=100)


class ScoutCandidate(BaseModel):
    """スカウト候補者"""
    user_id: str
    name: str
    match_score: int
    matched_features: List[str]
    profile_summary: Optional[str] = None


class ScoutSearchResponse(BaseModel):
    """スカウト検索レスポンス"""
    job_id: str
    candidates: List[ScoutCandidate]
    total_count: int


class ScoutMessageRequest(BaseModel):
    """スカウトメッセージ送信リクエスト"""
    user_id: str
    job_id: str
    message: Optional[str] = None


class ScoutMessageResponse(BaseModel):
    """スカウトメッセージレスポンス"""
    scout_id: str
    status: str
    sent_at: datetime


class EnrichmentRequest(BaseModel):
    """エンリッチメントリクエスト"""
    job_id: str
    missing_fields: List[str]


class EnrichmentResponse(BaseModel):
    """エンリッチメントレスポンス"""
    request_id: str
    status: str
    generated_questions: List[Dict[str, Any]]
