"""
会話内容からマッチ度をスコアリングするサービス
"""

import os
from typing import Dict, Any, List
from openai import OpenAI

from models.chat_models import ScoringInput, ScoringResult


class ScoringService:
    """会話内容から求人マッチ度をスコアリング"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
    
    def calculate_score(self, scoring_input: ScoringInput) -> ScoringResult:
        """
        会話内容からマッチ度を計算
        
        Args:
            scoring_input: スコアリング入力
            
        Returns:
            ScoringResult: スコアリング結果
        """
        
        # システムプロンプト
        system_prompt = self._build_scoring_prompt(scoring_input)
        
        # OpenAI APIでスコア計算
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "会話内容を分析して、マッチ度スコア（0-100）を計算してください。"}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # スコアを抽出
            score = self._extract_score(result_text)
            
            # キーワードを抽出
            keywords = self._extract_keywords(scoring_input)
            
            # 80%以上かチェック
            should_show = score >= 80.0
            
            return ScoringResult(
                score=score,
                matched_keywords=keywords,
                reasoning=result_text,
                should_show_jobs=should_show
            )
            
        except Exception as e:
            print(f"❌ スコア計算エラー: {e}")
            # フォールバック: ルールベーススコア
            return self._fallback_scoring(scoring_input)
    
    def _build_scoring_prompt(self, scoring_input: ScoringInput) -> str:
        """スコアリング用プロンプトを構築"""
        
        prefs = scoring_input.user_preferences
        history = scoring_input.conversation_history
        
        # 会話履歴をテキスト化
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in history[-10:]  # 直近5ターン
        ])
        
        prompt = f"""あなたは求人マッチングの専門家です。
求職者の希望と会話内容から、どれだけ詳細な情報が集まったかを0-100のスコアで評価してください。

【登録済み情報】
- 希望職種: {prefs.get('job_title', '未設定')}
- 希望勤務地: {prefs.get('location', '未設定')}
- 希望年収: {prefs.get('salary_min', '未設定')}万円〜

【会話履歴】
{conversation_text}

【スコアリング基準】
- 0-20点: 基本情報のみ（登録情報のみ）
- 21-40点: 具体的なスキル・経験が1-2個判明
- 41-60点: スキル、働き方、環境のうち2つが明確
- 61-80点: スキル、働き方、環境、キャリア目標のうち3つが明確
- 81-100点: 求人を推薦できる十分な情報（4つ以上の要素が明確）

以下の形式で出力してください：
スコア: [数値]
理由: [簡潔な説明]
"""
        return prompt
    
    def _extract_score(self, result_text: str) -> float:
        """結果テキストからスコアを抽出"""
        import re
        
        # "スコア: 75" のような形式を探す
        match = re.search(r'スコア[：:]\s*(\d+)', result_text)
        if match:
            return float(match.group(1))
        
        # "75点" のような形式を探す
        match = re.search(r'(\d+)\s*点', result_text)
        if match:
            return float(match.group(1))
        
        # 数字のみ
        match = re.search(r'\b(\d{1,3})\b', result_text)
        if match:
            score = float(match.group(1))
            if 0 <= score <= 100:
                return score
        
        return 50.0  # デフォルト
    
    def _extract_keywords(self, scoring_input: ScoringInput) -> List[str]:
        """会話からキーワードを抽出"""
        
        keywords = []
        
        # ユーザーメッセージのみを抽出
        user_messages = [
            msg['content'] 
            for msg in scoring_input.conversation_history 
            if msg['role'] == 'user'
        ]
        
        all_text = " ".join(user_messages)
        
        # キーワードパターン
        keyword_patterns = {
            'skills': ['React', 'Python', 'JavaScript', 'Photoshop', 'Illustrator', 'Figma', 'HTML', 'CSS'],
            'work_style': ['リモート', 'フレックス', '週3', '週4', '在宅'],
            'environment': ['少人数', 'スタートアップ', 'ベンチャー', '大企業'],
            'experience': ['経験', '実務', 'プロジェクト', 'チーム']
        }
        
        for category, patterns in keyword_patterns.items():
            for pattern in patterns:
                if pattern.lower() in all_text.lower():
                    keywords.append(pattern)
        
        return list(set(keywords))[:10]  # 重複削除、最大10個
    
    def _fallback_scoring(self, scoring_input: ScoringInput) -> ScoringResult:
        """フォールバック: ルールベースのスコアリング"""
        
        # ターン数ベースのスコア
        turn_count = len([m for m in scoring_input.conversation_history if m['role'] == 'user'])
        base_score = min(turn_count * 10, 70)
        
        # キーワードボーナス
        keywords = self._extract_keywords(scoring_input)
        keyword_bonus = len(keywords) * 3
        
        final_score = min(base_score + keyword_bonus, 100)
        
        return ScoringResult(
            score=float(final_score),
            matched_keywords=keywords,
            reasoning=f"ターン数: {turn_count}, キーワード: {len(keywords)}個",
            should_show_jobs=final_score >= 80
        )
