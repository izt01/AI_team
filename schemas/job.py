"""
求人関連のPydanticスキーマ
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class JobCreate(BaseModel):
    """求人作成リクエスト"""
    job_title: str = Field(..., min_length=1, max_length=200)
    job_description: str
    employment_type: str
    location_prefecture: str
    location_city: Optional[str] = None
    salary_min: int = Field(..., ge=0)
    salary_max: int = Field(..., ge=0)
    required_skills: Optional[str] = None
    benefits: Optional[str] = None
    remote_option: Optional[str] = None
    flex_time: Optional[bool] = False
    side_job_allowed: Optional[bool] = False
    work_style_details: Optional[str] = None
    team_culture_details: Optional[str] = None
    growth_opportunities_details: Optional[str] = None
    additional_questions: Optional[Dict[str, Any]] = None


class JobUpdate(BaseModel):
    """求人更新リクエスト"""
    job_title: Optional[str] = None
    job_description: Optional[str] = None
    employment_type: Optional[str] = None
    location_prefecture: Optional[str] = None
    location_city: Optional[str] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    required_skills: Optional[str] = None
    benefits: Optional[str] = None
    remote_option: Optional[str] = None
    status: Optional[str] = None


class JobResponse(BaseModel):
    """求人レスポンス"""
    id: str
    company_id: str
    company_name: Optional[str] = None
    job_title: str
    job_description: str
    employment_type: str
    location_prefecture: str
    location_city: Optional[str] = None
    salary_min: int
    salary_max: int
    required_skills: Optional[str] = None
    benefits: Optional[str] = None
    remote_option: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class JobSearchRequest(BaseModel):
    """求人検索リクエスト"""
    job_title: Optional[str] = None
    location_prefecture: Optional[str] = None
    salary_min: Optional[int] = None
    remote_option: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class JobSearchResponse(BaseModel):
    """求人検索レスポンス"""
    total: int
    jobs: List[JobResponse]
    page: int
    limit: int
