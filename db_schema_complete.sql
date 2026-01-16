-- ============================================
-- AI求人マッチングシステム - 完全DBスキーマ
-- ============================================

-- データベース作成（必要に応じて）
-- CREATE DATABASE jobmatch;

-- ============================================
-- 1. ユーザー関連テーブル
-- ============================================

-- 個人基本情報
CREATE TABLE IF NOT EXISTS personal_date (
    user_id SERIAL PRIMARY KEY,  -- SERIAL = INTEGER with auto-increment
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    age INTEGER,
    gender VARCHAR(20),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ユーザープロフィール（職歴・スキル）
CREATE TABLE IF NOT EXISTS user_profile (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES personal_date(user_id) ON DELETE CASCADE,
    job_title VARCHAR(200),
    years_of_experience INTEGER,
    skills TEXT[],
    education_level VARCHAR(50),
    location_prefecture VARCHAR(50),
    location_city VARCHAR(100),
    salary_min INTEGER,
    salary_max INTEGER,
    work_style_preference TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- ユーザー希望条件プロフィール
CREATE TABLE IF NOT EXISTS user_preferences_profile (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES personal_date(user_id) ON DELETE CASCADE,
    job_title VARCHAR(200),
    location_prefecture VARCHAR(50),
    location_city VARCHAR(100),
    salary_min INTEGER,
    salary_max INTEGER,
    remote_work_preference VARCHAR(50),
    employment_type VARCHAR(50),
    industry_preferences TEXT[],
    work_hours_preference VARCHAR(100),
    company_size_preference VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- ユーザー性格分析
CREATE TABLE IF NOT EXISTS user_personality_analysis (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES personal_date(user_id) ON DELETE CASCADE,
    personality_traits JSONB,
    work_values JSONB,
    communication_style VARCHAR(50),
    decision_making_style VARCHAR(50),
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- ユーザーセッション
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER REFERENCES personal_date(user_id) ON DELETE CASCADE,
    session_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- ============================================
-- 2. 企業・求人関連テーブル
-- ============================================

-- 企業基本情報
CREATE TABLE IF NOT EXISTS company_date (
    company_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    company_size VARCHAR(50),
    founded_year INTEGER,
    website_url VARCHAR(500),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 求人情報（メインテーブル）
CREATE TABLE IF NOT EXISTS company_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES company_date(company_id) ON DELETE CASCADE,
    
    -- Layer 1: 基本情報（必須）
    job_title VARCHAR(200) NOT NULL,
    job_description TEXT NOT NULL,
    location_prefecture VARCHAR(50) NOT NULL,
    location_city VARCHAR(100),
    salary_min INTEGER NOT NULL,
    salary_max INTEGER NOT NULL,
    employment_type VARCHAR(50) DEFAULT '正社員',
    
    -- Layer 2: 構造化データ（オプション）
    remote_option VARCHAR(50),
    flex_time BOOLEAN DEFAULT FALSE,
    latest_start_time TIME,
    side_job_allowed BOOLEAN DEFAULT FALSE,
    team_size VARCHAR(50),
    development_method VARCHAR(100),
    tech_stack JSONB,
    required_skills TEXT[],
    preferred_skills TEXT[],
    benefits TEXT[],
    
    -- Layer 3: 自由記述（AI抽出対象）
    work_style_details TEXT,
    team_culture_details TEXT,
    growth_opportunities_details TEXT,
    benefits_details TEXT,
    office_environment_details TEXT,
    project_details TEXT,
    company_appeal_text TEXT,
    
    -- AI処理済みデータ
    ai_extracted_features JSONB,
    additional_questions JSONB,
    embedding VECTOR(1536),
    
    -- メタデータ
    status VARCHAR(20) DEFAULT 'active',
    view_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    favorite_count INTEGER DEFAULT 0,
    apply_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 求人属性（追加の構造化データ）
CREATE TABLE IF NOT EXISTS job_attributes (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES company_profile(id) ON DELETE CASCADE,
    attribute_name VARCHAR(100) NOT NULL,
    attribute_value TEXT,
    attribute_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 動的質問の回答（別テーブル方式）
CREATE TABLE IF NOT EXISTS job_additional_answers (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES company_profile(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    answer_text TEXT,
    question_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 3. 会話・マッチング関連テーブル
-- ============================================

-- 会話ログ（メインログ）
CREATE TABLE IF NOT EXISTS conversation_logs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id INTEGER REFERENCES personal_date(user_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    user_message TEXT,
    ai_response TEXT,
    extracted_intent JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会話セッション
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES personal_date(user_id) ON DELETE CASCADE,
    session_id VARCHAR(100) NOT NULL UNIQUE,
    total_turns INTEGER,
    end_reason VARCHAR(50),
    final_match_percentage FLOAT,
    presented_jobs JSONB,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会話ターン詳細
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

-- ユーザー洞察蓄積
CREATE TABLE IF NOT EXISTS user_insights (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    insights JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, session_id)
);

-- スコア履歴
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

-- チャット履歴
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    sender VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 4. ユーザー行動追跡テーブル
-- ============================================

-- ユーザーインタラクション
CREATE TABLE IF NOT EXISTS user_interactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES personal_date(user_id) ON DELETE CASCADE,
    job_id UUID REFERENCES company_profile(id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL,
    session_id VARCHAR(100),
    interaction_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ユーザーインタラクションサマリー（ビュー）
CREATE OR REPLACE VIEW user_interaction_summary AS
SELECT 
    user_id,
    job_id,
    COUNT(*) FILTER (WHERE interaction_type = 'view') as view_count,
    COUNT(*) FILTER (WHERE interaction_type = 'click') as click_count,
    COUNT(*) FILTER (WHERE interaction_type = 'favorite') as favorite_count,
    COUNT(*) FILTER (WHERE interaction_type = 'apply') as apply_count,
    MAX(created_at) as last_interaction
FROM user_interactions
GROUP BY user_id, job_id;

-- 検索履歴
CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES personal_date(user_id) ON DELETE CASCADE,
    search_query TEXT,
    filters JSONB,
    results_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 5. エンリッチメント・トレンド関連テーブル
-- ============================================

-- 不足情報ログ
CREATE TABLE IF NOT EXISTS missing_job_info_log (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES company_profile(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES personal_date(user_id) ON DELETE SET NULL,
    missing_field VARCHAR(100) NOT NULL,
    detected_from VARCHAR(50),
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 企業への追加質問リクエスト
CREATE TABLE IF NOT EXISTS company_enrichment_requests (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES company_profile(id) ON DELETE CASCADE,
    company_id UUID REFERENCES company_date(company_id) ON DELETE CASCADE,
    missing_field VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50),
    priority_score INTEGER,
    detection_count INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    response_text TEXT
);

-- グローバル嗜好トレンド
CREATE TABLE IF NOT EXISTS global_preference_trends (
    id SERIAL PRIMARY KEY,
    preference_key VARCHAR(100) NOT NULL,
    preference_value TEXT,
    occurrence_count INTEGER DEFAULT 1,
    unique_users INTEGER DEFAULT 1,
    last_detected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trend_score FLOAT,
    category VARCHAR(50),
    UNIQUE(preference_key, preference_value)
);

-- トレンド閾値（動的質問生成用）
CREATE TABLE IF NOT EXISTS trend_thresholds (
    id SERIAL PRIMARY KEY,
    threshold_name VARCHAR(100) UNIQUE NOT NULL,
    threshold_value INTEGER NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 週次トレンド（キャッシュ）
CREATE TABLE IF NOT EXISTS current_weekly_trends (
    id SERIAL PRIMARY KEY,
    week_start DATE NOT NULL,
    trend_data JSONB NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(week_start)
);

-- ============================================
-- 6. 基本項目管理テーブル
-- ============================================

-- 基本項目定義
CREATE TABLE IF NOT EXISTS baseline_job_fields (
    field_id SERIAL PRIMARY KEY,
    field_name VARCHAR(100) UNIQUE NOT NULL,
    field_type VARCHAR(50) NOT NULL,
    label VARCHAR(200) NOT NULL,
    question_template TEXT,
    options JSONB,
    placeholder TEXT,
    required BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 0,
    category VARCHAR(50),
    promoted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 7. スカウト関連テーブル
-- ============================================

-- スカウトメッセージ
CREATE TABLE IF NOT EXISTS scout_messages (
    id SERIAL PRIMARY KEY,
    company_id UUID REFERENCES company_date(company_id) ON DELETE CASCADE,
    job_id UUID REFERENCES company_profile(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES personal_date(user_id) ON DELETE CASCADE,
    message_title VARCHAR(255) NOT NULL,
    message_body TEXT NOT NULL,
    match_score FLOAT,
    match_reasons JSONB,
    status VARCHAR(50) DEFAULT 'sent',
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    replied_at TIMESTAMP
);

-- ============================================
-- 8. 動的質問関連テーブル
-- ============================================

-- 動的質問定義
CREATE TABLE IF NOT EXISTS dynamic_questions (
    id SERIAL PRIMARY KEY,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50),
    target_context VARCHAR(100),
    options JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ユーザー回答
CREATE TABLE IF NOT EXISTS user_question_responses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES personal_date(user_id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES dynamic_questions(id) ON DELETE CASCADE,
    response_text TEXT,
    response_data JSONB,
    session_id VARCHAR(100),
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- インデックス作成
-- ============================================

-- パフォーマンス向上用インデックス
CREATE INDEX IF NOT EXISTS idx_company_profile_job_title ON company_profile(job_title);
CREATE INDEX IF NOT EXISTS idx_company_profile_location ON company_profile(location_prefecture, location_city);
CREATE INDEX IF NOT EXISTS idx_company_profile_salary ON company_profile(salary_min, salary_max);
CREATE INDEX IF NOT EXISTS idx_company_profile_status ON company_profile(status);
CREATE INDEX IF NOT EXISTS idx_company_profile_company_id ON company_profile(company_id);

CREATE INDEX IF NOT EXISTS idx_user_interactions_user_job ON user_interactions(user_id, job_id);
CREATE INDEX IF NOT EXISTS idx_user_interactions_type ON user_interactions(interaction_type);

CREATE INDEX IF NOT EXISTS idx_conversation_logs_session ON conversation_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_user ON conversation_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_conversation_turns_session ON conversation_turns(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_score_history_session ON score_history(user_id, session_id, turn_number);

CREATE INDEX IF NOT EXISTS idx_missing_job_info_job ON missing_job_info_log(job_id);
CREATE INDEX IF NOT EXISTS idx_missing_job_info_field ON missing_job_info_log(missing_field);

CREATE INDEX IF NOT EXISTS idx_global_trends_key ON global_preference_trends(preference_key);
CREATE INDEX IF NOT EXISTS idx_global_trends_score ON global_preference_trends(trend_score DESC);

-- ============================================
-- サンプルデータ挿入（トレンド閾値）
-- ============================================

INSERT INTO trend_thresholds (threshold_name, threshold_value, description) 
VALUES 
    ('high_demand_threshold', 10, '高需要と判断する最小出現回数'),
    ('medium_demand_threshold', 5, '中需要と判断する最小出現回数'),
    ('question_generation_threshold', 3, '動的質問を生成する最小出現回数')
ON CONFLICT (threshold_name) DO NOTHING;

-- ============================================
-- コメント追加
-- ============================================

COMMENT ON TABLE personal_date IS 'ユーザー基本情報';
COMMENT ON TABLE company_date IS '企業基本情報';
COMMENT ON TABLE company_profile IS '求人情報（3層構造）';
COMMENT ON TABLE conversation_logs IS '会話ログ（メイン）';
COMMENT ON TABLE user_interactions IS 'ユーザー行動追跡';
COMMENT ON TABLE missing_job_info_log IS '不足情報検知ログ';
COMMENT ON TABLE company_enrichment_requests IS '企業への追加質問リクエスト';
COMMENT ON TABLE global_preference_trends IS 'グローバル嗜好トレンド分析';

-- ============================================
-- 完了メッセージ
-- ============================================

DO $$ 
BEGIN 
    RAISE NOTICE '✅ データベーススキーマの作成が完了しました';
    RAISE NOTICE '📊 テーブル数: 約30テーブル';
    RAISE NOTICE '🔍 インデックス: パフォーマンス最適化済み';
END $$;