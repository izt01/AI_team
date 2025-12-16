"""
完全動的質問生成システム
- 固定リストを使わず、AIが求人データとユーザーの状況から自由に質問を生成
- 類似ユーザーの成功パターンを参考にする
- 質問の有効性を追跡して改善
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI
import json
from typing import Dict, Any, Optional, List
import re
from db_config import get_db_conn


class DynamicQuestionGenerator:
    """完全動的質問生成クラス"""

    def __init__(self, openai_client: OpenAI):
        self.client = openai_client

    def generate_next_question(
        self, 
        user_id: int, 
        recommendations: List[Dict[str, Any]], 
        user_last_message: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        AIを使って次の質問を完全動的に生成
        
        Args:
            user_id: ユーザーID
            recommendations: 現在の推薦求人リスト
            user_last_message: ユーザーの最後のメッセージ
            
        Returns:
            生成された質問の辞書、または None
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 1. ユーザーの既存の回答履歴を取得
            cur.execute("""
                SELECT 
                    COALESCE(dq.question_key, 'question_' || uqr.question_id) as question_key,
                    uqr.response_text, 
                    uqr.normalized_response
                FROM user_question_responses uqr
                LEFT JOIN dynamic_questions dq ON uqr.question_id = dq.id
                WHERE uqr.user_id = %s
                ORDER BY uqr.created_at
            """, (user_id,))
            
            answered_questions = cur.fetchall()
            answered_summary = self._format_answered_questions(answered_questions)
            
            # 2. 求人の属性を分析
            if recommendations:
                job_ids = [str(job['id']) for job in recommendations[:50]]
                
                cur.execute("""
                    SELECT 
                        work_flexibility,
                        company_culture,
                        career_path
                    FROM job_attributes
                    WHERE job_id = ANY(%s::uuid[])
                """, (job_ids,))
                
                job_attributes = cur.fetchall()
            else:
                job_attributes = []
            
            # 3. 求人の多様性を分析
            diversity_analysis = self._analyze_job_diversity(job_attributes)
            
            # 4. 類似ユーザーの成功パターンを取得
            similar_users_patterns = self._get_similar_users_success_patterns(user_id, cur)
            
            # 5. ユーザープロファイルを取得
            cur.execute("""
                SELECT job_title, location_prefecture, salary_min
                FROM user_profile
                WHERE user_id = %s
            """, (user_id,))
            
            user_profile = cur.fetchone()
            
            cur.close()
            conn.close()
            
            # 6. AIに質問を生成させる
            question = self._generate_question_with_ai(
                user_profile=user_profile,
                answered_summary=answered_summary,
                diversity_analysis=diversity_analysis,
                similar_users_patterns=similar_users_patterns,
                recommendations_count=len(recommendations),
                user_last_message=user_last_message
            )
            
            return question
            
        except Exception as e:
            print(f"Error generating dynamic question: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _format_answered_questions(self, answered_questions: List[Dict]) -> str:
        """回答済み質問を整形"""
        if not answered_questions:
            return "【初回質問】ユーザーはまだ質問に答えていません。最初の質問を生成してください。"
        
        formatted = []
        for q in answered_questions:
            formatted.append(f"- {q['question_key']}: {q['response_text']}")
        
        return "\n".join(formatted)
    
    def _analyze_job_diversity(self, job_attributes: List[Dict]) -> Dict[str, Any]:
        """求人の多様性を分析"""
        if not job_attributes:
            return {"has_diversity": False, "summary": "求人データがありません"}
        
        analysis = {
            "total_jobs": len(job_attributes),
            "work_flexibility": {},
            "company_culture": {},
            "career_path": {},
            "diversity_areas": []
        }
        
        # 働き方の柔軟性
        remote_yes = sum(1 for attr in job_attributes if attr.get('work_flexibility', {}).get('remote') == True)
        remote_no = sum(1 for attr in job_attributes if attr.get('work_flexibility', {}).get('remote') == False)
        
        flex_yes = sum(1 for attr in job_attributes if attr.get('work_flexibility', {}).get('flex_time') == True)
        flex_no = sum(1 for attr in job_attributes if attr.get('work_flexibility', {}).get('flex_time') == False)
        
        side_job_yes = sum(1 for attr in job_attributes if attr.get('work_flexibility', {}).get('side_job') == True)
        side_job_no = sum(1 for attr in job_attributes if attr.get('work_flexibility', {}).get('side_job') == False)
        
        analysis['work_flexibility'] = {
            'remote': {'yes': remote_yes, 'no': remote_no},
            'flex_time': {'yes': flex_yes, 'no': flex_no},
            'side_job': {'yes': side_job_yes, 'no': side_job_no}
        }
        
        # 多様性のある項目を検出
        if remote_yes > 0 and remote_no > 0:
            analysis['diversity_areas'].append({
                'topic': 'remote',
                'label': 'リモートワーク',
                'yes_count': remote_yes,
                'no_count': remote_no
            })
        
        if flex_yes > 0 and flex_no > 0:
            analysis['diversity_areas'].append({
                'topic': 'flex_time',
                'label': 'フレックスタイム',
                'yes_count': flex_yes,
                'no_count': flex_no
            })
        
        if side_job_yes > 0 and side_job_no > 0:
            analysis['diversity_areas'].append({
                'topic': 'side_job',
                'label': '副業',
                'yes_count': side_job_yes,
                'no_count': side_job_no
            })
        
        # 企業規模
        company_sizes = {}
        for attr in job_attributes:
            size = attr.get('company_culture', {}).get('size')
            if size and size != 'unknown':
                company_sizes[size] = company_sizes.get(size, 0) + 1
        
        if len(company_sizes) > 1:
            analysis['diversity_areas'].append({
                'topic': 'company_size',
                'label': '企業規模',
                'distribution': company_sizes
            })
        
        analysis['company_culture'] = {'sizes': company_sizes}
        
        # キャリアパス
        training_yes = sum(1 for attr in job_attributes if attr.get('career_path', {}).get('training') == True)
        training_no = sum(1 for attr in job_attributes if attr.get('career_path', {}).get('training') == False)
        
        growth_yes = sum(1 for attr in job_attributes if attr.get('career_path', {}).get('growth_opportunities') == True)
        growth_no = sum(1 for attr in job_attributes if attr.get('career_path', {}).get('growth_opportunities') == False)
        
        analysis['career_path'] = {
            'training': {'yes': training_yes, 'no': training_no},
            'growth': {'yes': growth_yes, 'no': growth_no}
        }
        
        if training_yes > 0 and training_no > 0:
            analysis['diversity_areas'].append({
                'topic': 'training',
                'label': '研修制度',
                'yes_count': training_yes,
                'no_count': training_no
            })
        
        if growth_yes > 0 and growth_no > 0:
            analysis['diversity_areas'].append({
                'topic': 'growth',
                'label': 'キャリア成長機会',
                'yes_count': growth_yes,
                'no_count': growth_no
            })
        
        analysis['has_diversity'] = len(analysis['diversity_areas']) > 0
        
        return analysis
    
    def _get_similar_users_success_patterns(self, user_id: int, cur) -> str:
        """類似ユーザーの成功パターンを取得"""
        try:
            # 類似ユーザーの会話履歴から成功パターンを抽出
            cur.execute("""
                SELECT 
                    ch.user_id,
                    COUNT(DISTINCT ch.id) as message_count,
                    COUNT(DISTINCT ui.id) as apply_count,
                    STRING_AGG(DISTINCT uqr.question_key, ', ') as questions_asked
                FROM chat_history ch
                LEFT JOIN user_interactions ui ON ch.user_id = ui.user_id AND ui.interaction_type = 'apply'
                LEFT JOIN user_question_responses uqr ON ch.user_id = uqr.user_id
                WHERE ch.user_id != %s
                  AND ui.id IS NOT NULL
                GROUP BY ch.user_id
                HAVING COUNT(DISTINCT ui.id) > 0
                ORDER BY apply_count DESC
                LIMIT 10
            """, (user_id,))
            
            similar_users = cur.fetchall()
            
            if not similar_users:
                return "類似ユーザーのデータがありません"
            
            patterns = []
            for user in similar_users:
                if user['questions_asked']:
                    patterns.append(
                        f"- ユーザー{user['user_id']}: {user['apply_count']}件応募, "
                        f"質問テーマ: {user['questions_asked']}"
                    )
            
            return "\n".join(patterns) if patterns else "参考情報なし"
            
        except Exception as e:
            print(f"Error getting similar users patterns: {e}")
            return "参考情報なし"
    
    def _generate_question_with_ai(
        self,
        user_profile: Dict,
        answered_summary: str,
        diversity_analysis: Dict,
        similar_users_patterns: str,
        recommendations_count: int,
        user_last_message: str
    ) -> Optional[Dict[str, Any]]:
        """AIを使って質問を生成"""
        
        # 多様性のある項目をテキスト化
        diversity_text = ""
        if diversity_analysis.get('has_diversity'):
            diversity_text = "【求人の多様性】\n"
            for area in diversity_analysis['diversity_areas'][:5]:
                if 'yes_count' in area:
                    diversity_text += f"- {area['label']}: あり {area['yes_count']}件 / なし {area['no_count']}件\n"
                elif 'distribution' in area:
                    diversity_text += f"- {area['label']}: {area['distribution']}\n"
        else:
            diversity_text = "【求人の多様性】求人の属性に大きな差はありません"
        
        prompt = f"""
