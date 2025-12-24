# 柔軟な求人情報管理システム - 提案書

## 🎯 問題の本質

おっしゃる通りです！**項目を固定化すると、以下の問題が発生します**：

1. **項目の追加が必要になる度にDBスキーマ変更**
   - ユーザー: 「ペット同伴出勤できる会社がいい」
   - システム: 「pet_allowed カラムがありません...」→ ALTER TABLE 必要

2. **予測不可能なニーズ**
   - 今後出てくる新しい働き方（週3日勤務、ワーケーション等）
   - 時代とともに変化する価値観（SDGs、DE&I等）

3. **企業側の入力負担**
   - 100個の項目を全て埋めるのは現実的ではない
   - 項目が増える度に再入力が必要

---

## 💡 解決策: **ハイブリッドアプローチ**

### 基本コンセプト

```
【構造化データ】最低限の必須項目（20-30項目）
    +
【非構造化データ】自由記述フィールド（複数）
    +
【AIによる情報抽出・マッチング】
```

これにより：
- ✅ 基本的な検索・フィルタリングは構造化データで高速処理
- ✅ 柔軟な要望はAIが非構造化データから情報を抽出
- ✅ 新しいニーズが出てもDBスキーマ変更不要
- ✅ 企業側の入力負担も軽減

---

## 📋 提案システム構成

### 1. **3層構造のデータモデル**

#### Layer 1: 必須構造化データ（検索・フィルタリング用）

これらは**必ず項目化が必要**：

```sql
-- 基本情報（絶対に必要）
job_title VARCHAR(100) NOT NULL,
location_prefecture VARCHAR(50) NOT NULL,
salary_min INTEGER NOT NULL,
salary_max INTEGER NOT NULL,
employment_type VARCHAR(50),

-- 働き方（最重要・高頻度）
remote_option VARCHAR(50),  -- 完全リモート/ハイブリッド/なし
flex_time BOOLEAN,
earliest_start_time TIME,
latest_start_time TIME,
side_job_allowed BOOLEAN,

-- 技術スタック（エンジニア求人では必須）
tech_stack JSONB,  -- 柔軟性のためJSONB

-- 成長機会（高頻度）
training_program BOOLEAN,
mentor_system BOOLEAN,
conference_support BOOLEAN,

-- 基本的な福利厚生
remote_work_allowance INTEGER,
housing_allowance INTEGER
```

**理由**: これらは**ユーザーが最もよく聞く条件**で、高速な検索が必要

#### Layer 2: 構造化された自由記述フィールド（カテゴリ別）

```sql
CREATE TABLE company_profile (
    -- ... Layer 1の項目 ...
    
    -- Layer 2: カテゴリ別自由記述（TEXT/JSONB）
    work_style_details TEXT,           -- 働き方の詳細
    team_culture_details TEXT,         -- チーム・文化の詳細
    growth_opportunities_details TEXT, -- 成長機会の詳細
    benefits_details TEXT,             -- 福利厚生の詳細
    office_environment_details TEXT,   -- オフィス環境の詳細
    project_details TEXT,              -- プロジェクトの詳細
    
    -- Layer 3: 完全自由記述
    company_appeal_text TEXT,          -- 企業からの自由アピール
    free_description TEXT,             -- その他自由記述
    
    -- AI抽出用キャッシュ（後述）
    ai_extracted_features JSONB        -- AIが抽出した特徴
);
```

#### Layer 3: ベクトル検索用の埋め込み（Embedding）

```sql
-- ベクトル検索テーブル（pgvector拡張使用）
CREATE TABLE job_embeddings (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES company_profile(id),
    embedding_type VARCHAR(50),  -- 'full_description', 'work_style', etc.
    embedding vector(1536),      -- OpenAI embedding (1536次元)
    source_text TEXT,             -- 元のテキスト
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ベクトル検索用インデックス
CREATE INDEX ON job_embeddings USING ivfflat (embedding vector_cosine_ops);
```

