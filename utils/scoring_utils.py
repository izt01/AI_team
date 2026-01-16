"""
スコアリング関連のユーティリティ
元のrule_based_scoring.pyとai_matching_scoring_fix.pyを統合
"""

from typing import Dict, Any, List, Tuple
import re
from utils.ai_utils import analyze_job_compatibility


# ルールベーススコアリングの重み
WEIGHTS = {
    "base": 40,
    "keyword_hit": 4,
    "flex_need_hit": 10,
    "remote_match": 12,
    "remote_mismatch": -8,
    "career_goal_hit": 10,
    "job_title_hit": 18,
    "culture_hit": 10,
    "location_hit": 6,
    "confidence_bonus": 8,
    "confidence_penalty": -8,
}

CONF_HIGH = 0.85
CONF_LOW = 0.35


def _norm(s: Any) -> str:
    """文字列正規化"""
    if s is None:
        return ""
    s = str(s)
    s = s.replace("\u3000", " ").strip()
    return s.lower()


def _contains(haystack: str, needle: str) -> bool:
    """部分一致判定"""
    if not haystack or not needle:
        return False
    return needle in haystack


def _extract_job_text(job: Dict[str, Any]) -> str:
    """求人のテキスト情報を集約"""
    candidates = [
        "job_title", "title", "position", "occupation", "role",
        "company", "company_name",
        "job_description", "description", "summary",
        "requirements", "required_skills", "skills",
        "industry", "tags",
        "location", "work_location", "prefecture", "city",
        "remote_work", "work_style",
        "employment_type",
    ]
    parts: List[str] = []
    for k in candidates:
        v = job.get(k)
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            parts.append(" ".join([_norm(x) for x in v if x is not None]))
        else:
            parts.append(_norm(v))
    return " ".join([p for p in parts if p]).strip()


def _get_remote_flag(job: Dict[str, Any]) -> str:
    """リモート可否を推定"""
    raw = _norm(job.get("remote_work") or job.get("remote") or job.get("work_style") or "")
    if not raw:
        return "unknown"
    
    if any(x in raw for x in ["可", "可能", "ok", "true", "yes", "リモート", "在宅"]):
        if any(x in raw for x in ["不可", "ng", "no", "false", "なし", "できない"]):
            return "no"
        if any(x in raw for x in ["一部", "週", "ハイブリッド", "部分"]):
            return "partial"
        return "yes"
    
    if any(x in raw for x in ["不可", "ng", "no", "false", "なし", "できない"]):
        return "no"
    
    return "unknown"