あなたは求人マッチングの専門AIアシスタントです。
ユーザーと自然な会話をしながら、最適な求人を絞り込むために次の質問を生成してください。

【ユーザー情報】
- 希望職種: {user_profile.get('job_title', '未設定')}
- 希望勤務地: {user_profile.get('location_prefecture', '未設定')}
- 希望年収: {user_profile.get('salary_min', 0)}万円以上

【現在の状況】
- 該当求人数: {recommendations_count}件
- ユーザーの最後のメッセージ: "{user_last_message}"

【既に聞いた内容】
{answered_summary}

{diversity_text}

【類似ユーザーの成功パターン】
過去に似た条件で求人を探したユーザーが、どんな質問に答えて成功したか：
{similar_users_patterns}

【あなたのタスク】
上記の情報を総合的に判断して、次に聞くべき質問を**1つだけ**生成してください。

【重要な制約】
1. **初回の場合は必ず質問を生成してください**（question_text を null にしない）
2. **既に聞いた質問は絶対に聞かない**
3. **求人に多様性がある項目を優先的に質問する**（絞り込みに効果的）
4. **自然な会話形式で質問する**（「〜についてはどうですか？」「〜は重要ですか？」など）
5. **一度に1つの観点だけを質問する**
6. **質問文は簡潔に、最大50文字程度**
7. **もし既に5つ以上の質問に答えていて、十分に絞り込めた場合のみ question_text を null にする**