---

## 🔧 具体的な実装方法

### 方法1: 企業側の入力フォーム設計

#### 入力画面の構成

```
┌─────────────────────────────────────────────┐
│ 求人情報登録                                │
├─────────────────────────────────────────────┤
│ 【必須項目】（20項目程度）                  │
│ ✓ 職種名: [_______________]                │
│ ✓ 勤務地: [都道府県▼] [市区町村______]    │
│ ✓ 年収: [最低____] - [最高____] 万円      │
│ ✓ リモート: [完全可▼ ハイブリッド なし]   │
│ ✓ フレックス: [あり ☑️  なし ☐]          │
│ ...                                         │
├─────────────────────────────────────────────┤
│ 【詳細情報】（カテゴリ別自由記述）          │
│                                             │
│ 📝 働き方について（500文字以内）            │
│ ┌─────────────────────────────────────┐   │
│ │ 例: フレックス制で7:00-22:00の間で  │   │
│ │ 自由に勤務可能。10時出社も可。      │   │
│ │ リモートワークは週3日まで。         │   │
│ └─────────────────────────────────────┘   │
│                                             │
│ 📝 チーム・文化について（500文字以内）      │
│ ┌─────────────────────────────────────┐   │
│ │ 5-7名のスクラムチーム。平均年齢32歳 │   │
│ │ フラットな組織で意見が言いやすい。  │   │
│ └─────────────────────────────────────┘   │
│                                             │
│ 📝 成長機会について（500文字以内）          │
│ 📝 福利厚生について（500文字以内）          │
│ 📝 オフィス環境について（500文字以内）      │
│ 📝 プロジェクトについて（500文字以内）      │
│                                             │
├─────────────────────────────────────────────┤
│ 【自由アピール】（1000文字以内）            │
│ ┌─────────────────────────────────────┐   │
│ │ 当社の特徴や魅力を自由にアピール    │   │
│ │ してください                        │   │
│ └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

#### メリット
- ✅ 必須項目は構造化されており検索可能
- ✅ 詳細はカテゴリ別に整理されて読みやすい
- ✅ 企業側の入力負担が軽い
- ✅ 新しい要望に柔軟に対応可能

---

### 方法2: AI活用の2段階マッチング

#### ステップ1: 初期フィルタリング（構造化データ）

```python
def initial_filtering(user_profile: Dict) -> List[Dict]:
    """Layer 1の構造化データで高速フィルタリング"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 基本条件で絞り込み
    cur.execute("""
        SELECT *
        FROM company_profile
        WHERE job_title ILIKE %s
          AND location_prefecture = %s
          AND salary_min >= %s
          AND (
              -- リモートワーク条件
              (remote_option = '完全リモート可' AND %s = '強く希望')
              OR 
              (remote_option IN ('完全リモート可', 'ハイブリッド') AND %s = '希望')
              OR
              %s = '不問'
          )
        ORDER BY created_at DESC
        LIMIT 100  -- 100件に絞る
    """, (
        f'%{user_profile["job_title"]}%',
        user_profile['location'],
        user_profile['salary_min'],
        user_profile['remote_preference'],
        user_profile['remote_preference'],
        user_profile['remote_preference']
    ))
    
    return cur.fetchall()
```

#### ステップ2: AIによる詳細マッチング（非構造化データ）

```python
def ai_detailed_matching(
    user_intent: Dict,
    candidates: List[Dict]
) -> List[Dict]:
    """AIでLayer 2/3のテキストから詳細マッチング"""
    
    for job in candidates:
        # 求人の全テキストを結合
        job_full_text = f"""
        職種: {job['job_title']}
        働き方: {job.get('work_style_details', '')}
        チーム・文化: {job.get('team_culture_details', '')}
        成長機会: {job.get('growth_opportunities_details', '')}
        福利厚生: {job.get('benefits_details', '')}
        オフィス環境: {job.get('office_environment_details', '')}
        プロジェクト: {job.get('project_details', '')}
        自由アピール: {job.get('company_appeal_text', '')}
        """
        
        # AIでマッチング
        score = calculate_ai_match_score(user_intent, job_full_text)
        job['ai_match_score'] = score
    
    # AIスコアでソート
    candidates.sort(key=lambda x: x['ai_match_score'], reverse=True)
    return candidates


def calculate_ai_match_score(user_intent: Dict, job_text: str) -> float:
    """AIでマッチングスコアを計算"""
    
    prompt = f"""
    【ユーザーの希望】
    {json.dumps(user_intent, ensure_ascii=False, indent=2)}
    
    【求人情報】
    {job_text}
    
    このユーザーと求人のマッチ度を0-100で評価してください。
    
    特に以下を重視:
    1. ユーザーのpain_points（不満点）が解決されるか
    2. 代替案への受容（alternative_condition_acceptance）を考慮
    3. 暗黙の優先度（implicit_values）との一致
    
    例:
    - ユーザー: 「満員電車が嫌」
    - 求人に「10時出社可」があれば高評価
    - 求人に「リモート週3日可」があれば高評価
    
    JSON形式で返答:
    {{
        "score": 85,
        "reasoning": "10時出社可能でユーザーの満員電車回避ニーズに合致",
        "matched_features": ["10時出社可", "フレックスタイム"],
        "concerns": ["完全リモートではない"]
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",  # より高精度なモデル
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3
    )
    
    result = json.loads(response.choices[0].message.content)
    return result['score']
```

---

### 方法3: ベクトル検索による類似マッチング

#### 実装例（pgvector使用）

```python
from openai import OpenAI

def semantic_search_jobs(user_query: str, top_k: int = 20) -> List[Dict]:
    """ユーザーの自由記述をベクトル化して類似求人を検索"""
    
    # ユーザーの要望をベクトル化
    client = OpenAI()
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=user_query
    )
    query_embedding = response.data[0].embedding
    
    # PostgreSQLでベクトル類似検索
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # pgvectorで類似度検索
    cur.execute("""
        SELECT 
            cp.*,
            je.embedding <=> %s::vector AS distance,
            1 - (je.embedding <=> %s::vector) AS similarity
        FROM job_embeddings je
        JOIN company_profile cp ON je.job_id = cp.id
        WHERE je.embedding_type = 'full_description'
        ORDER BY je.embedding <=> %s::vector
        LIMIT %s
    """, (query_embedding, query_embedding, query_embedding, top_k))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return [dict(r) for r in results]


