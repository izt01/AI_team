"""
汎用ヘルパー関数
"""

from typing import Any, Dict
from datetime import datetime, date
from decimal import Decimal
import json


def serialize_for_json(obj: Any) -> Any:
    """
    JSONシリアライズできない型を変換
    
    Args:
        obj: 変換対象オブジェクト
        
    Returns:
        変換後のオブジェクト
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    return obj


def clean_dict_for_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    辞書をJSONシリアライズ可能に変換
    
    Args:
        data: 変換対象の辞書
        
    Returns:
        変換後の辞書
    """
    return serialize_for_json(data)


def merge_accumulated_insights(
    current_insights: Dict[str, Any],
    new_intent: Dict[str, Any]
) -> Dict[str, Any]:
    """
    蓄積された洞察と新しい意図をマージ
    
    Args:
        current_insights: 現在の蓄積洞察
        new_intent: 新しいユーザー意図
        
    Returns:
        マージ後の洞察
    """
    merged = {
        "keywords": list(set(
            current_insights.get("keywords", []) + 
            new_intent.get("keywords", [])
        )),
        "pain_points": list(set(
            current_insights.get("pain_points", []) + 
            new_intent.get("pain_points", [])
        )),
        "flexible_needs": list(set(
            current_insights.get("flexible_needs", []) + 
            new_intent.get("flexible_needs", [])
        )),
        "explicit_preferences": {
            **current_insights.get("explicit_preferences", {}),
            **new_intent.get("explicit_preferences", {})
        },
        "implicit_values": {
            **current_insights.get("implicit_values", {}),
            **new_intent.get("implicit_values", {})
        }
    }
    
    return merged


def format_job_for_display(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    求人情報を表示用にフォーマット
    
    Args:
        job: 求人情報
        
    Returns:
        フォーマット済み求人情報
    """
    return {
        "id": job.get("id"),
        "job_title": job.get("job_title"),
        "company_name": job.get("company_name"),
        "location": f"{job.get('location_prefecture', '')} {job.get('location_city', '')}".strip(),
        "salary_range": f"{job.get('salary_min', 0)}-{job.get('salary_max', 0)}万円",
        "remote_option": job.get("remote_option", "情報なし"),
        "employment_type": job.get("employment_type"),
        "description_preview": (job.get("job_description", "")[:100] + "...") 
            if job.get("job_description") and len(job.get("job_description", "")) > 100 
            else job.get("job_description", ""),
    }


def validate_email(email: str) -> bool:
    """
    簡易的なメールアドレスバリデーション
    
    Args:
        email: メールアドレス
        
    Returns:
        有効ならTrue
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def paginate_results(
    items: list,
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """
    結果をページネーション
    
    Args:
        items: アイテムリスト
        page: ページ番号（1始まり）
        per_page: ページあたりのアイテム数
        
    Returns:
        ページネーション情報
    """
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }
