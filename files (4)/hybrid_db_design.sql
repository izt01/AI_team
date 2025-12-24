-- ============================================================================
-- JobMatch AI - ハイブリッド方式 DB設計
-- ============================================================================
-- 
-- このスクリプトは、構造化データ + 非構造化データのハイブリッド方式で
-- company_profile テーブルを再設計します。
--
-- 【設計思想】
-- Layer 1: 必須構造化データ（20-30項目）→ 高速検索用
-- Layer 2: カテゴリ別自由記述 → AI処理用
-- Layer 3: 完全自由記述 → 柔軟性確保
--
-- 実行方法:
-- psql -U devuser -d jobmatch -f hybrid_db_design.sql
--
-- ============================================================================

-- 既存テーブルを削除（開発環境のみ！本番では注意）
-- DROP TABLE IF EXISTS company_profile CASCADE;
-- DROP TABLE IF EXISTS job_embeddings CASCADE;

-- ============================================================================
-- メインテーブル: company_profile（ハイブリッド方式）
-- ============================================================================

CREATE TABLE IF NOT EXISTS company_profile_hybrid (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    
    -- ========================================
    -- Layer 1: 必須構造化データ（検索・フィルタリング用）
    -- ========================================
    
    -- 基本情報
    job_title VARCHAR(100) NOT NULL,
    location_prefecture VARCHAR(50) NOT NULL,
    location_city VARCHAR(100),
    salary_min INTEGER NOT NULL,
    salary_max INTEGER NOT NULL,
    employment_type VARCHAR(50),  -- 正社員/契約社員/業務委託
    
    -- 働き方の基本（最重要項目のみ）
    remote_option VARCHAR(50),  -- 完全リモート可/ハイブリッド/なし
    flex_time BOOLEAN DEFAULT FALSE,
    earliest_start_time TIME,  -- 最も早い出社時間
    latest_start_time TIME,    -- 最も遅い出社時間（満員電車回避）
    side_job_allowed BOOLEAN DEFAULT FALSE,
    
    -- 技術スタック（JSONB形式で柔軟に）
    tech_stack JSONB,
    /*
    例:
    {
        "languages": ["Python", "JavaScript"],
        "frameworks": ["Django", "React"],
        "databases": ["PostgreSQL"],
        "infrastructure": ["AWS", "Docker"],
        "tools": ["GitHub", "Slack"]
    }
    */
    
    -- 成長機会の基本
    training_available BOOLEAN DEFAULT FALSE,  -- 研修制度あり
    mentor_system BOOLEAN DEFAULT FALSE,       -- メンター制度あり
    conference_support BOOLEAN DEFAULT FALSE,  -- カンファレンス支援あり
    book_budget INTEGER DEFAULT 0,             -- 書籍購入予算（月額）
    
    -- 福利厚生の基本
    remote_work_allowance INTEGER DEFAULT 0,   -- リモートワーク手当（月額）
    housing_allowance INTEGER DEFAULT 0,       -- 住宅手当（月額）
    
    -- チームの基本（最重要項目のみ）
    team_size VARCHAR(50),      -- 例: "5-10名"
    development_method VARCHAR(50),  -- アジャイル/スクラム/ウォーターフォール
    
    -- ========================================
    -- Layer 2: カテゴリ別自由記述（AI処理用）
    -- ========================================
    
    work_style_details TEXT,
    /*
    企業が自由に記述:
    「フレックスタイム制で7:00-22:00の間で自由に勤務可能。
     コアタイムは11:00-15:00。10時出社も歓迎。
     リモートワークは週3日まで可能。月1回のワーケーションOK。」
    */
    
    team_culture_details TEXT,
    /*
    企業が自由に記述:
    「5-7名のスクラムチーム。平均年齢32歳。
     フラットな組織で役職関係なく意見が言える。
     週1回のチームランチで交流。ペット同伴出勤OK。」
    */
    
    growth_opportunities_details TEXT,
    /*
    企業が自由に記述:
    「入社時3ヶ月の新人研修プログラム。
     技術書購入は上限なし。カンファレンス参加は年2回まで全額補助。
     週1時間の学習時間を勤務時間内に確保。」
    */
    
    benefits_details TEXT,
    /*
    企業が自由に記述:
    「リモートワーク手当月1万円。住宅手当月3万円。
     社員食堂あり。フィットネスジム利用補助。
     ストックオプション制度。退職金制度あり。」
    */
    
    office_environment_details TEXT,
    /*
    企業が自由に記述:
    「MacBook Pro支給、モニター2枚。
     フリーアドレス制。集中ブースあり。
     カフェスペース、仮眠室完備。駅から徒歩3分。」
    */
    
    project_details TEXT,
    /*
    企業が自由に記述:
    「自社サービスの開発。ユーザー数100万人超。
     最新技術の導入に積極的。AWS/Kubernetesを活用。
     マイクロサービスアーキテクチャ。」
    */
    
    -- ========================================
    -- Layer 3: 完全自由記述
    -- ========================================
    
    company_appeal_text TEXT,
    /*
    企業からの完全自由アピール:
    「当社は創業5年のスタートアップです。
     社員全員が株式を保有し、会社の成長を一緒に作っています。
     失敗を恐れずチャレンジできる文化を大切にしています。
     ペット同伴出勤、サウナ・ジム使い放題など、
     ユニークな福利厚生も充実しています。」
    */
    
    free_description TEXT,
    /*
    その他、何でも自由に記述:
    （予測不可能な新しい働き方、制度など）
    */
    
    -- ========================================
    -- AI処理結果（キャッシュ）
    -- ========================================
    
    ai_extracted_features JSONB,
    /*
    AIが自動抽出した特徴をキャッシュ:
    {
        "work_flexibility": {
            "late_start_available": true,
            "latest_start_time": "10:00",
            "workation_available": true,
            "pet_friendly": true
        },
        "team_characteristics": {
            "team_size": "5-7名",
            "average_age": 32,
            "flat_organization": true
        },
        "unique_benefits": [
            "ペット同伴出勤可",
            "ワーケーション制度",
            "サウナ・ジム使い放題"
        ],
        "keywords": ["スタートアップ", "フラット", "挑戦"]
    }
    */
    
    last_ai_extraction_at TIMESTAMP,  -- 最終AI処理日時
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (company_id) REFERENCES company_date(company_id) ON DELETE CASCADE
);

