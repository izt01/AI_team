"""
AIによる動的質問生成サービス
"""

import os
from typing import Dict, Any, List
from openai import OpenAI

from models.chat_models import QuestionContext, GeneratedQuestion


class QuestionGenerator:
    """OpenAI APIを使用して質問を動的に生成"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
    
    def generate_question(self, context: QuestionContext) -> GeneratedQuestion:
        """
        コンテキストに基づいて次の質問を生成
        
        Args:
            context: 質問生成のコンテキスト
            
        Returns:
            GeneratedQuestion: 生成された質問
        """
        
        # システムプロンプト
        system_prompt = self._build_system_prompt(context)
        
        # 会話履歴を構築
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 過去の会話を追加
        for msg in context.conversation_history[-6:]:  # 直近3ターン
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # OpenAI APIで質問生成
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
            
            question_text = response.choices[0].message.content.strip()
            
            # 質問タイプと深掘りフラグを判定
            is_deep_dive = self._is_deep_dive_question(question_text, context)
            question_type = self._classify_question_type(question_text)
            
            return GeneratedQuestion(
                question=question_text,
                is_deep_dive=is_deep_dive,
                question_type=question_type
            )
            
        except Exception as e:
            print(f"❌ 質問生成エラー: {e}")
            # フォールバック質問
            return self._fallback_question(context)
    
    def _build_system_prompt(self, context: QuestionContext) -> str:
        """システムプロンプトを構築"""
        
        prefs = context.user_preferences
        turn = context.turn_count
        score = context.current_score
        
        # 会話履歴から既に聞いたテーマを抽出
        asked_themes = []
        for msg in context.conversation_history:
            if msg["role"] == "assistant":
                content = msg["content"]
                if "スキル" in content or "経験" in content or "ツール" in content:
                    asked_themes.append("スキル・経験")
                if "リモート" in content or "勤務" in content or "働き方" in content:
                    asked_themes.append("働き方")
                if "チーム" in content or "環境" in content or "社風" in content:
                    asked_themes.append("職場環境")
                if "将来" in content or "キャリア" in content or "目標" in content:
                    asked_themes.append("キャリア目標")
        
        asked_themes_str = "、".join(set(asked_themes)) if asked_themes else "なし"
        
        # 直前のユーザー回答を取得
        last_user_message = ""
        if context.conversation_history:
            user_messages = [msg for msg in context.conversation_history if msg.get("role") == "user"]
            if user_messages:
                last_user_message = user_messages[-1].get("content", "")
        
        # 深掘りモードの判定と指示
        if context.is_deep_dive_previous:
            # 前回深掘りした → 今回は新しいテーマ＋代替案提案
            mode = "alternative"
            mode_instruction = f"""
【重要指示】
前回は深掘り質問をしました。今回は以下のいずれかを行ってください：

A) 新しいテーマで質問する
   - 既に聞いたテーマ（{asked_themes_str}）以外から選ぶ

B) 代替案を提案する（推奨）
   - 前回の回答から本質的なニーズを読み取る
   - そのニーズを満たす別の選択肢を提案する
   
   例：
   ユーザー「リモートワークがいい」
   AI「なぜリモートワークを希望されますか？」
   ユーザー「満員電車に乗りたくない」
   AI「なるほど！通勤のストレスを避けたいんですね。それなら、フルリモートでなくても、
       勤務開始時間が遅い会社（例：10時始業）なら満員電車を避けられますが、
       そういった選択肢も検討されますか？」

**2回連続で同じテーマを深掘りしないでください。**
"""
        else:
            # 前回深掘りしていない → 深掘り可能
            mode = "deep_dive"
            mode_instruction = f"""
【重要指示】
前回のユーザー回答を深掘りしてください：

直前の回答: {last_user_message[:100]}...

深掘りのポイント：
1. 具体的な理由や背景を聞く
   - 「なぜそう思うのか」
   - 「どういう経験からそう考えるのか」

