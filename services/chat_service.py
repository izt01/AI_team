"""
チャット統合サービス - すべての機能を統合
"""

from typing import Optional, List
from models.chat_models import (
    ChatSession, QuestionContext, ScoringInput, 
    ChatTurnResult, JobRecommendation
)
from utils.session_manager import SessionManager
from services.question_generator import QuestionGenerator
from services.scoring_service import ScoringService
from services.job_recommender import JobRecommender


class ChatService:
    """チャット統合サービス"""
    
    def __init__(self):
        self.question_gen = QuestionGenerator()
        self.scoring_service = ScoringService()
    
    def start_chat(self, user_id: str) -> ChatTurnResult:
        """
        チャット開始（初回メッセージ）
        
        Args:
            user_id: ユーザーID
            
        Returns:
            ChatTurnResult: 初回メッセージ
        """
        
        # ユーザーのStep2情報を取得
        user_preferences = SessionManager.get_user_preferences(user_id)
        
        # セッション作成
        session = SessionManager.create_session(user_id, user_preferences)
        
        # 初回メッセージ
        initial_message = self._generate_initial_message(user_preferences)
        
        # セッションに記録
        SessionManager.add_turn(
            session=session,
            user_message="[初回接続]",
            ai_message=initial_message,
            is_deep_dive=False,
            new_score=0.0
        )
        
        return ChatTurnResult(
            ai_message=initial_message,
            current_score=0.0,
            turn_count=1,
            should_show_jobs=False,
            jobs=None,
            session_id=session.session_id
        )
    
    def process_message(
        self,
        user_id: str,
        user_message: str,
        session_id: Optional[str] = None
    ) -> ChatTurnResult:
        """
        ユーザーメッセージを処理
        
        Args:
            user_id: ユーザーID
            user_message: ユーザーのメッセージ
            session_id: セッションID（既存セッション）
            
        Returns:
            ChatTurnResult: 会話結果
        """
        
        # セッション取得または作成
        if session_id:
            session = SessionManager.get_session(session_id)
            if not session:
                # セッションがない場合は新規作成
                return self.start_chat(user_id)
        else:
            return self.start_chat(user_id)
        
        print(f"\n{'='*60}")
        print(f"💬 ターン {session.turn_count + 1} 開始")
        print(f"   ユーザー: {user_message[:50]}...")
        print(f"   現在スコア: {session.current_score}%")
        
        # Step 1: スコアリング
        scoring_result = self._score_conversation(session, user_message)
        print(f"📊 新しいスコア: {scoring_result.score}%")
        print(f"   マッチキーワード: {', '.join(scoring_result.matched_keywords[:5])}")
        
        # スコア履歴を更新
        session.score_history.append(scoring_result.score)
        
        # Step 2: 求人表示判定
        should_show, trigger_reason = JobRecommender.should_show_jobs(
            turn_count=session.turn_count + 1,
            current_score=scoring_result.score,
            user_message=user_message,
            score_history=session.score_history  # スコア履歴を渡す
        )
        
        print(f"🎯 求人表示判定: {should_show} (理由: {trigger_reason})")
        
        # Step 3: 求人表示 or 次の質問
        if should_show:
            # 求人を取得
            jobs = JobRecommender.get_recommendations(
                user_preferences=session.user_preferences,
                conversation_keywords=scoring_result.matched_keywords,
                limit=5
            )
            
            print(f"✅ 求人推薦: {len(jobs)}件")
            
            # 求人が0件の場合の処理
            if not jobs:
                ai_message = f"""素晴らしい！マッチ度が{scoring_result.score:.0f}%に達しました！

あなたのご希望は十分に理解できました：
- {session.user_preferences.get('job_title', 'デザイナー')}として活躍したい
- Photoshopなどのデザインツールに精通
- 大規模プロジェクトでリーダーシップを発揮したい
- Web広告やファッション系デザインにも興味

申し訳ございませんが、現在システムに登録されている求人情報がございません。
実際のサービスでは、これらの条件にマッチする求人をご紹介できます。

何か他にお聞きしたいことはございますか？"""
                
                SessionManager.add_turn(
                    session=session,
                    user_message=user_message,
                    ai_message=ai_message,
                    is_deep_dive=False,
                    new_score=scoring_result.score
                )
                
                return ChatTurnResult(
                    ai_message=ai_message,
                    current_score=scoring_result.score,
                    turn_count=session.turn_count,
                    should_show_jobs=False,  # 求人なしなので表示しない
                    jobs=None,
                    session_id=session.session_id
                )
            
            # 求人紹介メッセージ
            ai_message = self._generate_job_intro_message(
                jobs=jobs,
                trigger_reason=trigger_reason,
                score=scoring_result.score
            )
            
            # セッションに記録
            SessionManager.add_turn(
                session=session,
                user_message=user_message,
                ai_message=ai_message,
                is_deep_dive=False,
                new_score=scoring_result.score
            )
            
            return ChatTurnResult(
                ai_message=ai_message,
                current_score=scoring_result.score,
                turn_count=session.turn_count,
                should_show_jobs=True,
                jobs=jobs,
                session_id=session.session_id
            )
        
        else:
            # 最新のユーザーメッセージを含む会話履歴を作成
            temp_history = session.conversation_history.copy()
            temp_history.append({
                "role": "user",
                "content": user_message,
                "turn": str(session.turn_count + 1)
            })
            
            # 次の質問を生成
            question_context = QuestionContext(
                user_preferences=session.user_preferences,
                conversation_history=temp_history,  # 最新メッセージを含む
                current_score=scoring_result.score,
                turn_count=session.turn_count + 1,
                is_deep_dive_previous=session.is_deep_dive_previous
            )
            
            generated_q = self.question_gen.generate_question(question_context)
            
            print(f"❓ 次の質問: {generated_q.question[:50]}...")
            print(f"   深掘り: {generated_q.is_deep_dive}")
            print(f"   タイプ: {generated_q.question_type}")
            
            # セッションに記録
            SessionManager.add_turn(
                session=session,
                user_message=user_message,
                ai_message=generated_q.question,
                is_deep_dive=generated_q.is_deep_dive,
                new_score=scoring_result.score
            )
            
            print(f"={'='*60}\n")
            
            return ChatTurnResult(
                ai_message=generated_q.question,
                current_score=scoring_result.score,
                turn_count=session.turn_count,
                should_show_jobs=False,
                jobs=None,
                session_id=session.session_id
            )
    
    def _generate_initial_message(self, user_preferences: dict) -> str:
        """初回メッセージを生成"""
        
        job_title = user_preferences.get('job_title', '未設定')
        location = user_preferences.get('location', '未設定')
        salary_min = user_preferences.get('salary_min', 0)
        
        # 登録情報の表示
        pref_info = f"""登録情報を確認しました：
- 希望職種: {job_title}
- 希望勤務地: {location}
- 希望年収: {salary_min}万円〜"""
        
        # 職種に応じた質問を生成
        if job_title and job_title != '未設定':
            question = f"まず、{job_title}としてどのようなスキルや経験をお持ちですか？\n具体的なツールや技術があれば教えてください。"
        else:
            question = "まず、どのようなスキルや経験をお持ちですか？\n具体的なツールや技術があれば教えてください。"
        
        message = f"""こんにちは！あなたにぴったりの求人を見つけるお手伝いをします。

{pref_info}

それでは、より詳しくあなたの希望を教えてください。

{question}"""
        
        return message
    
    def _score_conversation(self, session: ChatSession, user_message: str) -> any:
        """会話をスコアリング"""
        
        scoring_input = ScoringInput(
            user_preferences=session.user_preferences,
            conversation_history=session.conversation_history,
            latest_user_response=user_message
        )
        
        return self.scoring_service.calculate_score(scoring_input)
    
    def _generate_job_intro_message(
        self,
        jobs: List[JobRecommendation],
        trigger_reason: str,
        score: float
    ) -> str:
        """求人紹介メッセージを生成"""
        
        if trigger_reason == "match_score_high":
            intro = f"素晴らしい！マッチ度が{score:.0f}%に達しました！\n\nあなたにぴったりの求人を見つけました：\n\n"
        elif trigger_reason == "user_request":
            intro = "承知しました！現在の情報から、おすすめの求人をご紹介します：\n\n"
        elif trigger_reason == "score_stagnant":
            intro = "十分な情報が集まったようですね！\n\nこれまでのお話から、おすすめの求人をご紹介します：\n\n"
        else:  # turn_limit
            intro = "たくさんお話しいただきありがとうございます！\n\nこれまでの内容から、おすすめの求人をご紹介します：\n\n"
        
        # 求人リスト
        job_list = ""
        for i, job in enumerate(jobs, 1):
            job_list += f"{i}. **{job.job_title}** - {job.company_name}\n"
            job_list += f"   💰 {job.salary_min}万〜{job.salary_max}万円\n"
            job_list += f"   📍 {job.location} | {job.remote_option}\n"
            job_list += f"   ⭐ マッチ度: {job.match_score:.0f}% ({job.match_reasoning})\n"
            job_list += f"   【ID:{job.job_id}】\n\n"
        
        outro = "\n気になる求人があれば、番号またはIDで教えてください！\n詳しい情報をお伝えします。"
        
        return intro + job_list + outro