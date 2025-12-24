-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 進化型AI求人マッチングシステム v3.0 - テーブル作成スクリプト
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- 実行方法:
-- psql -U devuser -d jobmatch -f create_tables_evolved.sql

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 1. conversation_turns（会話ターンデータ）
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TABLE IF NOT EXISTS conversation_turns (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES personal_date(user_id),
    session_id VARCHAR(100) NOT NULL,
    turn_number INTEGER NOT NULL,
    user_message TEXT,
    bot_message TEXT,
    extracted_info JSONB,
    top_score FLOAT,
    top_match_percentage FLOAT,
    candidate_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_conversation_turns_user 
ON conversation_turns(user_id);

CREATE INDEX IF NOT EXISTS idx_conversation_turns_session 
ON conversation_turns(session_id);

CREATE INDEX IF NOT EXISTS idx_conversation_turns_user_session 
ON conversation_turns(user_id, session_id);

COMMENT ON TABLE conversation_turns IS '会話の各ターンのデータを記録';
COMMENT ON COLUMN conversation_turns.extracted_info IS 'AIが抽出したユーザーの意図・希望（JSON）';
COMMENT ON COLUMN conversation_turns.top_score IS 'そのターンでのトップ求人のスコア';
COMMENT ON COLUMN conversation_turns.top_match_percentage IS 'そのターンでのトップ求人のマッチ度（%）';

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 2. user_insights（ユーザー情報の蓄積）
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TABLE IF NOT EXISTS user_insights (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES personal_date(user_id),
    session_id VARCHAR(100) NOT NULL,
    insights JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, session_id)
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_user_insights_user 
ON user_insights(user_id);

CREATE INDEX IF NOT EXISTS idx_user_insights_session 
ON user_insights(session_id);

COMMENT ON TABLE user_insights IS '会話を通じて蓄積されたユーザーの希望・価値観';
COMMENT ON COLUMN user_insights.insights IS '蓄積された情報（explicit_preferences, implicit_values, pain_points, keywords）';

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 3. conversation_sessions（セッションサマリー）
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TABLE IF NOT EXISTS conversation_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES personal_date(user_id),
    session_id VARCHAR(100) NOT NULL UNIQUE,
    total_turns INTEGER,
    end_reason VARCHAR(50),
    final_match_percentage FLOAT,
    presented_jobs JSONB,
    ended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user 
ON conversation_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_conversation_sessions_session 
ON conversation_sessions(session_id);

COMMENT ON TABLE conversation_sessions IS '会話セッションの最終結果';
COMMENT ON COLUMN conversation_sessions.end_reason IS '終了理由（high_match, score_converged, user_requested, max_turns）';
COMMENT ON COLUMN conversation_sessions.presented_jobs IS '提示した求人IDのリスト（JSON配列）';

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 4. score_history（スコア履歴）
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TABLE IF NOT EXISTS score_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES personal_date(user_id),
    session_id VARCHAR(100) NOT NULL,
    turn_number INTEGER NOT NULL,
    job_id VARCHAR(100) NOT NULL,
    score FLOAT,
    match_percentage FLOAT,
    score_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_score_history_user 
ON score_history(user_id);

CREATE INDEX IF NOT EXISTS idx_score_history_session 
ON score_history(session_id);

CREATE INDEX IF NOT EXISTS idx_score_history_session_turn 
ON score_history(session_id, turn_number);

CREATE INDEX IF NOT EXISTS idx_score_history_job 
ON score_history(job_id);

COMMENT ON TABLE score_history IS '各ターンでの求人のスコア推移';
COMMENT ON COLUMN score_history.score_details IS '加点理由のリスト（JSON配列）';

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 5. chat_history（チャット履歴）- 既存テーブルの確認
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- chat_history テーブルが存在しない場合は作成
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES personal_date(user_id),
    session_id VARCHAR(100),
    sender VARCHAR(10) NOT NULL CHECK (sender IN ('user', 'bot')),
    message TEXT NOT NULL,
    extracted_intent JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_chat_history_user 
ON chat_history(user_id);

CREATE INDEX IF NOT EXISTS idx_chat_history_session 
ON chat_history(session_id);

CREATE INDEX IF NOT EXISTS idx_chat_history_user_session 
ON chat_history(user_id, session_id);

COMMENT ON TABLE chat_history IS 'ユーザーとボットの会話履歴';

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 6. user_interactions（ユーザー行動）- 既存テーブルの確認
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- user_interactions テーブルが存在しない場合は作成
CREATE TABLE IF NOT EXISTS user_interactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES personal_date(user_id),
    job_id UUID NOT NULL,
    interaction_type VARCHAR(50) NOT NULL,
    interaction_value FLOAT DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_user_interactions_user 
ON user_interactions(user_id);

CREATE INDEX IF NOT EXISTS idx_user_interactions_job 
ON user_interactions(job_id);

CREATE INDEX IF NOT EXISTS idx_user_interactions_type 
ON user_interactions(interaction_type);

COMMENT ON TABLE user_interactions IS 'ユーザーの行動履歴（クリック、お気に入り、応募など）';

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 完了メッセージ
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DO $$
BEGIN
    RAISE NOTICE '✅ 進化型AI求人マッチングシステム v3.0';
    RAISE NOTICE '✅ テーブル作成完了';
    RAISE NOTICE '';
    RAISE NOTICE '作成されたテーブル:';
    RAISE NOTICE '  1. conversation_turns - 会話ターンデータ';
    RAISE NOTICE '  2. user_insights - ユーザー情報蓄積';
    RAISE NOTICE '  3. conversation_sessions - セッションサマリー';
    RAISE NOTICE '  4. score_history - スコア履歴';
    RAISE NOTICE '  5. chat_history - チャット履歴（既存も確認）';
    RAISE NOTICE '  6. user_interactions - ユーザー行動（既存も確認）';
    RAISE NOTICE '';
    RAISE NOTICE '次のステップ:';
    RAISE NOTICE '  python main_evolved_complete.py';
END $$;
