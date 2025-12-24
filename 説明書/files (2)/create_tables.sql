-- ============================================================================
-- JobMatch AI - データベーステーブル作成スクリプト
-- ============================================================================
-- 
-- このスクリプトは、JobMatch AIシステムで使用する全テーブルを作成します。
-- PostgreSQL 12以降を想定しています。
--
-- 実行方法:
-- psql -U devuser -d jobmatch -f create_tables.sql
--
-- ============================================================================

-- ============================================================================
-- 1. ユーザー関連テーブル
-- ============================================================================

-- ユーザー個人情報テーブル
CREATE TABLE IF NOT EXISTS personal_date (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    user_name VARCHAR(100) NOT NULL,
    birth_day DATE,
    phone_number VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ユーザープロフィールテーブル（希望条件）
CREATE TABLE IF NOT EXISTS user_profile (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    job_title VARCHAR(100),
    location_prefecture VARCHAR(50),
    salary_min INTEGER DEFAULT 0,
    employment_type VARCHAR(50),
    work_hours VARCHAR(100),
    holiday_policy VARCHAR(100),
    workplace_atmosphere VARCHAR(100),
    remote VARCHAR(50),
    employee_benefits TEXT,
    job_summary TEXT,
    skills TEXT,
    certifications TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES personal_date(user_id) ON DELETE CASCADE
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_personal_date_email ON personal_date(email);
CREATE INDEX IF NOT EXISTS idx_user_profile_user_id ON user_profile(user_id);

-- ============================================================================
-- 2. 企業・求人関連テーブル
-- ============================================================================

-- 企業基本情報テーブル
CREATE TABLE IF NOT EXISTS company_date (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL UNIQUE,
    company_name VARCHAR(200) NOT NULL,
    industry VARCHAR(100),
    employee_count INTEGER,
    founded_year INTEGER,
    headquarters VARCHAR(200),
    website VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 求人情報テーブル
CREATE TABLE IF NOT EXISTS company_profile (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    job_title VARCHAR(100) NOT NULL,
    location_prefecture VARCHAR(50) NOT NULL,
    location_city VARCHAR(100),
    salary_min INTEGER NOT NULL,
    salary_max INTEGER NOT NULL,
    employment_type VARCHAR(50),
    job_summary TEXT,
    required_skills TEXT,
    preferred_skills TEXT,
    remote_option VARCHAR(50),
    remote_work VARCHAR(50),
    company_culture TEXT,
    work_flexibility VARCHAR(100),
    benefits TEXT,
    work_hours VARCHAR(100),
    holidays VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES company_date(company_id) ON DELETE CASCADE
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_company_profile_company_id ON company_profile(company_id);
CREATE INDEX IF NOT EXISTS idx_company_profile_job_title ON company_profile(job_title);
CREATE INDEX IF NOT EXISTS idx_company_profile_location ON company_profile(location_prefecture);
CREATE INDEX IF NOT EXISTS idx_company_profile_salary ON company_profile(salary_min, salary_max);

-- ============================================================================
-- 3. セッション管理テーブル
-- ============================================================================

-- セッション管理テーブル（クッキー制限回避）
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER,
    session_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);

-- ============================================================================
-- 4. 会話追跡テーブル
-- ============================================================================

-- 会話ターン記録テーブル
CREATE TABLE IF NOT EXISTS conversation_turns (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
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

-- ユーザー洞察蓄積テーブル
CREATE TABLE IF NOT EXISTS user_insights (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    insights JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, session_id)
);

-- 会話セッションサマリーテーブル
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(100) NOT NULL UNIQUE,
    total_turns INTEGER,
    end_reason VARCHAR(50),
    final_match_percentage FLOAT,
    presented_jobs JSONB,
    ended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_conversation_turns_session 
    ON conversation_turns(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_turn 
    ON conversation_turns(session_id, turn_number);

-- ============================================================================
-- 5. スコア履歴テーブル
-- ============================================================================

-- スコア履歴テーブル
CREATE TABLE IF NOT EXISTS score_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    turn_number INTEGER NOT NULL,
    job_id VARCHAR(100) NOT NULL,
    score FLOAT,
    match_percentage FLOAT,
    score_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_score_history_session 
    ON score_history(user_id, session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_score_history_job 
    ON score_history(job_id);

-- ============================================================================
-- 6. ユーザー行動追跡テーブル
-- ============================================================================

-- ユーザー行動追跡テーブル（クリック、お気に入り、応募）
CREATE TABLE IF NOT EXISTS user_interactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    job_id UUID NOT NULL,
    interaction_type VARCHAR(20) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_user_interactions_user_job 
    ON user_interactions(user_id, job_id, interaction_type);

-- ============================================================================
-- 7. チャット履歴テーブル
-- ============================================================================

-- チャット履歴テーブル
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    sender VARCHAR(10) NOT NULL,
    message TEXT,
    extracted_intent JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_chat_history_session 
    ON chat_history(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_created 
    ON chat_history(created_at DESC);

-- ============================================================================
-- コメント追加
-- ============================================================================

COMMENT ON TABLE personal_date IS 'ユーザーの個人情報（氏名、メール、パスワード等）';
COMMENT ON TABLE user_profile IS 'ユーザーの希望条件プロフィール（職種、勤務地、年収等）';
COMMENT ON TABLE company_date IS '企業の基本情報';
COMMENT ON TABLE company_profile IS '企業の求人情報';
COMMENT ON TABLE user_sessions IS 'セッション管理（クッキー制限回避のため大きなデータを保存）';
COMMENT ON TABLE conversation_turns IS '会話の各ターンを記録';
COMMENT ON TABLE user_insights IS '会話を通じて得られたユーザーの洞察を蓄積';
COMMENT ON TABLE conversation_sessions IS '会話セッションの終了情報サマリー';
COMMENT ON TABLE score_history IS '各ターンでの求人スコアの変化を記録';
COMMENT ON TABLE user_interactions IS 'ユーザーの行動（クリック、お気に入り、応募）を追跡';
COMMENT ON TABLE chat_history IS 'チャット履歴の完全な記録';

-- ============================================================================
-- テーブル作成完了
-- ============================================================================

-- 確認用クエリ（オプション）
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE';
    
    RAISE NOTICE '✅ テーブル作成完了: % テーブルが作成されました', table_count;
END $$;
