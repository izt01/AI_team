-- ============================================================================
-- JobMatch AI - Phase 1: 緊急対応カラム追加スクリプト
-- ============================================================================
-- 
-- このスクリプトは、ユーザーの自由な回答に対応するための
-- 最低限必要なカラムを company_profile テーブルに追加します。
--
-- 実行方法:
-- psql -U devuser -d jobmatch -f phase1_add_columns.sql
--
-- ============================================================================

\echo '============================================================================'
\echo 'Phase 1: 緊急対応カラム追加開始'
\echo '============================================================================'

-- ============================================================================
-- 1. 働き方の詳細カラム追加
-- ============================================================================

\echo ''
\echo '📋 Step 1: 働き方の詳細カラムを追加中...'

-- フレックスタイム制度
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    flex_time BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN company_profile.flex_time IS 'フレックスタイム制度の有無';

-- コアタイム（フレックスの場合）
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    core_time VARCHAR(50);

COMMENT ON COLUMN company_profile.core_time IS 'コアタイム（例: "11:00-15:00"）';

-- 最も早い出社時間
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    earliest_start_time TIME;

COMMENT ON COLUMN company_profile.earliest_start_time IS '最も早い出社可能時間';

-- 最も遅い出社時間
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    latest_start_time TIME;

COMMENT ON COLUMN company_profile.latest_start_time IS '最も遅い出社可能時間（満員電車回避）';

-- 時短勤務の可否
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    part_time_available BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN company_profile.part_time_available IS '時短勤務の可否';

-- 副業の可否
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    side_job_allowed BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN company_profile.side_job_allowed IS '副業の可否';

-- 服装規定
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    dress_code VARCHAR(50) DEFAULT 'オフィスカジュアル';

COMMENT ON COLUMN company_profile.dress_code IS '服装規定（自由/オフィスカジュアル/スーツ）';

\echo '✅ 働き方の詳細カラムを追加完了'

-- ============================================================================
-- 2. チーム・組織カラム追加
-- ============================================================================

\echo ''
\echo '👥 Step 2: チーム・組織カラムを追加中...'

-- チームサイズ
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    team_size VARCHAR(50);

COMMENT ON COLUMN company_profile.team_size IS 'チームサイズ（例: "5-10名"）';

-- 平均年齢
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    average_age INTEGER;

COMMENT ON COLUMN company_profile.average_age IS 'チームの平均年齢';

-- 外国人比率
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    foreign_ratio INTEGER;

COMMENT ON COLUMN company_profile.foreign_ratio IS '外国人メンバーの比率（%）';

-- 女性比率
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    female_ratio INTEGER;

COMMENT ON COLUMN company_profile.female_ratio IS '女性メンバーの比率（%）';

-- 開発手法
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    development_method VARCHAR(50);

COMMENT ON COLUMN company_profile.development_method IS '開発手法（アジャイル/スクラム/ウォーターフォール等）';

\echo '✅ チーム・組織カラムを追加完了'

-- ============================================================================
-- 3. 成長・学習カラム追加
-- ============================================================================

\echo ''
\echo '📚 Step 3: 成長・学習カラムを追加中...'

-- 研修制度
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    training_program TEXT;

COMMENT ON COLUMN company_profile.training_program IS '研修制度の詳細';

-- 勉強会の頻度
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    study_session_frequency VARCHAR(50);

COMMENT ON COLUMN company_profile.study_session_frequency IS '勉強会の頻度（週1回/月2回等）';

-- カンファレンス参加支援
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    conference_support BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN company_profile.conference_support IS 'カンファレンス参加支援の有無';

-- 書籍購入予算
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    book_purchase_budget INTEGER DEFAULT 0;

COMMENT ON COLUMN company_profile.book_purchase_budget IS '書籍購入予算（月額円）';

-- メンター制度
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    mentor_system BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN company_profile.mentor_system IS 'メンター制度の有無';

\echo '✅ 成長・学習カラムを追加完了'

-- ============================================================================
-- 4. 評価・キャリアカラム追加
-- ============================================================================

\echo ''
\echo '📈 Step 4: 評価・キャリアカラムを追加中...'

-- 評価制度
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    evaluation_system TEXT;

COMMENT ON COLUMN company_profile.evaluation_system IS '評価制度の詳細';

-- 昇給頻度
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    salary_review_frequency VARCHAR(50);

COMMENT ON COLUMN company_profile.salary_review_frequency IS '昇給の頻度（年1回/年2回等）';

-- キャリアパス
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    career_path TEXT;

COMMENT ON COLUMN company_profile.career_path IS 'キャリアパスの詳細';

-- 昇進基準
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    promotion_criteria TEXT;

COMMENT ON COLUMN company_profile.promotion_criteria IS '昇進基準';

\echo '✅ 評価・キャリアカラムを追加完了'

-- ============================================================================
-- 5. 福利厚生の詳細カラム追加
-- ============================================================================

