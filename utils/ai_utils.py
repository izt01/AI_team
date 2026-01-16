"""
AI関連のユーティリティ関数
"""

from openai import OpenAI
import json
from typing import Dict, Any, List
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_user_intent(message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
    """
    ユーザーの発言から意図を抽出
    
    Args:
        message: ユーザーメッセージ
        conversation_history: 会話履歴
        
    Returns:
        抽出された意図
    """
    
    history_text = ""
    if conversation_history:
        history_text = "\n過去の会話:\n" + "\n".join([
            f"{'ユーザー' if h.get('role') == 'user' else 'AI'}: {h.get('message', '')}"
            for h in conversation_history[-5:]
        ])
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """あなたは求人マッチングシステムのアシスタントです。
ユーザーの発言から以下の情報を抽出してください：

1. keywords: 重要なキーワード（職種、スキル、技術など）
2. pain_points: 現在の不満や避けたいこと
3. flexible_needs: 柔軟な要望や希望
4. explicit_preferences: 明示的な希望条件
5. implicit_values: 暗黙の価値観や優先度
6. confidence: 抽出の確信度（0.0-1.0）

JSON形式で返答してください。"""
                },
                {
                    "role": "user",
                    "content": f"メッセージ: {message}\n{history_text}"
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        print(f"❌ 意図抽出エラー: {e}")
        return {
            "keywords": [],
            "pain_points": [],
            "flexible_needs": [],
            "explicit_preferences": {},
            "implicit_values": {},
            "confidence": 0.0
        }


def generate_ai_response(
    user_message: str,
    context: Dict[str, Any],
    conversation_history: List[Dict] = None
) -> str:
    """
    AIレスポンスを生成
    
    Args:
        user_message: ユーザーメッセージ
        context: コンテキスト情報
        conversation_history: 会話履歴
        
    Returns:
        AI生成メッセージ
    """
    
    history_messages = []
    if conversation_history:
        for h in conversation_history[-5:]:
            role = "user" if h.get('role') == 'user' else "assistant"
            history_messages.append({
                "role": role,
                "content": h.get('message', '')
            })
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """あなたは求人マッチングアシスタントです。
ユーザーの希望を理解し、最適な求人を提案してください。
自然で親しみやすい会話を心がけてください。"""
                },
                *history_messages,
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"❌ AIレスポンス生成エラー: {e}")
        return "申し訳ございません。エラーが発生しました。もう一度お試しください。"


def get_embedding(text: str) -> List[float]:
    """
    テキストのembeddingを取得
    
    Args:
        text: テキスト
        
    Returns:
        embedding ベクトル
    """
    try:
        response = client.embeddings.create(
            input=[text],
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Embedding取得エラー: {e}")
        return []


def analyze_job_compatibility(
    user_intent: Dict[str, Any],
    job: Dict[str, Any],
    accumulated_insights: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    求人との相性を分析
    
    Args:
        user_intent: ユーザー意図
        job: 求人情報
        accumulated_insights: 蓄積された洞察
        
    Returns:
        相性分析結果
    """
    
    job_text = f"""
職種: {job.get('job_title', '')}
企業: {job.get('company_name', '')}
勤務地: {job.get('location_prefecture', '')} {job.get('location_city', '')}
年収: {job.get('salary_min', 0)}-{job.get('salary_max', 0)}万円
リモート: {job.get('remote_option', 'なし')}
業務内容: {job.get('job_description', '')}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """求人とユーザーの相性を0-100点で評価してください。

評価基準:
- 希望条件との一致度
- 不満点の解消度
- キャリアゴールとの整合性

JSON形式で返答:
{
    "score": 85,
    "reasoning": "理由",
    "matched_features": ["特徴1", "特徴2"],
    "concerns": ["懸念点1"]
}"""
                },
                {
                    "role": "user",
                    "content": f"ユーザー意図:\n{json.dumps(user_intent, ensure_ascii=False)}\n\n求人:\n{job_text}"
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        print(f"❌ 相性分析エラー: {e}")
        return {
            "score": 50,
            "reasoning": "エラーが発生しました",
            "matched_features": [],
            "concerns": []
        }


def generate_scout_question(
    user_message: str,
    base_conditions: Dict[str, Any],
    conversation_history: List[Dict] = None,
    turn_count: int = 1
) -> str:
    """
    スカウト用の次の質問を動的に生成
    
    Args:
        user_message: ユーザーの最新メッセージ
        base_conditions: 基本条件（職種、勤務地、年収）
        conversation_history: 会話履歴
        turn_count: 現在のターン数
        
    Returns:
        AIが生成した次の質問
    """
    
    # 会話履歴を構築
    history_messages = []
    if conversation_history:
        for msg in conversation_history[-5:]:  # 直近5件
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                history_messages.append({
                    "role": role,
                    "content": content
                })
    
    # 基本条件の情報
    base_info = f"""
【基本条件】
- 職種: {base_conditions.get('job_title', '未設定')}
- 勤務地: {base_conditions.get('location', '未設定')}
- 最低年収: {base_conditions.get('salary_min', '未設定')}万円
"""
    
    # システムプロンプト
    system_prompt = f"""あなたは企業の採用担当者をサポートするAIアシスタントです。
候補者の条件を詳しくヒアリングして、最適な人材をマッチングします。

{base_info}

これらの基本条件は**既に設定済み**です。同じことを聞かないでください。

【あなたの役割】
1. ユーザーの回答を理解し、それに応じた適切な追加質問をする
2. 自然で親しみやすい会話を心がける
3. **基本条件以外の**以下の情報を段階的に聞き出す：
   - 勤務形態（リモート、出社頻度、フレックスなど）
   - 技術スタック・ツール・スキル（基本条件の職種に関連するもの）
   - 経験年数・レベル
   - チーム規模・組織文化
   - その他の重要な条件

【現在のターン】: {turn_count}/3

【重要なガイドライン】
- **職種、勤務地、年収については既に設定済みなので聞かない**
- ユーザーの回答に基づいて、関連する質問をする
- YES/NOで答えられる質問と、自由回答の質問を組み合わせる
- 質問は1つずつ、簡潔に
- 専門用語を使う場合は、例を添える
- **3ターン目では「十分な情報が集まりました。候補者を検索しています...」と伝える**"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                *history_messages,
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        ai_response = response.choices[0].message.content
        print(f"🤖 OpenAI応答生成成功: {ai_response[:100]}...")
        return ai_response
        
    except Exception as e:
        print(f"❌ OpenAI API エラー: {e}")
        
        # フォールバック: 固定の質問
        fallback_questions = {
            1: "ありがとうございます。リモートワークは必須ですか？それとも柔軟に対応可能ですか？",
            2: "承知しました。使用している技術スタックやツールについて教えてください。",
            3: "なるほど。求める候補者の経験年数はどのくらいを想定していますか？",
        }
        
        return fallback_questions.get(
            turn_count,
            "ありがとうございます。十分な情報が集まりました。候補者を検索しています..."
        )
