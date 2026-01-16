"""
チャット関連のデータモデル
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatSession(BaseModel):
    """チャットセッション"""
    session_id: str
    user_id: str
    turn_count: int = 0
    current_score: float = 0.0
    score_history: List[float] = []  # スコア履歴（停滞検知用）
    is_deep_dive_previous: bool = False  # 前回が深掘り質問だったか
    deep_dive_count: int = 0  # 連続深掘り回数
    conversation_history: List[Dict[str, str]] = []
    user_preferences: Dict[str, Any] = {}  # Step2の情報
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class QuestionContext(BaseModel):
    """質問生成のコンテキスト"""
    user_preferences: Dict[str, Any]  # Step2の情報
    conversation_history: List[Dict[str, str]]
    current_score: float
    turn_count: int
    is_deep_dive_previous: bool


class GeneratedQuestion(BaseModel):
    """生成された質問"""
    question: str
    is_deep_dive: bool  # この質問が深掘りかどうか
    question_type: str  # 'skill', 'experience', 'environment', 'career_goal', etc.


class ScoringInput(BaseModel):
    """スコアリング入力"""
    user_preferences: Dict[str, Any]
    conversation_history: List[Dict[str, str]]
    latest_user_response: str


class ScoringResult(BaseModel):
    """スコアリング結果"""
    score: float  # 0-100
    matched_keywords: List[str]
    reasoning: str
    should_show_jobs: bool  # 求人を表示すべきか


class JobRecommendation(BaseModel):
    """求人推薦"""
    job_id: str
    job_title: str
    company_name: str
    match_score: float
    match_reasoning: str
    salary_min: Optional[int]
    salary_max: Optional[int]
    location: str
    remote_option: str


class ChatTurnResult(BaseModel):
    """1ターンの会話結果"""
    ai_message: str
    current_score: float
    turn_count: int
    should_show_jobs: bool
    jobs: Optional[List[JobRecommendation]] = None
    session_id: str