# 使用例
user_query = """
満員電車を避けられて、Pythonで機械学習の実務経験を積める環境がいい。
フラットな組織で、若いメンバーと働きたい。
年収は500万円以上希望。
"""

matches = semantic_search_jobs(user_query, top_k=20)
# → AIが自動的に「10時出社可」「リモート可」「ML案件あり」等の
#    求人を類似度でランキング
```

---

### 方法4: AI特徴抽出とキャッシング

企業が入力した自由記述から、AIで特徴を事前抽出してキャッシュ：

```python
def extract_and_cache_features(job_id: int):
    """求人のテキストからAIで特徴を抽出してキャッシュ"""
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 求人情報を取得
    cur.execute("SELECT * FROM company_profile WHERE id = %s", (job_id,))
    job = cur.fetchone()
    
    # 全テキストを結合
    full_text = f"""
    {job.get('work_style_details', '')}
    {job.get('team_culture_details', '')}
    {job.get('growth_opportunities_details', '')}
    {job.get('benefits_details', '')}
    {job.get('office_environment_details', '')}
    {job.get('project_details', '')}
    {job.get('company_appeal_text', '')}
    """
    
    # AIで特徴抽出
    prompt = f"""
    以下の求人情報から、構造化された特徴を抽出してJSON形式で返してください。
    
    【求人情報】
    {full_text}
    
    以下のような特徴を抽出:
    {{
        "work_flexibility": {{
            "late_start_available": true/false,
            "latest_start_time": "10:00",
            "work_from_anywhere": true/false,
            "pet_friendly": true/false,
            "workation_available": true/false
        }},
        "team_characteristics": {{
            "team_size": "5-7名",
            "average_age": 32,
            "flat_organization": true/false,
            "international": true/false
        }},
        "growth_support": {{
            "training_programs": ["新人研修", "技術研修"],
            "conference_support": true/false,
            "book_budget": 10000,
            "learning_time": "週1時間の学習時間"
        }},
        "unique_benefits": [
            "ペット同伴出勤可",
            "ワーケーション制度",
            "サウナ・ジム使い放題"
        ],
        "keywords": ["フラット", "若手", "機械学習", "AWS"]
    }}
    
    ※ 明記されていない項目はnullにしてください
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    
    features = json.loads(response.choices[0].message.content)
    
    # キャッシュとして保存
    cur.execute("""
        UPDATE company_profile
        SET ai_extracted_features = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (json.dumps(features), job_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return features


# マッチング時にキャッシュを利用
def fast_ai_matching_with_cache(user_intent: Dict, job: Dict) -> float:
    """キャッシュされた特徴を使って高速マッチング"""
    
    cached_features = job.get('ai_extracted_features', {})
    
    score = 50  # 基本スコア
    
    # ユーザーが「満員電車を避けたい」
    if 'commute_stress' in user_intent.get('pain_points', []):
        if cached_features.get('work_flexibility', {}).get('late_start_available'):
            score += 20
        if job.get('remote_option') == '完全リモート可':
            score += 30
    
    # ユーザーが「ペット同伴で働きたい」（新しいニーズ！）
    if 'pet_friendly' in user_intent.get('keywords', []):
        if 'ペット同伴出勤可' in cached_features.get('unique_benefits', []):
            score += 25
    
    return min(score, 100)
```

---

## 🗄️ 推奨DB設計（ハイブリッド方式）

### 最終的なテーブル設計

```sql
CREATE TABLE company_profile (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    
    -- ========================================
    -- Layer 1: 必須構造化データ（20-30項目）
    -- ========================================
    job_title VARCHAR(100) NOT NULL,
    location_prefecture VARCHAR(50) NOT NULL,
    location_city VARCHAR(100),
    salary_min INTEGER NOT NULL,
    salary_max INTEGER NOT NULL,
    employment_type VARCHAR(50),
    
    -- 働き方（必須項目のみ）
    remote_option VARCHAR(50),  -- 完全/ハイブリッド/なし
    flex_time BOOLEAN DEFAULT FALSE,
    earliest_start_time TIME,
    latest_start_time TIME,
    side_job_allowed BOOLEAN DEFAULT FALSE,
    
    -- 技術スタック（JSONB）
    tech_stack JSONB,
    
    -- 成長機会（必須項目のみ）
    training_program BOOLEAN DEFAULT FALSE,
    mentor_system BOOLEAN DEFAULT FALSE,
    conference_support BOOLEAN DEFAULT FALSE,
    
    -- 福利厚生（必須項目のみ）
    remote_work_allowance INTEGER DEFAULT 0,
    housing_allowance INTEGER DEFAULT 0,
    
    -- ========================================
    -- Layer 2: カテゴリ別自由記述
    -- ========================================
    work_style_details TEXT,
    team_culture_details TEXT,
    growth_opportunities_details TEXT,
    benefits_details TEXT,
    office_environment_details TEXT,
    project_details TEXT,
    
    -- ========================================
    -- Layer 3: 完全自由記述
    -- ========================================
    company_appeal_text TEXT,
    free_description TEXT,
    
    -- ========================================
    -- AI処理結果（キャッシュ）
    -- ========================================
    ai_extracted_features JSONB,  -- AIが抽出した特徴
    last_ai_extraction_at TIMESTAMP,  -- 最終AI処理日時
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ベクトル検索テーブル（pgvector拡張）
CREATE TABLE job_embeddings (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES company_profile(id),
    embedding_type VARCHAR(50),
    embedding vector(1536),
    source_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_company_profile_basic ON company_profile(job_title, location_prefecture, salary_min);
CREATE INDEX idx_company_profile_remote ON company_profile(remote_option);
CREATE INDEX idx_company_profile_flex ON company_profile(flex_time) WHERE flex_time = TRUE;
CREATE INDEX idx_company_profile_tech_stack ON company_profile USING GIN(tech_stack);
CREATE INDEX idx_company_profile_ai_features ON company_profile USING GIN(ai_extracted_features);
CREATE INDEX idx_job_embeddings_vector ON job_embeddings USING ivfflat(embedding vector_cosine_ops);
```

---

## 🚀 実装ロードマップ

### Phase 1: ハイブリッド基盤構築（2-3週間）

1. **DB設計変更**
   - Layer 1の必須項目（20-30個）
   - Layer 2のカテゴリ別自由記述フィールド
   - ai_extracted_features カラム追加

2. **企業入力フォーム改修**
   - 必須項目 + カテゴリ別自由記述
   - 入力ガイダンス・例文を充実

3. **基本マッチング実装**
   - Layer 1での高速フィルタリング
   - Layer 2でのテキストマッチング

### Phase 2: AI機能強化（3-4週間）

1. **AI特徴抽出機能**
   - 自由記述から特徴を抽出
   - ai_extracted_features にキャッシュ

2. **AIスコアリング改善**
   - キャッシュされた特徴を活用
   - ユーザーの複雑な要望に対応

### Phase 3: ベクトル検索導入（4-6週間）

1. **pgvector拡張のセットアップ**
2. **Embedding生成パイプライン**
3. **セマンティック検索機能**

---

## 📊 比較: 固定項目 vs ハイブリッド

| 項目 | 固定項目方式 | ハイブリッド方式 |
|------|-------------|-----------------|
| **スキーマ変更頻度** | 高い（新ニーズの度に変更） | 低い（ほぼ不要） |
| **企業入力負担** | 高い（100項目以上） | 中程度（必須20-30 + 自由記述） |
| **検索速度** | 非常に速い | 速い（Layer 1）+ 柔軟（Layer 2/3） |
| **柔軟性** | 低い | 非常に高い |
| **新ニーズ対応** | スキーマ変更必要 | すぐに対応可能 |
| **AIコスト** | 不要 | 中程度（キャッシュで軽減） |

---

## 💡 結論

### 推奨アプローチ

**ハイブリッド方式（Layer 1 + Layer 2 + AI）**

#### 理由

1. ✅ **スケーラビリティ**: 新しいニーズに柔軟に対応
2. ✅ **現実的な運用**: 企業の入力負担が適切
3. ✅ **高速検索**: Layer 1で初期フィルタリング
4. ✅ **高精度マッチング**: AIがLayer 2/3から詳細抽出
5. ✅ **将来性**: ベクトル検索で更に高度化可能

#### 具体的には

```
1. 必須項目は20-30個に厳選（最頻出の条件のみ）
   → 高速検索に使用

2. カテゴリ別自由記述（6-8カテゴリ）
   → 企業が柔軟に記載、AIが処理

3. 完全自由記述フィールド
   → 予測不可能なアピールポイント

4. AIで特徴抽出 + キャッシュ
   → リアルタイムAI処理を削減

5. 将来的にベクトル検索導入
   → セマンティック検索で精度向上
```

この方式なら、**「ペット同伴出勤」「ワーケーション制度」など、予測不可能な新しいニーズにもDB変更なしで即座に対応できます**。