def rule_based_scoring(
    extracted_info: Dict[str, Any],
    job: Dict[str, Any],
    accumulated_insights: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    ルールベースのスコアリング
    
    Args:
        extracted_info: 抽出されたユーザー意図
        job: 求人情報
        accumulated_insights: 蓄積された洞察
        
    Returns:
        スコアリング結果
    """
    score = WEIGHTS["base"]
    matched_features: List[str] = []
    concerns: List[str] = []
    
    # キーワード一致
    keywords = extracted_info.get("keywords", [])
    job_text = _extract_job_text(job)
    
    keyword_hits = []
    for kw in keywords[:20]:
        kw_norm = _norm(kw)
        if len(kw_norm) >= 2 and _contains(job_text, kw_norm):
            keyword_hits.append(kw)
    
    if keyword_hits:
        score += WEIGHTS["keyword_hit"] * min(len(keyword_hits), 10)
        matched_features.append(f"キーワード一致: {', '.join(keyword_hits[:3])}")
    
    # 柔軟ニーズ
    needs = extracted_info.get("flexible_needs", [])
    for n in needs[:10]:
        n_norm = _norm(n)
        if len(n_norm) >= 2 and _contains(job_text, n_norm):
            score += WEIGHTS["flex_need_hit"]
            matched_features.append("柔軟ニーズに合致")
            break
    
    # リモート希望
    remote_pref = extracted_info.get("explicit_preferences", {}).get("remote_work")
    if remote_pref:
        remote_pref_norm = _norm(remote_pref)
        wants_remote = any(x in remote_pref_norm for x in ["希望", "したい", "あり", "可", "リモート"])
        
        if wants_remote:
            job_remote = _get_remote_flag(job)
            if job_remote == "yes":
                score += WEIGHTS["remote_match"]
                matched_features.append("リモート可")
            elif job_remote == "partial":
                score += int(WEIGHTS["remote_match"] * 0.6)
                matched_features.append("リモート一部可")
            elif job_remote == "no":
                score += WEIGHTS["remote_mismatch"]
                concerns.append("リモート希望だが不可の可能性")
    
    # 職種一致
    title = _norm(job.get("job_title", ""))
    job_change_req = extracted_info.get("job_change_request", {}) or {}
    new_titles = job_change_req.get("new_job_titles", [])
    
    for t in new_titles:
        t_norm = _norm(t)
        if t_norm and title and (t_norm in title or title in t_norm):
            score += WEIGHTS["job_title_hit"]
            matched_features.append("希望職種が一致")
            break
    
    # 勤務地
    pref = _norm(extracted_info.get("explicit_preferences", {}).get("location_prefecture", ""))
    city = _norm(extracted_info.get("explicit_preferences", {}).get("location_city", ""))
    
    if pref or city:
        job_loc = _norm(job.get("location", "") or job.get("work_location", ""))
        job_pref = _norm(job.get("prefecture", ""))
        job_city = _norm(job.get("city", ""))
        blob = " ".join([job_loc, job_pref, job_city]).strip()
        
        if pref and _contains(blob, pref):
            score += WEIGHTS["location_hit"]
            matched_features.append(f"勤務地（{pref}）が一致")
        
        if city and _contains(blob, city):
            score += WEIGHTS["location_hit"]
            matched_features.append(f"市区町村（{city}）が一致")
    
    # confidence補正
    conf = extracted_info.get("confidence")
    try:
        conf_f = float(conf) if conf is not None else None
    except:
        conf_f = None
    
    if conf_f is not None:
        if conf_f >= CONF_HIGH:
            score += WEIGHTS["confidence_bonus"]
            matched_features.append("回答の確信度が高い")
        elif conf_f <= CONF_LOW:
            score += WEIGHTS["confidence_penalty"]
            matched_features.append("回答の確信度が低い")
    
    # 0-100に正規化
    score = max(0, min(100, score))
    
    reasoning = " / ".join(matched_features[:5]) if matched_features else "現時点の条件から総合評価"
    
    return {
        "score": int(round(score)),
        "reasoning": reasoning,
        "matched_features": matched_features[:8],
        "concerns": concerns[:5],
    }


def ai_based_scoring(
    user_intent: Dict[str, Any],
    job: Dict[str, Any],
    accumulated_insights: Dict[str, Any] = None,
    turn_number: int = 1
) -> Dict[str, Any]:
    """
    AIベースのスコアリング
    
    Args:
        user_intent: ユーザー意図
        job: 求人情報
        accumulated_insights: 蓄積された洞察
        turn_number: 会話のターン数
        
    Returns:
        スコアリング結果
    """
    
    # 蓄積データを統合
    all_keywords = accumulated_insights.get('keywords', []) if accumulated_insights else []
    all_pain_points = accumulated_insights.get('pain_points', []) if accumulated_insights else []
    all_flexible_needs = accumulated_insights.get('flexible_needs', []) if accumulated_insights else []
    
    all_keywords.extend(user_intent.get('keywords', []))
    all_pain_points.extend(user_intent.get('pain_points', []))
    all_flexible_needs.extend(user_intent.get('flexible_needs', []))
    
    # 重複削除
    all_keywords = list(set(all_keywords))
    all_pain_points = list(set(all_pain_points))
    all_flexible_needs = list(set(all_flexible_needs))
    
    # 統合されたユーザー情報
    comprehensive_user_info = {
        "keywords": all_keywords,
        "pain_points": all_pain_points,
        "flexible_needs": all_flexible_needs,
        "explicit_preferences": user_intent.get('explicit_preferences', {}),
        "implicit_values": user_intent.get('implicit_values', {}),
    }
    
    # 情報量ボーナス
    info_richness = len(all_keywords) + len(all_pain_points) + len(all_flexible_needs)
    info_bonus = min(info_richness * 2, 20)
    
    # AI分析を実行
    result = analyze_job_compatibility(comprehensive_user_info, job, accumulated_insights)
    
    # ボーナス適用
    base_score = result.get('score', 50)
    final_score = min(base_score + info_bonus, 100)
    result['score'] = final_score
    result['info_bonus'] = info_bonus
    result['base_score'] = base_score
    
    return result


def hybrid_scoring(
    user_intent: Dict[str, Any],
    job: Dict[str, Any],
    accumulated_insights: Dict[str, Any] = None,
    use_ai: bool = True,
    turn_number: int = 1
) -> Dict[str, Any]:
    """
    ハイブリッドスコアリング（ルールベース + AI）
    
    Args:
        user_intent: ユーザー意図
        job: 求人情報
        accumulated_insights: 蓄積された洞察
        use_ai: AIスコアリングを使用するか
        turn_number: 会話のターン数
        
    Returns:
        スコアリング結果
    """
    
    # ルールベーススコア
    rule_result = rule_based_scoring(user_intent, job, accumulated_insights)
    
    if not use_ai:
        return rule_result
    
    # AIスコア
    try:
        ai_result = ai_based_scoring(user_intent, job, accumulated_insights, turn_number)
        
        # ハイブリッド（重み付け平均）
        hybrid_score = int(rule_result['score'] * 0.4 + ai_result['score'] * 0.6)
        
        return {
            "score": hybrid_score,
            "rule_score": rule_result['score'],
            "ai_score": ai_result['score'],
            "reasoning": ai_result.get('reasoning', rule_result['reasoning']),
            "matched_features": list(set(
                rule_result.get('matched_features', []) + 
                ai_result.get('matched_features', [])
            ))[:10],
            "concerns": list(set(
                rule_result.get('concerns', []) + 
                ai_result.get('concerns', [])
            ))[:5],
        }
    
    except Exception as e:
        print(f"⚠️ AIスコアリング失敗、ルールベースのみ使用: {e}")
        return rule_result