\echo ''
\echo '💰 Step 5: 福利厚生の詳細カラムを追加中...'

-- リモートワーク手当
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    remote_work_allowance INTEGER DEFAULT 0;

COMMENT ON COLUMN company_profile.remote_work_allowance IS 'リモートワーク手当（月額円）';

-- 住宅手当
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    housing_allowance INTEGER DEFAULT 0;

COMMENT ON COLUMN company_profile.housing_allowance IS '住宅手当（月額円）';

-- 交通費上限
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    commute_allowance_limit INTEGER DEFAULT 0;

COMMENT ON COLUMN company_profile.commute_allowance_limit IS '交通費上限（月額円）';

-- 退職金制度
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    retirement_plan BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN company_profile.retirement_plan IS '退職金制度の有無';

\echo '✅ 福利厚生の詳細カラムを追加完了'

-- ============================================================================
-- 6. 職場環境カラム追加
-- ============================================================================

\echo ''
\echo '🖥️  Step 6: 職場環境カラムを追加中...'

-- PC環境
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    pc_spec TEXT;

COMMENT ON COLUMN company_profile.pc_spec IS 'PC環境（例: "MacBook Pro/Windows選択可"）';

-- モニター枚数
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    monitor_count INTEGER DEFAULT 1;

COMMENT ON COLUMN company_profile.monitor_count IS 'モニター枚数';

-- オフィス設備
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    office_facilities TEXT;

COMMENT ON COLUMN company_profile.office_facilities IS 'オフィス設備の詳細';

-- 静かな作業環境
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    quiet_workspace BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN company_profile.quiet_workspace IS '静かな作業環境の有無';

\echo '✅ 職場環境カラムを追加完了'

-- ============================================================================
-- 7. プロジェクト詳細カラム追加（JSONB使用）
-- ============================================================================

\echo ''
\echo '🔧 Step 7: プロジェクト詳細カラムを追加中...'

-- 技術スタック（JSONB形式）
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    tech_stack JSONB;

COMMENT ON COLUMN company_profile.tech_stack IS '技術スタックの詳細（JSONB形式）';

-- プロジェクト規模
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    project_scale VARCHAR(50);

COMMENT ON COLUMN company_profile.project_scale IS 'プロジェクト規模（小規模/中規模/大規模）';

-- チーム構成
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    team_structure TEXT;

COMMENT ON COLUMN company_profile.team_structure IS 'チーム構成の詳細';

-- 開発プロセス
ALTER TABLE company_profile ADD COLUMN IF NOT EXISTS 
    development_process TEXT;

COMMENT ON COLUMN company_profile.development_process IS '開発プロセスの詳細';

\echo '✅ プロジェクト詳細カラムを追加完了'

-- ============================================================================
-- 8. インデックス作成
-- ============================================================================

\echo ''
\echo '📑 Step 8: インデックスを作成中...'

-- フレックスタイム検索用
CREATE INDEX IF NOT EXISTS idx_company_profile_flex_time 
    ON company_profile(flex_time) WHERE flex_time = TRUE;

-- 副業可検索用
CREATE INDEX IF NOT EXISTS idx_company_profile_side_job 
    ON company_profile(side_job_allowed) WHERE side_job_allowed = TRUE;

-- 技術スタック検索用（GINインデックス）
CREATE INDEX IF NOT EXISTS idx_company_profile_tech_stack 
    ON company_profile USING GIN(tech_stack);

\echo '✅ インデックスを作成完了'

-- ============================================================================
-- 9. 確認
-- ============================================================================

\echo ''
\echo '🔍 Step 9: 追加されたカラムを確認中...'

-- 追加されたカラムをリスト表示
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'company_profile'
    AND column_name IN (
        'flex_time', 'core_time', 'earliest_start_time', 'latest_start_time',
        'part_time_available', 'side_job_allowed', 'dress_code',
        'team_size', 'average_age', 'foreign_ratio', 'female_ratio', 'development_method',
        'training_program', 'study_session_frequency', 'conference_support', 
        'book_purchase_budget', 'mentor_system',
        'evaluation_system', 'salary_review_frequency', 'career_path', 'promotion_criteria',
        'remote_work_allowance', 'housing_allowance', 'commute_allowance_limit', 'retirement_plan',
        'pc_spec', 'monitor_count', 'office_facilities', 'quiet_workspace',
        'tech_stack', 'project_scale', 'team_structure', 'development_process'
    )
ORDER BY ordinal_position;

\echo ''
\echo '============================================================================'
\echo '✅ Phase 1: カラム追加が完了しました！'
\echo '============================================================================'
\echo ''
\echo '追加されたカラム数: 35個'
\echo ''
\echo '次のステップ:'
\echo '1. ダミーデータを更新: python update_dummy_data_phase1.py'
\echo '2. アプリケーションのスコアリングロジックを更新'
\echo ''
\echo '============================================================================'
