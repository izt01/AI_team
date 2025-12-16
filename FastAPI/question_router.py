"""
動的質問関連APIルーター
- 質問の取得・生成
- ユーザー回答の記録
- 回答履歴の取得
"""

from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional

from models.api_models import (
    QuestionResponse,
    QuestionAnswerRequest,
    QuestionAnswerResponse,
    UserResponseResponse,
)
from dynamic_questions import QuestionSelector, QuestionGenerator
from tracking import QuestionResponseManager

router = APIRouter()


@router.get("/all", response_model=List[QuestionResponse])
async def get_all_questions():
    """
    全質問取得
    
    登録されている全ての質問を取得します。
    有効性スコアの高い順にソートされます。
    """
    try:
        questions = QuestionSelector.get_all_questions()
        
        return [QuestionResponse(**q) for q in questions]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"質問取得エラー: {str(e)}"
        )


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: int):
    """
    質問詳細取得
    
    指定したIDの質問を取得します。
    """
    try:
        question = QuestionSelector.get_question_by_id(question_id)
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="質問が見つかりません"
            )
        
        return QuestionResponse(**question)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"質問取得エラー: {str(e)}"
        )


@router.get("/key/{question_key}", response_model=QuestionResponse)
async def get_question_by_key(question_key: str):
    """
    質問取得（キー指定）
    
    question_keyで質問を取得します。
    """
    try:
        question = QuestionSelector.get_question_by_key(question_key)
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="質問が見つかりません"
            )
        
        return QuestionResponse(**question)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"質問取得エラー: {str(e)}"
        )


@router.get("/next/{user_id}", response_model=Optional[QuestionResponse])
async def get_next_question(user_id: int):
    """
    次の質問取得
    
    ユーザーの回答履歴を基に、次に尋ねるべき質問を選択します。
    未回答の質問の中から、有効性スコアが高いものを返します。
    """
    try:
        # 現在の検索結果は空リストとして渡す（実際の実装では取得）
        search_results = []
        
        question = QuestionSelector.select_next_question(
            user_id=user_id,
            search_results=search_results
        )
        
        if not question:
            return None
        
        return QuestionResponse(**question)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"次の質問取得エラー: {str(e)}"
        )


@router.post("/answer", response_model=QuestionAnswerResponse)
async def save_answer(request: QuestionAnswerRequest):
    """
    質問への回答保存
    
    ユーザーの質問への回答を保存します。
    既に同じ質問に回答している場合は上書きします（UPSERT）。
    """
    try:
        success = QuestionResponseManager.save_response(
            user_id=request.user_id,
            question_id=request.question_id,
            response_text=request.response_text,
            normalized_response=request.normalized_response,
            confidence_score=request.confidence_score,
        )
        
        if success:
            return QuestionAnswerResponse(
                success=True,
                message="回答を保存しました"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="回答の保存に失敗しました"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"回答保存エラー: {str(e)}"
        )


@router.get("/responses/{user_id}", response_model=List[UserResponseResponse])
async def get_user_responses(user_id: int):
    """
    ユーザー回答一覧取得
    
    指定したユーザーの全ての質問への回答を取得します。
    """
    try:
        responses = QuestionResponseManager.get_user_responses(user_id=user_id)
        
        return [UserResponseResponse(**resp) for resp in responses]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"回答一覧取得エラー: {str(e)}"
        )


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_questions():
    """
    動的質問生成
    
    求人データを分析して新しい質問を自動生成します。
    管理者用の機能です。
    """
    try:
        questions = QuestionGenerator.generate_questions_from_jobs()
        saved_count = QuestionGenerator.save_generated_questions(questions)
        
        return {
            "status": "success",
            "generated_questions": len(questions),
            "saved": saved_count,
            "message": f"{saved_count}件の質問を生成・保存しました"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"質問生成エラー: {str(e)}"
        )


@router.put("/{question_id}/mark-effective", response_model=QuestionAnswerResponse)
async def mark_question_effective(question_id: int):
    """
    質問を有効としてマーク
    
    この質問が有効だったことを記録します。
    お気に入りや応募があった場合に呼び出されます。
    """
    try:
        success = QuestionResponseManager.mark_question_as_effective(question_id)
        
        if success:
            return QuestionAnswerResponse(
                success=True,
                message="質問を有効としてマークしました"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="マーキングに失敗しました"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"マーキングエラー: {str(e)}"
        )