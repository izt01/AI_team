# JobMatch AI - 改善提案書

## 📋 現状の問題点

### 1. **DB・求人情報の不足** ⚠️ 最重要

#### 問題
現在の`company_profile`テーブルには以下の重要な情報が**不足または不十分**です：

| カテゴリ | 不足している情報 | 影響 |
|---------|----------------|------|
| **働き方の詳細** | - フレックスタイム制度の詳細<br>- コアタイムの有無<br>- 時短勤務の可否<br>- 副業可否<br>- 服装規定 | ユーザーの「満員電車を避けたい」「柔軟な働き方」などの要望に対応できない |
| **チーム・組織** | - チームサイズ<br>- 平均年齢<br>- 外国人比率<br>- 女性比率<br>- 開発手法（アジャイル/ウォーターフォール） | 「フラットな組織」「若い環境」などの要望に対応できない |
| **成長・学習** | - 研修制度の詳細<br>- 勉強会の頻度<br>- カンファレンス参加支援<br>- 書籍購入制度<br>- メンター制度 | 「学習機会」「スキルアップ」などの要望に対応できない |
| **評価・キャリア** | - 評価制度<br>- 昇進・昇給の頻度<br>- キャリアパス<br>- 異動の可能性 | 「キャリアアップ」「安定性」などの要望に対応できない |
| **福利厚生の詳細** | - リモートワーク手当の金額<br>- 住宅手当の条件・金額<br>- 各種手当の詳細<br>- 退職金制度 | 「待遇」「安定性」などの要望に正確に対応できない |
| **職場環境** | - オフィス設備<br>- 開発環境（PC、モニター枚数）<br>- 休憩スペース<br>- 私語の可否 | 「働きやすさ」「環境」などの要望に対応できない |
| **プロジェクト詳細** | - プロジェクトの規模<br>- 使用技術スタック（詳細）<br>- チーム構成<br>- 開発プロセス | 「やりがい」「技術スタック」などの要望に対応できない |

### 2. **スコアリングロジックの限界** ⚠️

#### 問題
現在のスコアリングは**ハードコーディングされた条件マッチング**のみです：

```python
# 現在の実装（一部抜粋）
if remote_pref in ['強く希望', '希望']:
    if '完全' in remote_option:
        job['score'] += 20  # ← 固定値
    elif 'ハイブリッド' in remote_option:
        job['score'] += 10  # ← 固定値
```

#### 限界
- **柔軟性がない**: ユーザーが「満員電車を避けたい」と言った場合、リモートワーク以外の選択肢（フレックスタイム、10時出社）を考慮できない
- **複雑な条件に対応できない**: 「年収は妥協できるが、ワークライフバランスは重視」のような複雑な優先順位を反映できない
- **代替案の提示が不十分**: DBに代替案の情報がないため、AIが提案しても実際にマッチングできない

### 3. **意図抽出の精度問題** ⚠️

#### 問題
AIの意図抽出は優れていますが、**抽出した情報を活用する仕組みが不完全**です：

```python
"alternative_condition_acceptance": {
    "accepted": true,
    "condition_type": "work_hours",
    "details": "10時出社",
    "reason": "満員電車を避けたい"
}
```

→ しかし、**求人データに「10時出社可」の情報がない**ため、マッチングできない

---

## 🛠️ 改善提案

### 提案1: **求人情報テーブルの大幅拡張** ⭐⭐⭐⭐⭐ 最優先

#### 新規カラム（company_profile テーブル）

