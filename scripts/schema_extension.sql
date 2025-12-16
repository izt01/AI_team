-- ==========================================
-- 学習型求人マッチングシステム - スキーマ拡張
-- ==========================================

-- pgvector拡張を有効化（ベクトル検索用）
CREATE EXTENSION IF NOT EXISTS vector;

-- ==========================================
-- 1. ユーザー行動履歴テーブル
-- ==========================================
CREATE TABLE IF NOT EXISTS user_interactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES personal_date(user_id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL,
    interaction_type VARCHAR(20) NOT NULL CHECK (interaction_type IN ('click', 'favorite', 'apply', 'view', 'chat_mention')),
    interaction_value FLOAT DEFAULT 0.0,  -- 閲覧時間（秒）やその他の数値
    metadata JSONB,  -- 追加情報（クリック位置、デバイスタイプなど）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_interactions_user ON user_interactions(user_id);
CREATE INDEX idx_user_interactions_job ON user_interactions(job_id);
CREATE INDEX idx_user_interactions_type ON user_interactions(interaction_type);
CREATE INDEX idx_user_interactions_created ON user_interactions(created_at DESC);

-- ==========================================
-- 2. チャット履歴テーブル
-- ==========================================
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES personal_date(user_id) ON DELETE CASCADE,
    message_type VARCHAR(10) NOT NULL CHECK (message_type IN ('user', 'bot')),
    message_text TEXT NOT NULL,
    extracted_intent JSONB,  -- AIが抽出した意図（JSON形式）
    session_id VARCHAR(100),  -- セッションID（同一会話をグループ化）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_history_user ON chat_history(user_id);
CREATE INDEX idx_chat_history_session ON chat_history(session_id);
CREATE INDEX idx_chat_history_created ON chat_history(created_at DESC);

-- ==========================================
-- 3. 動的質問マスタテーブル
-- ==========================================
CREATE TABLE IF NOT EXISTS dynamic_questions (
    id SERIAL PRIMARY KEY,
    question_key VARCHAR(100) NOT NULL UNIQUE,  -- 質問の識別子（例: 'remote_work'）
    question_text TEXT NOT NULL,  -- 質問文
    category VARCHAR(50) NOT NULL,  -- カテゴリ（'働き方', 'キャリアパス', '企業文化'など）
    question_type VARCHAR(20) DEFAULT 'boolean',  -- 質問タイプ（boolean, choice, text）
    options JSONB,  -- 選択肢（question_typeがchoiceの場合）
    usage_count INTEGER DEFAULT 0,  -- 質問が使われた回数
    positive_response_count INTEGER DEFAULT 0,  -- この質問後に良い結果（お気に入り、応募）があった回数
    effectiveness_score FLOAT DEFAULT 0.0,  -- 有効性スコア（positive_response_count / usage_count）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_questions_category ON dynamic_questions(category);
CREATE INDEX idx_questions_effectiveness ON dynamic_questions(effectiveness_score DESC);

-- ==========================================
-- 4. ユーザーの質問への回答テーブル
-- ==========================================
CREATE TABLE IF NOT EXISTS user_question_responses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES personal_date(user_id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES dynamic_questions(id) ON DELETE CASCADE,
    response_text TEXT NOT NULL,  -- ユーザーの生の回答
    normalized_response TEXT,  -- AIが正規化した回答
    confidence_score FLOAT DEFAULT 0.0,  -- AIの抽出確信度
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, question_id)  -- 同じ質問には1回だけ回答
);

CREATE INDEX idx_user_responses_user ON user_question_responses(user_id);
CREATE INDEX idx_user_responses_question ON user_question_responses(question_id);

-- ==========================================
-- 5. 求人の多軸属性テーブル
-- ==========================================
CREATE TABLE IF NOT EXISTS job_attributes (
    job_id INTEGER PRIMARY KEY,  -- company_profile.idを参照
    company_culture JSONB,  -- 企業文化（例: {"type": "startup", "atmosphere": "flat", "size": "small"}）
    work_flexibility JSONB,  -- 働き方の柔軟性（例: {"remote": true, "flex_time": true, "side_job": false}）
    career_path JSONB,  -- キャリアパス（例: {"growth_opportunities": true, "training": true, "promotion_speed": "fast"}）
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_job_attributes_culture ON job_attributes USING GIN(company_culture);
CREATE INDEX idx_job_attributes_flexibility ON job_attributes USING GIN(work_flexibility);
CREATE INDEX idx_job_attributes_career ON job_attributes USING GIN(career_path);

-- ==========================================
-- 6. ユーザーの多軸評価プロファイルテーブル
-- ==========================================
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES personal_date(user_id) ON DELETE CASCADE,
    preference_vector vector(1536),  -- OpenAI Embeddingによるベクトル表現
    company_culture_pref JSONB,  -- 企業文化の好み
    work_flexibility_pref JSONB,  -- 働き方の好み
    career_path_pref JSONB,  -- キャリアパスの好み
    preference_text TEXT,  -- プロファイルのテキスト表現（embedding生成元）
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ベクトル類似度検索用のインデックス（IVFFlat）
CREATE INDEX idx_user_pref_vector ON user_preferences
USING ivfflat (preference_vector vector_cosine_ops)
WITH (lists = 100);

-- ==========================================
-- 7. 機械学習モデルスコアテーブル
-- ==========================================
CREATE TABLE IF NOT EXISTS ml_model_scores (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES personal_date(user_id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL,
    score FLOAT NOT NULL,  -- 予測スコア（0.0〜1.0）
    model_version VARCHAR(50) NOT NULL,  -- モデルのバージョン
    feature_importance JSONB,  -- 特徴量の重要度
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, job_id, model_version)
);

CREATE INDEX idx_ml_scores_user ON ml_model_scores(user_id);
CREATE INDEX idx_ml_scores_job ON ml_model_scores(job_id);
CREATE INDEX idx_ml_scores_score ON ml_model_scores(score DESC);

-- ==========================================
-- 8. company_profileテーブルにベクトル列を追加
-- ==========================================
-- 既存のembedding列（TEXT型）をvector型に変更
ALTER TABLE company_profile
ADD COLUMN IF NOT EXISTS embedding_vector vector(1536);

-- 既存のembedding（TEXT）からvector型に変換
-- 注意: 既存データがある場合は、別途マイグレーションスクリプトで変換が必要

-- ベクトル検索用インデックス
CREATE INDEX IF NOT EXISTS idx_company_profile_vector
ON company_profile
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 100);

-- ==========================================
-- 9. 既存テーブルへの列追加
-- ==========================================

-- user_profileテーブルに列を追加
ALTER TABLE user_profile
ADD COLUMN IF NOT EXISTS preference_embedding vector(1536),
ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- company_profileテーブルに列を追加
ALTER TABLE company_profile
ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS favorite_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS apply_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS click_count INTEGER DEFAULT 0;

-- ==========================================
-- 10. 初期データ: デフォルト質問セット
-- ==========================================
INSERT INTO dynamic_questions (question_key, question_text, category, question_type, options) VALUES
('remote_work', 'リモートワーク可能な求人を希望しますか？', '働き方の柔軟性', 'boolean', NULL),
('flex_time', 'フレックスタイム制度を希望しますか？', '働き方の柔軟性', 'boolean', NULL),
('side_job', '副業可能な求人を希望しますか？', '働き方の柔軟性', 'boolean', NULL),
('company_size', '企業規模の希望はありますか？', '企業文化・雰囲気', 'choice', '["大企業", "中堅企業", "ベンチャー", "スタートアップ"]'::jsonb),
('company_atmosphere', '組織の雰囲気はどのようなものが良いですか？', '企業文化・雰囲気', 'choice', '["フラットな組織", "縦型組織", "チャレンジング", "堅実"]'::jsonb),
('career_growth', 'キャリア成長の機会を重視しますか？', 'キャリアパス', 'boolean', NULL),
('training_support', '研修・スキルアップ支援を重視しますか？', 'キャリアパス', 'boolean', NULL),
('promotion_speed', '昇進スピードを重視しますか？', 'キャリアパス', 'boolean', NULL)
ON CONFLICT (question_key) DO NOTHING;

-- ==========================================
-- 11. ビューの作成: ユーザー行動サマリー
-- ==========================================
CREATE OR REPLACE VIEW user_interaction_summary AS
SELECT
    user_id,
    COUNT(*) FILTER (WHERE interaction_type = 'click') as total_clicks,
    COUNT(*) FILTER (WHERE interaction_type = 'favorite') as total_favorites,
    COUNT(*) FILTER (WHERE interaction_type = 'apply') as total_applies,
    COUNT(*) FILTER (WHERE interaction_type = 'view') as total_views,
    AVG(interaction_value) FILTER (WHERE interaction_type = 'view') as avg_view_time,
    MAX(created_at) as last_interaction_at
FROM user_interactions
GROUP BY user_id;

-- ==========================================
-- 12. ビューの作成: 求人の人気度スコア
-- ==========================================
CREATE OR REPLACE VIEW job_popularity_score AS
SELECT
    job_id,
    COUNT(*) FILTER (WHERE interaction_type = 'click') as click_count,
    COUNT(*) FILTER (WHERE interaction_type = 'favorite') as favorite_count,
    COUNT(*) FILTER (WHERE interaction_type = 'apply') as apply_count,
    COUNT(*) FILTER (WHERE interaction_type = 'view') as view_count,
    -- 人気度スコア計算（重み付け）
    (COUNT(*) FILTER (WHERE interaction_type = 'apply') * 10.0 +
     COUNT(*) FILTER (WHERE interaction_type = 'favorite') * 5.0 +
     COUNT(*) FILTER (WHERE interaction_type = 'click') * 2.0 +
     COUNT(*) FILTER (WHERE interaction_type = 'view') * 1.0) as popularity_score
FROM user_interactions
GROUP BY job_id;

-- ==========================================
-- 13. トリガー: 質問の有効性スコア自動更新
-- ==========================================
CREATE OR REPLACE FUNCTION update_question_effectiveness()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE dynamic_questions
    SET
        effectiveness_score = CASE
            WHEN usage_count > 0 THEN positive_response_count::FLOAT / usage_count::FLOAT
            ELSE 0.0
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.question_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_question_effectiveness
AFTER INSERT ON user_question_responses
FOR EACH ROW
EXECUTE FUNCTION update_question_effectiveness();

-- ==========================================
-- 完了メッセージ
-- ==========================================
-- スキーマ拡張が完了しました
