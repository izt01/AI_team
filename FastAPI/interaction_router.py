"""
行動追跡関連APIルーター
- ユーザー行動の記録（クリック、お気に入り、応募等）
- お気に入り管理
- 行動サマリー取得
"""

from fastapi import APIRouter, HTTPException, status
from typing import List

from models.api_models import (
    InteractionRequest,
    InteractionResponse,
    FavoriteResponse,
)
from tracking import UserInteractionTracker

router = APIRouter()


@router.post("/track", response_model=InteractionResponse)
async def track_interaction(request: InteractionRequest):
    """
    ユーザー行動記録
    
    ユーザーの求人に対する行動（クリック、閲覧、お気に入り、応募等）を記録します。
    
    **interaction_type:**
    - `click`: クリック
    - `view`: 閲覧
    - `favorite`: お気に入り
    - `apply`: 応募
    - `chat_mention`: チャット内で言及
    """
    try:
        success = UserInteractionTracker.track_interaction(
            user_id=request.user_id,
            job_id=request.job_id,
            interaction_type=request.interaction_type,
            interaction_value=request.interaction_value,
            metadata=request.metadata,
        )
        
        if success:
            return InteractionResponse(
                success=True,
                message="行動を記録しました"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="行動の記録に失敗しました"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"行動記録エラー: {str(e)}"
        )


@router.post("/favorites/add", response_model=InteractionResponse)
async def add_favorite(user_id: int, job_id: str):
    """
    お気に入り追加
    
    指定した求人をお気に入りに追加します。
    """
    try:
        success = UserInteractionTracker.add_favorite(
            user_id=user_id,
            job_id=job_id
        )
        
        if success:
            return InteractionResponse(
                success=True,
                message="お気に入りに追加しました"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="お気に入りの追加に失敗しました"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"お気に入り追加エラー: {str(e)}"
        )


@router.delete("/favorites/remove", response_model=InteractionResponse)
async def remove_favorite(user_id: int, job_id: str):
    """
    お気に入り削除
    
    指定した求人をお気に入りから削除します。
    """
    try:
        success = UserInteractionTracker.remove_favorite(
            user_id=user_id,
            job_id=job_id
        )
        
        if success:
            return InteractionResponse(
                success=True,
                message="お気に入りから削除しました"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="お気に入りの削除に失敗しました"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"お気に入り削除エラー: {str(e)}"
        )


@router.get("/favorites/{user_id}", response_model=List[FavoriteResponse])
async def get_favorites(user_id: int):
    """
    お気に入り一覧取得
    
    ユーザーのお気に入り求人一覧を取得します。
    """
    try:
        favorites = UserInteractionTracker.get_user_favorites(user_id=user_id)
        
        return [FavoriteResponse(**fav) for fav in favorites]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"お気に入り取得エラー: {str(e)}"
        )


@router.get("/favorites/{user_id}/check/{job_id}")
async def check_favorite(user_id: int, job_id: str):
    """
    お気に入り状態確認
    
    指定した求人がお気に入りに登録されているかを確認します。
    """
    try:
        is_favorited = UserInteractionTracker.is_favorited(
            user_id=user_id,
            job_id=job_id
        )
        
        return {
            "user_id": user_id,
            "job_id": job_id,
            "is_favorited": is_favorited
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"お気に入り状態確認エラー: {str(e)}"
        )


@router.post("/apply", response_model=InteractionResponse)
async def record_apply(user_id: int, job_id: str):
    """
    応募記録
    
    求人への応募を記録します。
    """
    try:
        success = UserInteractionTracker.record_apply(
            user_id=user_id,
            job_id=job_id
        )
        
        if success:
            return InteractionResponse(
                success=True,
                message="応募を記録しました"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="応募の記録に失敗しました"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"応募記録エラー: {str(e)}"
        )


@router.get("/apply/{user_id}/check/{job_id}")
async def check_applied(user_id: int, job_id: str):
    """
    応募状態確認
    
    指定した求人に応募済みかを確認します。
    """
    try:
        has_applied = UserInteractionTracker.has_applied(
            user_id=user_id,
            job_id=job_id
        )
        
        return {
            "user_id": user_id,
            "job_id": job_id,
            "has_applied": has_applied
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"応募状態確認エラー: {str(e)}"
        )


@router.get("/summary/{user_id}")
async def get_interaction_summary(user_id: int):
    """
    行動サマリー取得
    
    ユーザーの行動統計情報を取得します。
    """
    try:
        summary = UserInteractionTracker.get_user_interaction_summary(user_id=user_id)
        
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"サマリー取得エラー: {str(e)}"
        )