```sql
-- === 働き方の詳細 ===
ALTER TABLE company_profile ADD COLUMN flex_time BOOLEAN DEFAULT FALSE;  -- フレックスタイム制
ALTER TABLE company_profile ADD COLUMN core_time VARCHAR(50);  -- コアタイム（例: "11:00-15:00"）
ALTER TABLE company_profile ADD COLUMN earliest_start_time TIME;  -- 最も早い出社時間
ALTER TABLE company_profile ADD COLUMN latest_start_time TIME;  -- 最も遅い出社時間
ALTER TABLE company_profile ADD COLUMN part_time_available BOOLEAN DEFAULT FALSE;  -- 時短勤務可
ALTER TABLE company_profile ADD COLUMN side_job_allowed BOOLEAN DEFAULT FALSE;  -- 副業可
ALTER TABLE company_profile ADD COLUMN dress_code VARCHAR(50);  -- 服装規定（自由/オフィスカジュアル/スーツ）

-- === チーム・組織 ===
ALTER TABLE company_profile ADD COLUMN team_size VARCHAR(50);  -- チームサイズ（例: "5-10名"）
ALTER TABLE company_profile ADD COLUMN average_age INTEGER;  -- 平均年齢
ALTER TABLE company_profile ADD COLUMN foreign_ratio INTEGER;  -- 外国人比率（%）
ALTER TABLE company_profile ADD COLUMN female_ratio INTEGER;  -- 女性比率（%）
ALTER TABLE company_profile ADD COLUMN development_method VARCHAR(50);  -- 開発手法（アジャイル/スクラム等）

-- === 成長・学習 ===
ALTER TABLE company_profile ADD COLUMN training_program TEXT;  -- 研修制度の詳細
ALTER TABLE company_profile ADD COLUMN study_session_frequency VARCHAR(50);  -- 勉強会頻度（週1回/月1回等）
ALTER TABLE company_profile ADD COLUMN conference_support BOOLEAN DEFAULT FALSE;  -- カンファレンス参加支援
ALTER TABLE company_profile ADD COLUMN book_purchase_budget INTEGER;  -- 書籍購入予算（月額/年額）
ALTER TABLE company_profile ADD COLUMN mentor_system BOOLEAN DEFAULT FALSE;  -- メンター制度

-- === 評価・キャリア ===
ALTER TABLE company_profile ADD COLUMN evaluation_system TEXT;  -- 評価制度の詳細
ALTER TABLE company_profile ADD COLUMN salary_review_frequency VARCHAR(50);  -- 昇給頻度（年1回/年2回等）
ALTER TABLE company_profile ADD COLUMN career_path TEXT;  -- キャリアパスの詳細
ALTER TABLE company_profile ADD COLUMN promotion_criteria TEXT;  -- 昇進基準

-- === 福利厚生の詳細 ===
ALTER TABLE company_profile ADD COLUMN remote_work_allowance INTEGER;  -- リモートワーク手当（月額）
ALTER TABLE company_profile ADD COLUMN housing_allowance INTEGER;  -- 住宅手当（月額）
ALTER TABLE company_profile ADD COLUMN commute_allowance_limit INTEGER;  -- 交通費上限（月額）
ALTER TABLE company_profile ADD COLUMN retirement_plan BOOLEAN DEFAULT FALSE;  -- 退職金制度

-- === 職場環境 ===
ALTER TABLE company_profile ADD COLUMN pc_spec TEXT;  -- PC環境（例: "MacBook Pro/Windows選択可"）
ALTER TABLE company_profile ADD COLUMN monitor_count INTEGER;  -- モニター枚数
ALTER TABLE company_profile ADD COLUMN office_facilities TEXT;  -- オフィス設備
ALTER TABLE company_profile ADD COLUMN quiet_workspace BOOLEAN DEFAULT FALSE;  -- 静かな作業環境

-- === プロジェクト詳細 ===
ALTER TABLE company_profile ADD COLUMN tech_stack JSONB;  -- 技術スタック（詳細、JSONB形式）
ALTER TABLE company_profile ADD COLUMN project_scale VARCHAR(50);  -- プロジェクト規模
ALTER TABLE company_profile ADD COLUMN team_structure TEXT;  -- チーム構成
ALTER TABLE company_profile ADD COLUMN development_process TEXT;  -- 開発プロセスの詳細
```

#### tech_stack（JSONB）の構造例

```json
{
  "languages": ["Python", "JavaScript", "TypeScript"],
  "frameworks": ["Django", "React", "Next.js"],
  "databases": ["PostgreSQL", "Redis"],
  "infrastructure": ["AWS", "Docker", "Kubernetes"],
  "tools": ["GitHub", "Jira", "Slack"],
  "version_control": "Git",
  "ci_cd": ["GitHub Actions", "CircleCI"]
}
```

### 提案2: **新規テーブル作成** ⭐⭐⭐⭐

#### 2-1. 柔軟な働き方オプションテーブル

```sql
CREATE TABLE flexible_work_options (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES company_profile(id),
    option_type VARCHAR(50) NOT NULL,  -- 'flex_time', 'late_start', 'short_hours', etc.
    option_value TEXT,  -- 具体的な内容
    description TEXT,  -- 説明
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 例:
INSERT INTO flexible_work_options (job_id, option_type, option_value, description)
VALUES 
    (1, 'flex_time', '7:00-22:00', 'この時間帯で自由に勤務可能'),
    (1, 'late_start', '10:00出社可', '満員電車を避けられます'),
    (1, 'short_hours', '6時間勤務可', '育児・介護との両立可能');
```

#### 2-2. 学習・成長機会テーブル

```sql
CREATE TABLE learning_opportunities (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES company_profile(id),
    opportunity_type VARCHAR(50) NOT NULL,  -- 'training', 'conference', 'certification', etc.
    name VARCHAR(200),
    frequency VARCHAR(50),  -- 頻度
    cost_support INTEGER,  -- 費用補助（%）
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 例:
INSERT INTO learning_opportunities (job_id, opportunity_type, name, frequency, cost_support, description)
VALUES 
    (1, 'training', '新人研修プログラム', '入社時', 100, '3ヶ月間の手厚い研修'),
    (1, 'conference', 'RubyKaigi等の技術カンファレンス', '年2回まで', 100, '交通費・宿泊費含む'),
    (1, 'book', '技術書購入', '月3冊まで', 100, '上限なし');
```

#### 2-3. 職場文化・価値観テーブル

