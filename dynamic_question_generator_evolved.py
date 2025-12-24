"""
進化型AI求人マッチングシステム - 動的質問生成モジュール v3.0

【主要機能】
1. ユーザーの特性に応じた完全動的質問生成
2. 過去の会話履歴を踏まえた深掘り質問
3. 会話ターン数に応じた質問タイプの変化
4. 蓄積された情報を活用した質問生成
5. 候補求人の分布に基づく質問生成
"""

from openai import OpenAI
import json
import os
from typing import Dict, Any, Optional, List
from db_config import get_db_conn
from psycopg2.extras import RealDictCursor


class EvolvingQuestionGenerator:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def generate_next_question(
        self,
        user_id: int,
        session_id: str,
        conversation_turn: int,
        candidates: List[Dict],
        accumulated_insights: Dict,
        user_last_message: str
    ) -> str:
        """段階的な質問生成"""
            
        # 🔥 段階1: 基本情報（1-5ターン）
        if conversation_turn <= 5:
            if conversation_turn == 1:
                focus = "基本的な働き方の希望（リモート、チーム、環境）"
            elif conversation_turn == 2:
                focus = "コミュニケーションと連携のスタイル"
            elif conversation_turn == 3:
                focus = "職場の文化と雰囲気"
            elif conversation_turn == 4:
                focus = "具体的なツールと手法"
            else:  # conversation_turn == 5
                focus = "まとめと確認"
            
        # 🔥 段階2: 詳細情報（6-7ターン）
        elif conversation_turn <= 7:
            if conversation_turn == 6:
                focus = "スキルと成長の機会"
            else:  # conversation_turn == 7
                focus = "働き方の柔軟性と条件"
        
        # 🔥 段階3: 最終調整（8-9ターン）
        elif conversation_turn <= 9:
            if conversation_turn == 8:
                focus = "妥協点と優先順位"
            else:  # conversation_turn == 9
                focus = "最終確認と期待"
            
        # 🔥 段階4: 緊急時（10ターン）
        else:
            focus = "最終提案"
            
        # AIにフォーカスを伝えて質問生成
        prompt = f"""ユーザーは{focus}について話しています。
        今までの情報: {accumulated_insights}
        直前のメッセージ: {user_last_message}
            
        自然な流れで次の質問を1つだけ生成してください。
        前置きは不要で、質問だけを簡潔に。"""
            
        # 実際のAI呼び出し処理
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user", 
                        "content": user_last_message
                    }
                ],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ 質問生成エラー: {e}")
            # エラー時のフォールバック質問
            fallback_questions = {
                1: "あなたにとって理想の職場環境について教えてください。",
                2: "どのようなチームと働きたいですか？",
                3: "職場で重視することは何ですか？",
                4: "どのような成長機会を求めていますか？",
                5: "働き方で妥協できないことは何ですか？"
            }
            return fallback_questions.get(min(conversation_turn, 5), "もう少し詳しく教えてください。")
    
    def _get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """ユーザープロファイル取得"""
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT 
                    pd.user_name,
                    up.job_title,
                    up.location_prefecture,
                    up.salary_min
                FROM personal_date pd
                LEFT JOIN user_profile up ON pd.user_id = up.user_id
                WHERE pd.user_id = %s
            """, (user_id,))
            
            profile = cur.fetchone()
            cur.close()
            conn.close()
            
            return dict(profile) if profile else {}
            
        except Exception as e:
            print(f"❌ プロファイル取得エラー: {e}")
            return {}
    
    def _get_conversation_history(
        self, 
        user_id: int, 
        session_id: str
    ) -> List[Dict[str, str]]:
        """会話履歴取得"""
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT sender, message
                FROM chat_history
                WHERE user_id = %s AND session_id = %s
                ORDER BY created_at
            """, (user_id, session_id))
            
            history = cur.fetchall()
            cur.close()
            conn.close()
            
            return [dict(h) for h in history]
            
        except Exception as e:
            print(f"❌ 会話履歴取得エラー: {e}")
            return []
    
    def _analyze_candidates(
        self, 
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        候補求人の分布を分析
        
        候補の多様性を分析して、どの項目について質問すべきか判断
        """
        if not candidates:
            return {'has_diversity': False}
        
        analysis = {
            'total_count': len(candidates),
            'remote_work': {'full': 0, 'partial': 0, 'none': 0},
            'company_culture': {},
            'work_flexibility': {},
            'diversity_areas': []
        }
        
        # リモートワークの分布
        for job in candidates:
            remote = job.get('remote_work', 'none')
            if remote == 'full':
                analysis['remote_work']['full'] += 1
            elif remote == 'partial':
                analysis['remote_work']['partial'] += 1
            else:
                analysis['remote_work']['none'] += 1
        
        # 多様性チェック
        if analysis['remote_work']['full'] > 0 and analysis['remote_work']['none'] > 0:
            analysis['diversity_areas'].append({
                'topic': 'remote_work',
                'label': 'リモートワーク',
                'description': f"完全リモート{analysis['remote_work']['full']}件、出社{analysis['remote_work']['none']}件"
            })
        
        # 企業文化の分布（job_summaryから推測）
        keywords = {
            'フラット': 0,
            'スピード感': 0,
            'チームワーク': 0,
            '挑戦': 0
        }
        
        for job in candidates:
            summary = job.get('company_culture', '') or ''
            for keyword in keywords.keys():
                if keyword in summary:
                    keywords[keyword] += 1
        
        # キーワードに多様性があれば追加
        for keyword, count in keywords.items():
            if count > 0 and count < len(candidates):
                analysis['diversity_areas'].append({
                    'topic': 'culture',
                    'label': f'{keyword}な文化',
                    'description': f"{count}件の企業が{keyword}を重視"
                })
        
        analysis['has_diversity'] = len(analysis['diversity_areas']) > 0
        
        return analysis
    
    def _determine_conversation_phase(self, turn: int) -> str:
        """
        会話フェーズを判定
        
        Args:
            turn: ターン数（1-10）
            
        Returns:
            フェーズ ('exploration', 'deepening', 'confirmation')
        """
        if turn <= 3:
            return 'exploration'  # 探索フェーズ（広く聞く）
        elif turn <= 6:
            return 'deepening'    # 深掘りフェーズ（詳しく聞く）
        else:
            return 'confirmation' # 確認フェーズ（優先順位を明確化）
    
    def _generate_with_ai(
        self,
        user_profile: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        accumulated_insights: Dict[str, Any],
        candidates_analysis: Dict[str, Any],
        phase: str,
        conversation_turn: int,
        user_last_message: str
    ) -> str:
        """AIで質問を生成"""
        
        # フェーズごとの指示
        phase_instructions = {
            'exploration': """
【探索フェーズ（会話1-3回目）】
- オープンエンドな質問をしてください
- ユーザーの価値観や優先順位を広く理解する
- YES/NOで終わらない質問
- 理由や背景を聞く質問

例:
- 「理想の働き方について教えてください」
- 「キャリアで最も大切にしていることは何ですか？」
- 「その理由を詳しく教えていただけますか？」
""",
            'deepening': """
【深掘りフェーズ（会話4-6回目）】
- 前回の回答を深掘りする質問
- 具体的な希望を明確化する
- トレードオフを確認する質問
- **ユーザーの本質的なニーズを理解し、代替案を提案する**

例:
- 「リモートワークとオフィス勤務、どちらがより重要ですか？」
- 「年収と働きやすさ、優先順位をつけるとしたら？」
- 「その条件を満たすために、他の条件は妥協できますか？」
- 「〜が理由なら、△△という選択肢もありますが、いかがでしょうか？」（代替案提示）

**代替案の例:**
- 満員電車が嫌 → リモートワーク OR フレックスタイム（10時出社）
- 長時間通勤が嫌 → リモートワーク OR 職場近くに引っ越し可の企業
- 年収を上げたい → 高年収 OR ストックオプション・賞与充実
""",
            'confirmation': """
【確認フェーズ（会話7-10回目）】
- 最優先条件の最終確認
- 具体的な選択肢を提示して選んでもらう
- 迷っている点を明確化

例:
- 「A社とB社、どちらにより魅力を感じますか？」
- 「最も譲れない条件は何ですか？」
- 「これまでの話から、〜が重要だと理解しましたが、合っていますか？」
"""
        }
        
        # 過去の会話を整形
        history_text = ""
        if conversation_history:
            history_text = "\n".join([
                f"{'ユーザー' if h['sender'] == 'user' else 'AI'}: {h['message']}"
                for h in conversation_history[-6:]  # 最新6件
            ])
        
        # 蓄積された情報を整形
        insights_text = json.dumps(accumulated_insights, ensure_ascii=False, indent=2)
        
        # 候補分析を整形
        diversity_text = ""
        if candidates_analysis.get('has_diversity'):
            diversity_text = "\n【候補の多様性】\n"
            for area in candidates_analysis['diversity_areas'][:3]:
                diversity_text += f"- {area['label']}: {area['description']}\n"
        
        # プロンプト作成
        prompt = f"""あなたは優秀なキャリアカウンセラーです。
ユーザーとの会話を通じて、最適な求人を見つけるための質問をしてください。

【ユーザー情報】
- 名前: {user_profile.get('user_name', 'ユーザー')}さん
- 希望職種: {user_profile.get('job_title', '未設定')}
- 希望勤務地: {user_profile.get('location_prefecture', '未設定')}
- 希望年収: {user_profile.get('salary_min', 0)}万円以上

【会話の進行状況】
- 現在のターン: {conversation_turn}/10
- フェーズ: {phase}
- 候補求人数: {candidates_analysis.get('total_count', 0)}件

【過去の会話（最新6件）】
{history_text if history_text else '（まだ会話なし）'}

【これまでに抽出された情報】
{insights_text}

{diversity_text}

【ユーザーの最後の発言】
{user_last_message if user_last_message else '（初回）'}

{phase_instructions[phase]}

【重要な注意点】
1. 既に聞いた内容を繰り返さない
2. ユーザーの最後の発言を踏まえて深掘りする
3. 自然な会話の流れを保つ
4. 具体的で答えやすい質問にする
5. **質問の最後に必ず回答例を2-3個提示する**

【返答形式】
JSON形式で以下のように返してください:
{{
  "question_text": "質問文（200文字以内）",
  "examples": ["回答例1", "回答例2", "回答例3"],
  "reasoning": "この質問をする理由"
}}

**質問文の最後には必ず以下の形式で回答例を含めてください:**
「（例: 〜、〜、〜など）」

**回答例の作り方:**
- 具体的で実際に答えやすい例を提示
- ユーザーの状況に応じた例を選ぶ
- 2-3個の選択肢を提示

質問文のみを生成してください。前置きや説明は不要です。"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # JSON形式に対応したモデル
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは優秀なキャリアカウンセラーです。ユーザーに寄り添った質問をしてください。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            question_text = result.get('question_text', '')
            
            print(f"🤖 生成された質問: {question_text}")
            print(f"📝 理由: {result.get('reasoning', '')}")
            
            return question_text
            
        except Exception as e:
            print(f"❌ AI質問生成エラー: {e}")
            return self._get_fallback_question(conversation_turn)
    
    def _get_fallback_question(self, turn: int) -> str:
        """
        フォールバック質問（AIが失敗した時）
        
        Args:
            turn: ターン数
            
        Returns:
            フォールバック質問文
        """
        fallback_questions = {
            1: "理想の働き方について教えてください。どんな環境で働きたいですか？",
            2: "その理由を詳しく教えていただけますか？",
            3: "仕事で最も大切にしていることは何ですか？",
            4: "キャリアの目標について教えてください。",
            5: "働く上で、譲れない条件はありますか？",
            6: "チームや組織の雰囲気で重視することは？",
            7: "これまでの話を踏まえて、最優先の条件は何ですか？",
            8: "その条件を満たすために、他の条件は妥協できますか？",
            9: "理想の企業のイメージを教えてください。",
            10: "最後に、他に重視することはありますか？"
        }
        
        return fallback_questions.get(turn, "他に重視することはありますか？")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 互換性のための旧クラス名エイリアス
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DynamicQuestionGenerator(EvolvingQuestionGenerator):
    """
    旧バージョンとの互換性のためのエイリアス
    
    既存コードで DynamicQuestionGenerator を使用している場合、
    そのまま動作するようにする
    """
    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ユーティリティ関数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_question_generator(openai_api_key: str) -> EvolvingQuestionGenerator:
    """
    質問生成器を作成するヘルパー関数
    
    Args:
        openai_api_key: OpenAI APIキー
        
    Returns:
        質問生成器インスタンス
    """
    from openai import OpenAI
    client = OpenAI(api_key=openai_api_key)
    return EvolvingQuestionGenerator(client)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# テスト用コード
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    """テスト実行"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # テスト用のダミーデータ
    test_user_id = 1
    test_session_id = "test-session-123"
    test_turn = 1
    
    test_candidates = [
        {
            'job_id': 'job-1',
            'job_title': 'Webデザイナー',
            'company_name': 'テスト株式会社',
            'remote_work': 'full',
            'company_culture': 'フラットな組織'
        },
        {
            'job_id': 'job-2',
            'job_title': 'UIデザイナー',
            'company_name': 'サンプル株式会社',
            'remote_work': 'none',
            'company_culture': 'スピード感のある環境'
        }
    ]
    
    test_insights = {
        'explicit_preferences': {},
        'implicit_values': {},
        'pain_points': [],
        'keywords': []
    }
    
    # 質問生成器を作成
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        generator = create_question_generator(api_key)
        
        # 質問生成
        question = generator.generate_next_question(
            user_id=test_user_id,
            session_id=test_session_id,
            conversation_turn=test_turn,
            candidates=test_candidates,
            accumulated_insights=test_insights,
            user_last_message=""
        )
        
        print("\n" + "=" * 60)
        print("🤖 生成された質問:")
        print("=" * 60)
        print(question)
        print("=" * 60)
    else:
        print("❌ OPENAI_API_KEY が設定されていません")