【質問のテーマ例】
以下のようなテーマから、状況に応じて自由に質問を作成してください：
- リモートワーク、在宅勤務の可否
- フレックスタイム制度の有無
- 副業・兼業の可否
- 残業時間の多さ
- 企業規模（大企業、ベンチャーなど）
- 職場の雰囲気（活気的、安定的など）
- キャリア成長の機会
- 研修・育成制度
- 昇進スピード
- その他、求人の属性から判断した質問

【初回の質問について】
もしこれが初回の質問（既に聞いた内容が「初回質問」と表示されている場合）の場合は、
最も重要で効果的な質問を1つ選んでください。多くの場合、以下のような質問が効果的です：
- リモートワークの可否（働き方の柔軟性）
- 企業規模の希望（ベンチャーか大企業か）
- キャリア成長の重視度

【出力形式】
以下のJSON形式で返してください：

{{
  "question_key": "質問キー（重要: 必ず以下のリストから選択）",
  "question_text": "自然な質問文",
  "category": "質問のカテゴリ（働き方の柔軟性 / 企業文化・雰囲気 / キャリアパス）",
  "reasoning": "なぜこの質問をするのか、簡単な理由"
}}

【question_key の指定ルール】
**必ず以下のいずれかを使用してください（他のキーは使用禁止）:**

働き方の柔軟性:
- remote (リモートワーク)
- flex_time (フレックスタイム)
- side_job (副業)
- overtime (残業時間)

企業文化・雰囲気:
- company_size (企業規模)
- company_type (企業タイプ: ベンチャー/大企業/安定志向など)
- atmosphere (職場の雰囲気)

キャリアパス:
- training (研修制度)
- growth (成長機会)
- promotion (昇進スピード)

**例:**
- リモートワークについて質問 → "question_key": "remote"
- 企業規模について質問 → "question_key": "company_size"
- 成長機会について質問 → "question_key": "growth"

**重要:** question_key は上記リストから必ず選択し、_preference などのサフィックスを付けないでください。

**注意**: JSON以外の説明文は不要です。JSONのみを返してください。
**重要**: 初回の場合は必ず question_text に質問文を入れてください。null は禁止です。
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # JSONを抽出
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)
            
            result = json.loads(result_text)
            
            # question_textがnullなら質問終了
            if not result.get('question_text'):
                print("AI determined no more questions needed")
                return None
            
            print(f"\n=== AI Generated Question ===")
            print(f"Key: {result.get('question_key')}")
            print(f"Text: {result.get('question_text')}")
            print(f"Category: {result.get('category')}")
            print(f"Reasoning: {result.get('reasoning')}")
            print("=" * 40)
            
            return {
                'question_key': result.get('question_key'),
                'question_text': result.get('question_text'),
                'category': result.get('category', '働き方の柔軟性'),
                'question_type': 'free_text',  # 自由回答形式
                'reasoning': result.get('reasoning', '')
            }
            
        except Exception as e:
            print(f"Error generating question with AI: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_question_and_response(
        self, 
        user_id: int, 
        question_key: str,
        question_text: str,
        category: str,
        response_text: str,
        normalized_response: str
    ) -> bool:
        """
        動的に生成された質問と回答を保存
        
        Args:
            user_id: ユーザーID
            question_key: 質問キー
            question_text: 質問文
            category: カテゴリ
            response_text: ユーザーの回答
            normalized_response: 正規化された回答
            
        Returns:
            成功したかどうか
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            
            # 1. 質問をdynamic_questionsテーブルに保存（既存チェック）
            cur.execute("""
                INSERT INTO dynamic_questions (question_key, question_text, category, question_type)
                VALUES (%s, %s, %s, 'free_text')
                ON CONFLICT (question_key) DO UPDATE
                SET usage_count = dynamic_questions.usage_count + 1
                RETURNING id
            """, (question_key, question_text, category))
            
            question_id = cur.fetchone()[0]
            
            # 2. ユーザーの回答を保存
            cur.execute("""
                INSERT INTO user_question_responses 
                (user_id, question_id, response_text, normalized_response, created_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (user_id, question_id, response_text, normalized_response))
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"✓ Saved question and response for user {user_id}")
            return True
            
        except Exception as e:
            print(f"Error saving question and response: {e}")
            import traceback
            traceback.print_exc()
            return False