2. 具体例を求める
   - 「具体的にはどのような〜」
   - 「例えば〜」

3. 優先順位を確認する
   - 「その中で特に重視するのは」
   - 「どれくらい重要か」

ただし、既に十分に詳しい回答が得られている場合は、
新しいテーマ（{asked_themes_str}以外）に移ってください。
"""
        
        prompt = f"""あなたは求職者の本質的なニーズを理解し、最適な求人を提案する採用コンサルタントAIです。

【登録済み情報】
- 希望職種: {prefs.get('job_title', '未設定')}
- 希望勤務地: {prefs.get('location', '未設定')}
- 希望年収: {prefs.get('salary_min', '未設定')}万円〜

【現在の状況】
- ターン数: {turn}/10
- マッチ度: {score}%
- 既に聞いたテーマ: {asked_themes_str}
- 深掘り可能: {'いいえ（代替案提案モード）' if context.is_deep_dive_previous else 'はい'}

{mode_instruction}

【利用可能なテーマ】
- スキル・経験（具体的なツール、技術、実務経験、得意分野）
- 働き方（リモート、勤務時間、残業、フレックス）
- 職場環境（チームサイズ、社風、文化、開発プロセス）
- キャリア目標（将来やりたいこと、成長したい分野、目指すポジション）
- 条件の優先順維（何を最も重視するか、譲れない条件）

【応答形式】
1. 前回の回答を受けて、共感や理解を示す（1文）
2. 質問または代替案の提案（1〜2文）
3. 自然で会話的なトーンを保つ

次の応答を生成してください：
"""
        return prompt
    
    def _is_deep_dive_question(self, question: str, context: QuestionContext) -> bool:
        """質問が深掘りかどうかを判定"""
        
        # 前回のユーザー回答がない場合は深掘りではない
        if not context.conversation_history:
            return False
        
        # 直前のユーザー回答を取得
        user_messages = [msg for msg in context.conversation_history if msg["role"] == "user"]
        if not user_messages:
            return False
        
        last_user_message = user_messages[-1]["content"]
        
        # 深掘りのキーワード
        deep_dive_keywords = [
            "具体的に", "詳しく", "例えば", "もう少し", 
            "どのような", "なぜ", "理由", "経験"
        ]
        
        # 質問に深掘りキーワードが含まれているか
        has_keyword = any(keyword in question for keyword in deep_dive_keywords)
        
        # 前回の回答から50文字以内の言葉が質問に含まれている（話題の継続）
        words_from_last = [word for word in last_user_message.split() if len(word) > 2]
        has_continuation = any(word in question for word in words_from_last[:5])
        
        return has_keyword or has_continuation
    
    def _classify_question_type(self, question: str) -> str:
        """質問タイプを分類"""
        
        if any(word in question for word in ["スキル", "技術", "ツール", "経験"]):
            return "skill"
        elif any(word in question for word in ["リモート", "勤務", "働き方", "残業"]):
            return "environment"
        elif any(word in question for word in ["将来", "キャリア", "目標", "成長"]):
            return "career_goal"
        elif any(word in question for word in ["優先", "重視", "条件", "大切"]):
            return "priority"
        else:
            return "general"
    
    def _fallback_question(self, context: QuestionContext) -> GeneratedQuestion:
        """フォールバック質問"""
        
        turn = context.turn_count
        
        # ターン数に応じた質問
        fallback_questions = [
            "具体的にどのようなスキルや経験をお持ちですか？",
            "理想の職場環境について教えてください。",
            "キャリアで今後どのように成長していきたいですか？",
            "転職先を選ぶ上で、最も重視する条件は何ですか？"
        ]
        
        question_text = fallback_questions[min(turn % len(fallback_questions), len(fallback_questions) - 1)]
        
        return GeneratedQuestion(
            question=question_text,
            is_deep_dive=False,
            question_type="general"
        )