-- ============================================================================
-- ベクトル検索用テーブル（pgvector拡張を使用）
-- ============================================================================

-- pgvector拡張を有効化（未インストールの場合はスキップ）
-- CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS job_embeddings (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES company_profile_hybrid(id) ON DELETE CASCADE,
    embedding_type VARCHAR(50) NOT NULL,  -- 'full_description', 'work_style', etc.
    embedding vector(1536),  -- OpenAI text-embedding-3-large (1536次元)
    source_text TEXT,         -- 元のテキスト
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- インデックス作成
-- ============================================================================

-- Layer 1（構造化データ）の検索用インデックス
CREATE INDEX idx_cp_hybrid_basic 
    ON company_profile_hybrid(job_title, location_prefecture, salary_min);

CREATE INDEX idx_cp_hybrid_remote 
    ON company_profile_hybrid(remote_option);

CREATE INDEX idx_cp_hybrid_flex 
    ON company_profile_hybrid(flex_time) 
    WHERE flex_time = TRUE;

CREATE INDEX idx_cp_hybrid_side_job 
    ON company_profile_hybrid(side_job_allowed) 
    WHERE side_job_allowed = TRUE;

-- JSONB検索用GINインデックス
CREATE INDEX idx_cp_hybrid_tech_stack 
    ON company_profile_hybrid USING GIN(tech_stack);

CREATE INDEX idx_cp_hybrid_ai_features 
    ON company_profile_hybrid USING GIN(ai_extracted_features);

-- Layer 2/3（テキストデータ）の全文検索用インデックス
-- PostgreSQLのテキスト検索機能を使用
CREATE INDEX idx_cp_hybrid_work_style_fts 
    ON company_profile_hybrid USING GIN(to_tsvector('japanese', work_style_details));

CREATE INDEX idx_cp_hybrid_team_culture_fts 
    ON company_profile_hybrid USING GIN(to_tsvector('japanese', team_culture_details));

CREATE INDEX idx_cp_hybrid_appeal_fts 
    ON company_profile_hybrid USING GIN(to_tsvector('japanese', company_appeal_text));

-- ベクトル検索用インデックス（pgvectorがインストールされている場合）
-- CREATE INDEX idx_job_embeddings_vector 
--     ON job_embeddings USING ivfflat(embedding vector_cosine_ops) 
--     WITH (lists = 100);

-- ============================================================================
-- コメント追加
-- ============================================================================

COMMENT ON TABLE company_profile_hybrid IS 'ハイブリッド方式の求人情報テーブル（構造化 + 非構造化データ）';

COMMENT ON COLUMN company_profile_hybrid.tech_stack IS '技術スタック（JSONB形式）';
COMMENT ON COLUMN company_profile_hybrid.work_style_details IS '働き方の詳細（自由記述）';
COMMENT ON COLUMN company_profile_hybrid.team_culture_details IS 'チーム・文化の詳細（自由記述）';
COMMENT ON COLUMN company_profile_hybrid.growth_opportunities_details IS '成長機会の詳細（自由記述）';
COMMENT ON COLUMN company_profile_hybrid.benefits_details IS '福利厚生の詳細（自由記述）';
COMMENT ON COLUMN company_profile_hybrid.office_environment_details IS 'オフィス環境の詳細（自由記述）';
COMMENT ON COLUMN company_profile_hybrid.project_details IS 'プロジェクトの詳細（自由記述）';
COMMENT ON COLUMN company_profile_hybrid.company_appeal_text IS '企業からの自由アピール';
COMMENT ON COLUMN company_profile_hybrid.free_description IS 'その他自由記述';
COMMENT ON COLUMN company_profile_hybrid.ai_extracted_features IS 'AIが抽出した特徴（キャッシュ）';

COMMENT ON TABLE job_embeddings IS 'ベクトル検索用のEmbeddingテーブル';

-- ============================================================================
-- ビュー作成（互換性確保）
-- ============================================================================

-- 既存のcompany_profileテーブルとの互換性のためのビュー
CREATE OR REPLACE VIEW company_profile AS
SELECT 
    id,
    company_id,
    job_title,
    location_prefecture,
    location_city,
    salary_min,
    salary_max,
    employment_type,
    remote_option,
    
    -- Layer 2/3のテキストを結合して従来のカラム風に見せる
    work_style_details AS job_summary,
    remote_option AS remote_work,
    team_culture_details AS company_culture,
    
    created_at,
    updated_at
FROM company_profile_hybrid;

-- ============================================================================
-- サンプルデータ挿入（テスト用）
-- ============================================================================

INSERT INTO company_profile_hybrid (
    company_id,
    job_title,
    location_prefecture,
    salary_min,
    salary_max,
    employment_type,
    remote_option,
    flex_time,
    latest_start_time,
    side_job_allowed,
    tech_stack,
    training_available,
    mentor_system,
    conference_support,
    book_budget,
    team_size,
    development_method,
    work_style_details,
    team_culture_details,
    growth_opportunities_details,
    benefits_details,
    office_environment_details,
    project_details,
    company_appeal_text
) VALUES (
    1,
    'フルスタックエンジニア',
    '東京都',
    500,
    800,
    '正社員',
    'ハイブリッド',
    TRUE,
    '10:00',
    TRUE,
    '{"languages": ["Python", "TypeScript"], "frameworks": ["Django", "React"], "databases": ["PostgreSQL"], "infrastructure": ["AWS", "Docker"]}'::jsonb,
    TRUE,
    TRUE,
    TRUE,
    10000,
    '5-7名',
    'スクラム',
    'フレックスタイム制で7:00-22:00の間で自由に勤務可能。コアタイムは11:00-15:00。10時出社も歓迎しており、満員電車を避けたい方にも最適です。リモートワークは週3日まで可能で、月1回のワーケーションも推奨しています。',
    '5-7名のスクラムチーム。平均年齢32歳で、エンジニア経験3-8年のメンバーが中心です。フラットな組織で役職に関係なく意見が言いやすい環境。週1回のチームランチで交流を深めています。ペット同伴出勤もOKで、オフィスには猫が3匹います。',
    '入社時に3ヶ月の新人研修プログラムを実施。メンター制度で先輩エンジニアが1on1でサポート。技術書購入は上限なし、カンファレンス参加は年2回まで全額補助。週1時間の学習時間を勤務時間内に確保しており、自己成長を強く支援します。',
    'リモートワーク手当月1万円、住宅手当月3万円。社員食堂あり（昼食300円）。フィットネスジム利用補助（月5000円）。ストックオプション制度あり。退職金制度完備。年2回の社員旅行（海外含む）。',
    'MacBook Pro（M3, 32GB RAM）支給、4Kモニター2枚。フリーアドレス制で好きな場所で作業可能。集中ブースあり。カフェスペース、仮眠室、シャワールーム完備。駅から徒歩3分の好立地。',
    '自社サービス「TechMatch」の開発・運用。ユーザー数100万人超のプラットフォーム。最新技術の導入に積極的で、AWS/Kubernetes/Terraformを活用。マイクロサービスアーキテクチャで設計されており、技術的なチャレンジができます。',
    '当社は創業5年のスタートアップです。社員全員が株式を保有し、会社の成長を一緒に作り上げています。失敗を恐れずチャレンジできる文化を大切にしており、新しいアイデアは積極的に試せます。ペット同伴出勤、サウナ・ジム使い放題など、ユニークな福利厚生も充実。エンジニアファーストの環境で、技術的な意思決定はエンジニアが主導します。'
);

-- ============================================================================
-- 完了メッセージ
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '✅ ハイブリッド方式のDB設計が完了しました！';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '';
    RAISE NOTICE '【作成されたテーブル】';
    RAISE NOTICE '  - company_profile_hybrid（メインテーブル）';
    RAISE NOTICE '  - job_embeddings（ベクトル検索用）';
    RAISE NOTICE '  - company_profile（互換性ビュー）';
    RAISE NOTICE '';
    RAISE NOTICE '【特徴】';
    RAISE NOTICE '  Layer 1: 必須構造化データ（20-30項目）→ 高速検索';
    RAISE NOTICE '  Layer 2: カテゴリ別自由記述 → AI処理';
    RAISE NOTICE '  Layer 3: 完全自由記述 → 柔軟性確保';
    RAISE NOTICE '';
    RAISE NOTICE '【次のステップ】';
    RAISE NOTICE '  1. AI特徴抽出スクリプトを実行';
    RAISE NOTICE '  2. Embeddingを生成（pgvectorインストール後）';
    RAISE NOTICE '  3. アプリケーションのマッチングロジックを更新';
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
END $$;