```sql
CREATE TABLE company_culture_values (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES company_profile(id),
    value_type VARCHAR(50) NOT NULL,  -- 'flat_org', 'work_life', 'challenge', etc.
    score INTEGER CHECK (score BETWEEN 1 AND 5),  -- 重視度 1-5
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 例:
INSERT INTO company_culture_values (job_id, value_type, score, description)
VALUES 
    (1, 'flat_org', 5, '役職に関係なく意見が言える環境'),
    (1, 'work_life', 4, '残業月平均20時間、有給取得率85%'),
    (1, 'challenge', 5, '新技術の導入に積極的');
```

### 提案3: **高度なスコアリングシステム** ⭐⭐⭐⭐

#### 3-1. ベクトル類似度ベースのマッチング

ユーザーの希望と求人の特徴をベクトル化し、類似度でマッチング：

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def calculate_semantic_similarity(user_text, job_text):
    """セマンティック類似度計算"""
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([user_text, job_text])
    similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    return similarity * 100  # 0-100のスコア
```

#### 3-2. AIベースの動的スコアリング

```python
def ai_dynamic_scoring(user_intent: Dict, job: Dict) -> Dict:
    """AIで動的にスコアリング"""
    
    prompt = f"""
    ユーザーの希望: {json.dumps(user_intent, ensure_ascii=False)}
    
    求人情報: {json.dumps(job, ensure_ascii=False)}
    
    この求人がユーザーに合う度合いを0-100で評価してください。
    
    評価基準:
    1. ユーザーの pain_points を解決できるか（40点）
    2. explicit_preferences と一致するか（30点）
    3. implicit_values の優先度と一致するか（20点）
    4. alternative_condition_acceptance を考慮（10点）
    
    JSON形式で返答:
    {{
        "score": 85,
        "reasoning": "理由の説明",
        "match_points": ["マッチしたポイント1", "..."],
        "concerns": ["懸念点1", "..."]
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)
```

### 提案4: **ユーザー嗜好学習テーブル** ⭐⭐⭐

```sql
CREATE TABLE user_preference_learning (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    preference_key VARCHAR(100) NOT NULL,  -- 例: "remote_work_importance"
    preference_value FLOAT,  -- 重要度スコア（0-1）
    confidence FLOAT,  -- 信頼度（0-1）
    source VARCHAR(50),  -- 'explicit'（明示的）or 'implicit'（暗黙的）
    learned_from TEXT,  -- どの会話から学習したか
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_user_preference_learning_user 
    ON user_preference_learning(user_id, preference_key);
```

使用例：
```python
# ユーザーが「満員電車が嫌」と言った
→ "commute_stress_avoidance": 0.9 を学習

# 次回の検索で自動的に以下を考慮:
# - リモートワーク可の求人
# - フレックスタイムで10時出社可の求人
# - 職住近接（通勤30分以内）の求人
```

---

## 📊 優先順位と実装ロードマップ

### Phase 1: 緊急対応（1-2週間）⭐⭐⭐⭐⭐
1. **company_profile テーブルに最低限のカラム追加**
   - `flex_time`, `earliest_start_time`, `latest_start_time`
   - `side_job_allowed`, `dress_code`
   - `tech_stack` (JSONB)
   - `training_program`, `mentor_system`

2. **ダミーデータの拡充**
   - 新規カラムにリアルなデータを投入

### Phase 2: 中期対応（3-4週間）⭐⭐⭐⭐
1. **新規テーブルの作成と実装**
   - `flexible_work_options`
   - `learning_opportunities`
   - `company_culture_values`

2. **スコアリングロジックの改善**
   - 固定値から動的計算へ変更
   - 代替案を考慮したスコアリング

### Phase 3: 長期対応（5-8週間）⭐⭐⭐
1. **AIベースの高度なマッチング**
   - ベクトル類似度ベースのマッチング
   - GPTによる動的スコアリング

2. **ユーザー嗜好学習システム**
   - 過去の会話から学習
   - パーソナライズされた推薦

---

## 🎯 まとめ

### 現状の回答

**Q: 現状のコードで、ユーザーの自由な回答に適した求人を提示できる？**

**A: 部分的にはできますが、大きな制限があります。**

#### できること ✅
- ユーザーの自由な回答から意図を抽出
- 基本的な条件（リモートワーク、学習興味）でスコアリング
- 動的に質問を生成

#### できないこと ❌
- **複雑な働き方の要望に対応**（フレックス、時短、副業可否等）
- **代替案の提示後のマッチング**（DBに情報がない）
- **細かい職場環境の要望に対応**（チーム規模、平均年齢等）
- **学習・成長機会の詳細なマッチング**
- **ユーザーの優先順位を反映した柔軟なスコアリング**

### 必要な対応

**Q: もっと他に必要な情報がある？（DB、カラム増やす必要がある？）**

**A: はい、必須です。最低限、Phase 1の対応が必要です。**

最優先事項：
1. ✅ **働き方の柔軟性に関するカラム追加**（フレックス、出社時間等）
2. ✅ **技術スタックの詳細（JSONB形式）**
3. ✅ **学習・成長機会の情報**
4. ✅ **チーム・組織の詳細情報**

これらがないと、ユーザーの自由な回答に対して**満足のいく求人推薦ができません**。
