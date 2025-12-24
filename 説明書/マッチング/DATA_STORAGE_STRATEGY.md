# 🔄 進化型AIシステム - データ保存戦略完全ガイド

---

## 📋 目次

1. [保存されるデータの全体像](#1-保存されるデータの全体像)
2. [ハイブリッド型データベース設計](#2-ハイブリッド型データベース設計)
3. [柔軟性と構造化のバランス](#3-柔軟性と構造化のバランス)
4. [実装例](#4-実装例)

---

# 1. 保存されるデータの全体像

## 1-1. ユーザー行動履歴として保存されるもの

```
┌─────────────────────────────────────────────────────┐
│        ユーザー行動データ（5つのカテゴリ）            │
└─────────────────────────────────────────────────────┘

【1. 基本的な行動履歴】
├─ クリック（求人カードをクリック）
├─ 閲覧（求人詳細ページを見た）
├─ お気に入り（求人を保存）
├─ 応募（求人に応募）
└─ 検索（条件で絞り込み）

【2. チャット会話履歴】
├─ ユーザーの発言（全テキスト）
├─ AIの質問（全テキスト）
├─ 発言のタイムスタンプ
├─ 会話のセッションID
└─ 会話のトピック

【3. 抽出された構造化情報】
├─ 明示的な希望条件
│  ├─ 希望職種
│  ├─ 希望勤務地
│  ├─ 希望年収
│  └─ リモートワーク希望
│
├─ 暗黙的な価値観
│  ├─ ワークライフバランス重視度
│  ├─ キャリア成長重視度
│  ├─ 安定性 vs 挑戦
│  └─ チーム志向 vs 個人志向
│
└─ 感情・態度
   ├─ ポジティブ/ネガティブ
   ├─ 確信度（自信がある/迷っている）
   └─ 緊急度（すぐ転職/じっくり探す）

【4. エンベディングベクトル】
├─ 会話全体のエンベディング（1536次元）
├─ 各発言のエンベディング
└─ 時系列でのエンベディング変化

【5. メタデータ】
├─ セッション時間
├─ 応答速度
├─ 質問への回答率
├─ 会話の深さレベル
└─ 離脱ポイント
```

---

## 1-2. 具体例：1人のユーザーの1回のセッション

```
【ユーザーID: 5001, セッション: session_abc123】

=== 基本的な行動履歴 ===
2025-12-22 14:30:00 | click    | job_001
2025-12-22 14:30:15 | view     | job_001
2025-12-22 14:31:00 | favorite | job_001
2025-12-22 14:35:00 | click    | job_002
2025-12-22 14:35:20 | view     | job_002

=== チャット会話履歴 ===
[14:30:30] AI: 「リモートワークに興味はありますか？」
[14:30:45] User: 「はい、週3日以上希望します」
[14:31:00] AI: 「リモートワークを希望する理由を教えてください」
[14:31:30] User: 「通勤時間が片道1.5時間で、家族との時間と勉強に使いたいです」
[14:32:00] AI: 「何を勉強したいと考えていますか？」
[14:32:20] User: 「Reactです。将来フロントエンドスペシャリストになりたいからです」

=== 抽出された構造化情報 ===
{
  "explicit_preferences": {
    "remote_work": "週3日以上",
    "commute_time_current": "片道1.5時間",
    "learning_interest": "React",
    "career_goal": "フロントエンドスペシャリスト"
  },
  
  "implicit_values": {
    "work_life_balance_priority": 4,  // 5段階で4
    "career_growth_priority": 5,      // 5段階で5
    "family_priority": 5,              // 「家族との時間」から推定
    "learning_motivation": "high"      // 「勉強したい」から推定
  },
  
  "emotional_state": {
    "sentiment": "positive",           // 前向き
    "confidence": "high",              // 「〜したい」と明確
    "urgency": "medium"                // 急いでいない様子
  },
  
  "behavioral_pattern": {
    "response_time_avg": 25,           // 平均25秒で回答
    "response_length_avg": 45,         // 平均45文字
    "engagement_level": "high"         // よく話してくれる
  }
}

=== エンベディングベクトル ===
conversation_embedding: [0.123, -0.456, 0.789, ...] (1536次元)

=== メタデータ ===
session_duration: 5分30秒
total_exchanges: 3往復
conversation_depth: 3 (深掘り質問まで到達)
completion_status: "in_progress"
```

---

# 2. ハイブリッド型データベース設計

## 2-1. なぜハイブリッド型なのか？

```
❌ 完全固定カラム型の問題:
- 新しい質問に対応できない
- ユーザーの多様な回答を保存できない
- 柔軟性がない

❌ 完全フリーフォーム型の問題:
- クエリが遅い
- 集計・分析が困難
- インデックスが効かない

✅ ハイブリッド型の利点:
- よく使う情報は固定カラム（高速）
- 柔軟な情報はJSON/テキスト（拡張性）
- エンベディングで意味検索（AI活用）
```

---

## 2-2. テーブル設計（完全版）

### A. 構造化データテーブル（固定カラム）

```sql
-- ============================================
-- user_profile テーブル（基本情報）
-- ============================================
CREATE TABLE user_profile (
    user_id INTEGER PRIMARY KEY,
    
    -- 基本希望条件（固定カラム - よく使うので高速化）
    job_title VARCHAR(100),              -- 希望職種
    location_prefecture VARCHAR(50),     -- 希望勤務地
    salary_min INTEGER,                  -- 希望最低年収
    
    -- 優先度（1-5スケール - 集計しやすい）
    work_life_balance_priority INTEGER DEFAULT 3,
    salary_priority INTEGER DEFAULT 3,
    career_growth_priority INTEGER DEFAULT 3,
    stability_priority INTEGER DEFAULT 3,
    
    -- ユーザー特性（カテゴリカル - フィルタリング高速）
    decision_style VARCHAR(50),          -- 'quick', 'cautious', 'analytical'
    career_stage VARCHAR(50),            -- 'junior', 'mid', 'senior'
    
    -- エンベディング（ベクトル検索）
    conversation_embedding VECTOR(1536), -- pgvector型
    
    -- メタデータ
    profile_completeness INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- インデックス（高速検索用）
CREATE INDEX idx_user_profile_job ON user_profile(job_title);
CREATE INDEX idx_user_profile_location ON user_profile(location_prefecture);
CREATE INDEX idx_user_profile_salary ON user_profile(salary_min);
CREATE INDEX idx_user_profile_embedding ON user_profile 
    USING ivfflat (conversation_embedding vector_cosine_ops);
```

---

### B. 柔軟な非構造化データテーブル（JSONB）

```sql
-- ============================================
-- user_dynamic_profile テーブル（柔軟な情報）
-- ============================================
CREATE TABLE user_dynamic_profile (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user_profile(user_id),
    
    -- 🌟 キーポイント：JSONBで柔軟に保存
    profile_data JSONB NOT NULL,
    
    -- メタデータ
    data_version INTEGER DEFAULT 1,  -- データ構造のバージョン
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 制約：1ユーザー1レコード
    UNIQUE(user_id)
);

-- JSONB用のインデックス（重要！）
CREATE INDEX idx_dynamic_profile_data ON user_dynamic_profile USING GIN (profile_data);

-- 特定のJSONキーへのインデックス（さらに高速化）
CREATE INDEX idx_dynamic_profile_career_goal 
    ON user_dynamic_profile ((profile_data->>'career_goal'));
CREATE INDEX idx_dynamic_profile_learning_interests 
    ON user_dynamic_profile ((profile_data->'learning_interests'));
```

**JSONBに保存するデータの例：**

```json
{
  "career_goal": "3年後はテックリードになりたい",
  "learning_interests": ["React", "TypeScript", "AWS"],
  "current_skills": ["HTML", "CSS", "JavaScript", "Python"],
  "years_experience": 5,
  
  "pain_points": [
    "前職は残業が多かった",
    "技術的な挑戦が少なかった",
    "キャリアパスが不明確だった"
  ],
  
  "enjoyed_aspects": [
    "チームワークが良かった",
    "自社サービスを作れた"
  ],
  
  "work_style_preferences": {
    "team_size": "5-10人が理想",
    "meeting_frequency": "週2-3回が適切",
    "communication_style": "Slack中心、対面は週1回"
  },
  
  "company_preferences": {
    "size": "50-300人のミドルベンチャー",
    "culture": "フラットな組織、技術重視",
    "industry": ["Web", "SaaS", "AI"]
  },
  
  "avoiding": {
    "industries": ["金融", "受託"],
    "company_types": ["大企業の子会社"],
    "work_environments": ["長時間労働が当たり前"]
  },
  
  "custom_fields": {
    "favorite_tech_blog": "Qiita",
    "conference_attendance": "年2-3回",
    "side_projects": "個人でReactアプリ開発中"
  }
}
```

---

### C. チャット会話履歴テーブル（完全テキスト）

```sql
-- ============================================
-- chat_history テーブル（会話の生ログ）
-- ============================================
CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user_profile(user_id),
    session_id VARCHAR(255) NOT NULL,
    
    -- 会話の発言者と内容
    sender VARCHAR(50) NOT NULL,  -- 'user' or 'bot'
    message TEXT NOT NULL,        -- 🌟 完全なテキスト保存
    
    -- タイムスタンプ
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chat_history_user_session 
    ON chat_history(user_id, session_id);
CREATE INDEX idx_chat_history_created 
    ON chat_history(created_at DESC);

-- 全文検索用インデックス（PostgreSQL）
CREATE INDEX idx_chat_message_fulltext 
    ON chat_history USING GIN (to_tsvector('japanese', message));
```

---

### D. 抽出済み情報テーブル（AIが構造化）

```sql
-- ============================================
-- extracted_insights テーブル
-- AIが会話から抽出した構造化情報
-- ============================================
CREATE TABLE extracted_insights (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user_profile(user_id),
    session_id VARCHAR(255),
    
    -- 抽出元の情報
    source_message_id INTEGER REFERENCES chat_history(id),
    extraction_timestamp TIMESTAMP DEFAULT NOW(),
    
    -- 抽出された情報（JSONB）
    insights JSONB NOT NULL,
    
    -- 信頼度スコア（AIの確信度）
    confidence_score DECIMAL(3,2),  -- 0.00 - 1.00
    
    -- どのAIモデルが抽出したか
    extracted_by VARCHAR(50) DEFAULT 'gpt-4',
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_extracted_insights_user 
    ON extracted_insights(user_id);
CREATE INDEX idx_extracted_insights_data 
    ON extracted_insights USING GIN (insights);
```

**抽出済み情報の例：**

```json
{
  "extraction_type": "career_preference",
  "extracted_at": "2025-12-22T14:32:20Z",
  
  "raw_message": "Reactです。将来フロントエンドスペシャリストになりたいからです",
  
  "structured_data": {
    "learning_interest": "React",
    "career_goal": "フロントエンドスペシャリスト",
    "motivation": "career_advancement",
    "urgency": "long_term"
  },
  
  "inferred_values": {
    "career_growth_priority": 5,
    "learning_motivation": "high",
    "technical_focus": true
  },
  
  "keywords": ["React", "フロントエンド", "スペシャリスト", "勉強"],
  
  "sentiment": {
    "polarity": "positive",
    "confidence": 0.92
  }
}
```

---

### E. エンベディング履歴テーブル（時系列）

```sql
-- ============================================
-- user_embedding_history テーブル
-- ユーザーの興味・希望の変化を追跡
-- ============================================
CREATE TABLE user_embedding_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user_profile(user_id),
    session_id VARCHAR(255),
    
    -- エンベディングベクトル
    embedding VECTOR(1536) NOT NULL,
    
    -- 何に基づくエンベディングか
    source_type VARCHAR(50),  -- 'conversation', 'behavior', 'hybrid'
    source_text TEXT,         -- エンベディング元のテキスト
    
    -- タイムスタンプ
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_embedding_history_user 
    ON user_embedding_history(user_id, created_at DESC);
CREATE INDEX idx_embedding_history_vector 
    ON user_embedding_history USING ivfflat (embedding vector_cosine_ops);
```

---

## 2-3. データフロー図

```
┌─────────────────────────────────────────────┐
│    ユーザーがメッセージを送信                 │
│    「通勤1.5時間。家族時間とReact勉強に使いたい」│
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ STEP 1: 生ログ保存（完全テキスト）             │
│                                              │
│ INSERT INTO chat_history (                   │
│   user_id, session_id, sender, message       │
│ ) VALUES (                                   │
│   5001, 'session_abc', 'user',               │
│   '通勤1.5時間。家族時間とReact勉強に...'      │
│ )                                            │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ STEP 2: AI分析（OpenAI APIで情報抽出）        │
│                                              │
│ response = openai.chat.completions.create(   │
│   model="gpt-4",                             │
│   messages=[{                                │
│     "role": "system",                        │
│     "content": "以下の情報を抽出:\           │
│                 1. 明示的な希望条件\         │
│                 2. 暗黙の価値観\            │
│                 3. 感情・態度"              │
│   }, {                                       │
│     "role": "user",                          │
│     "content": "通勤1.5時間。家族..."        │
│   }]                                         │
│ )                                            │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ STEP 3: 抽出された情報を保存                  │
│                                              │
│ A) 構造化情報（extracted_insights）          │
│ {                                            │
│   "commute_time": "片道1.5時間",            │
│   "pain_point": "通勤時間が長い",           │
│   "learning_interest": "React",             │
│   "priority": "家族時間",                   │
│   "career_goal": "フロントエンド勉強"        │
│ }                                            │
│                                              │
│ B) 固定カラム更新（user_profile）            │
│ UPDATE user_profile SET                      │
│   work_life_balance_priority = 5,           │
│   career_growth_priority = 5                │
│ WHERE user_id = 5001                         │
│                                              │
│ C) 柔軟データ更新（user_dynamic_profile）     │
│ UPDATE user_dynamic_profile SET              │
│   profile_data = jsonb_set(                  │
│     profile_data,                            │
│     '{learning_interests}',                  │
│     '["React"]'                              │
│   )                                          │
│ WHERE user_id = 5001                         │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ STEP 4: エンベディング生成＆保存              │
│                                              │
│ embedding = openai.embeddings.create(        │
│   model="text-embedding-3-small",            │
│   input="通勤1.5時間。家族時間とReact勉強..."  │
│ )                                            │
│                                              │
│ INSERT INTO user_embedding_history (         │
│   user_id, embedding, source_text            │
│ ) VALUES (                                   │
│   5001, embedding, "通勤1.5時間..."          │
│ )                                            │
│                                              │
│ UPDATE user_profile SET                      │
│   conversation_embedding = embedding         │
│ WHERE user_id = 5001                         │
└─────────────────────────────────────────────┘
```

---

# 3. 柔軟性と構造化のバランス

## 3-1. 設計哲学

```
┌──────────────────────────────────────┐
│   80/20ルール                         │
└──────────────────────────────────────┘

【80%のケース】固定カラムで対応
- job_title
- location_prefecture
- salary_min
- work_life_balance_priority
- career_growth_priority

→ インデックスが効く、クエリ高速、集計簡単

【20%のケース】JSONBで対応
- 予想外の質問
- ユーザー独自の価値観
- 新しいカテゴリ

→ 柔軟性、拡張性

【すべてのケース】テキスト+エンベディングで対応
- 完全な会話履歴を保存
- エンベディングで意味検索
- AIが必要に応じて再解析
```

---

## 3-2. クエリ例：3つのアプローチ

### アプローチ1: 固定カラム（高速）

```sql
-- 「リモートワーク重視」のユーザーを検索
SELECT user_id, job_title, location_prefecture
FROM user_profile
WHERE work_life_balance_priority >= 4  -- 固定カラム
  AND salary_min >= 500
ORDER BY work_life_balance_priority DESC
LIMIT 10;

-- 実行時間: 10ms（インデックス使用）
```

---

### アプローチ2: JSONB（柔軟）

```sql
-- 「Reactを学びたい」ユーザーを検索
SELECT 
    up.user_id,
    up.job_title,
    udp.profile_data->'learning_interests' as interests
FROM user_profile up
JOIN user_dynamic_profile udp ON up.user_id = udp.user_id
WHERE udp.profile_data->'learning_interests' ? 'React'  -- JSONB検索
  AND udp.profile_data->>'career_goal' LIKE '%フロントエンド%'
LIMIT 10;

-- 実行時間: 50ms（GINインデックス使用）
```

---

### アプローチ3: エンベディング（意味検索）

```sql
-- 「ワークライフバランスを重視し、技術的成長も求める」ユーザーを検索
-- （固定カラムにない複雑な条件）

WITH query_embedding AS (
    -- クエリのエンベディングを取得（事前にPythonで生成）
    SELECT '[0.123, -0.456, ...]'::vector as embedding
)
SELECT 
    up.user_id,
    up.job_title,
    1 - (up.conversation_embedding <=> qe.embedding) as similarity
FROM user_profile up, query_embedding qe
WHERE up.conversation_embedding IS NOT NULL
ORDER BY up.conversation_embedding <=> qe.embedding
LIMIT 10;

-- 実行時間: 100ms（ベクトルインデックス使用）
```

---

## 3-3. 新しい質問への対応フロー

```
【シナリオ】
新しく「副業の可否」について聞くことにした

従来の固定カラム型:
❌ ALTER TABLE で新カラム追加が必要
❌ 既存データはNULL
❌ マイグレーションが必要

ハイブリッド型:
✅ 何もしなくてOK！

フロー:
1. AIが「副業について希望はありますか？」と質問
2. ユーザー「副業もやりたいです」と回答
3. chat_history に保存（完全テキスト）
4. AIが情報抽出:
   {
     "side_job_preference": "希望する",
     "side_job_motivation": "収入増、スキル向上"
   }
5. user_dynamic_profile の JSONB に追加:
   UPDATE user_dynamic_profile
   SET profile_data = jsonb_set(
       profile_data,
       '{side_job_preference}',
       '"希望する"'
   )

→ スキーマ変更不要！
→ 既存システム影響なし！
→ 即座に検索可能！
```

---

## 3-4. 実際のクエリ例：複雑な条件

```python
def find_matching_users(complex_criteria):
    """
    複雑な条件でユーザーを検索
    固定カラム + JSONB + エンベディング の組み合わせ
    """
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    # クエリのエンベディング生成
    query_text = f"""
    {complex_criteria['description']}
    職種: {complex_criteria.get('job_title')}
    優先事項: {complex_criteria.get('priorities')}
    """
    
    query_embedding = generate_embedding(query_text)
    
    # 複合クエリ
    cur.execute("""
        SELECT 
            up.user_id,
            up.job_title,
            up.location_prefecture,
            udp.profile_data->'learning_interests' as learning,
            1 - (up.conversation_embedding <=> %s::vector) as similarity
        FROM user_profile up
        JOIN user_dynamic_profile udp ON up.user_id = udp.user_id
        WHERE 
            -- 固定カラムで高速フィルタ
            up.work_life_balance_priority >= %s
            AND up.salary_min >= %s
            
            -- JSONBで柔軟フィルタ
            AND udp.profile_data->'learning_interests' ? %s
            
            -- エンベディングで意味的類似度
            AND (up.conversation_embedding <=> %s::vector) < 0.3
            
        ORDER BY similarity DESC
        LIMIT 20
    """, (
        query_embedding,
        complex_criteria['min_wlb_priority'],
        complex_criteria['min_salary'],
        complex_criteria['required_skill'],
        query_embedding
    ))
    
    return cur.fetchall()


# 使用例
results = find_matching_users({
    'description': 'フロントエンド技術を学びたい、家族時間も大切にしたい',
    'job_title': 'フロントエンドエンジニア',
    'priorities': ['work_life_balance', 'career_growth'],
    'min_wlb_priority': 4,
    'min_salary': 500,
    'required_skill': 'React'
})
```

---

# 4. 実装例

## 4-1. データ保存の完全な流れ

```python
"""
user_profile_manager.py
ユーザープロファイルの保存・更新を管理
"""

import json
from openai import OpenAI
import psycopg2

client = OpenAI()

class UserProfileManager:
    """
    ユーザープロファイルを管理
    固定カラム、JSONB、エンベディングを適切に使い分け
    """
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.conn = psycopg2.connect(
            host="localhost",
            dbname="jobmatch",
            user="devuser",
            password="devpass"
        )
    
    def save_chat_message(self, session_id, sender, message):
        """
        チャットメッセージを保存（完全テキスト）
        """
        cur = self.conn.cursor()
        
        cur.execute("""
            INSERT INTO chat_history (
                user_id, session_id, sender, message, created_at
            ) VALUES (%s, %s, %s, %s, NOW())
            RETURNING id
        """, (self.user_id, session_id, sender, message))
        
        message_id = cur.fetchone()[0]
        self.conn.commit()
        cur.close()
        
        return message_id
    
    def extract_and_save_insights(self, message, message_id):
        """
        AIでメッセージから情報を抽出して保存
        """
        
        # STEP 1: AIで情報抽出
        extracted = self._extract_insights_with_ai(message)
        
        if not extracted:
            return
        
        cur = self.conn.cursor()
        
        # STEP 2: 抽出情報をextracted_insightsに保存
        cur.execute("""
            INSERT INTO extracted_insights (
                user_id, source_message_id, insights, 
                confidence_score, created_at
            ) VALUES (%s, %s, %s, %s, NOW())
        """, (
            self.user_id,
            message_id,
            json.dumps(extracted),
            extracted.get('confidence', 0.8)
        ))
        
        # STEP 3: 固定カラムを更新（該当する場合）
        self._update_fixed_columns(extracted)
        
        # STEP 4: JSONBを更新（柔軟データ）
        self._update_dynamic_profile(extracted)
        
        self.conn.commit()
        cur.close()
    
    def _extract_insights_with_ai(self, message):
        """
        OpenAI APIで情報を抽出
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """
あなたは求人マッチングシステムのデータアナリストです。
ユーザーのメッセージから以下の情報を抽出してJSON形式で返してください:

1. explicit_preferences: 明示的な希望条件
   - job_title, location, salary, remote_work など

2. implicit_values: 暗黙の価値観（1-5で推定）
   - work_life_balance_priority
   - career_growth_priority
   - stability_priority

3. emotional_state: 感情・態度
   - sentiment (positive/negative/neutral)
   - confidence (high/medium/low)
   - urgency (high/medium/low)

4. extracted_keywords: キーワード抽出

5. confidence: この抽出の信頼度 (0.0-1.0)

JSON形式で返してください。
"""
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            temperature=0.3,
            response_format={ "type": "json_object" }
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except:
            return None
    
    def _update_fixed_columns(self, extracted):
        """
        固定カラムを更新
        """
        cur = self.conn.cursor()
        
        # 優先度の更新
        implicit_values = extracted.get('implicit_values', {})
        
        if implicit_values:
            cur.execute("""
                UPDATE user_profile
                SET 
                    work_life_balance_priority = COALESCE(%s, work_life_balance_priority),
                    career_growth_priority = COALESCE(%s, career_growth_priority),
                    stability_priority = COALESCE(%s, stability_priority),
                    last_updated = NOW()
                WHERE user_id = %s
            """, (
                implicit_values.get('work_life_balance_priority'),
                implicit_values.get('career_growth_priority'),
                implicit_values.get('stability_priority'),
                self.user_id
            ))
        
        # 基本情報の更新
        explicit_prefs = extracted.get('explicit_preferences', {})
        
        if explicit_prefs:
            cur.execute("""
                UPDATE user_profile
                SET 
                    job_title = COALESCE(%s, job_title),
                    location_prefecture = COALESCE(%s, location_prefecture),
                    salary_min = COALESCE(%s, salary_min)
                WHERE user_id = %s
            """, (
                explicit_prefs.get('job_title'),
                explicit_prefs.get('location'),
                explicit_prefs.get('salary_min'),
                self.user_id
            ))
        
        cur.close()
    
    def _update_dynamic_profile(self, extracted):
        """
        JSONB（柔軟データ）を更新
        """
        cur = self.conn.cursor()
        
        # 既存のJSONBデータを取得
        cur.execute("""
            SELECT profile_data 
            FROM user_dynamic_profile 
            WHERE user_id = %s
        """, (self.user_id,))
        
        result = cur.fetchone()
        current_data = result[0] if result else {}
        
        # 新しい情報をマージ
        explicit_prefs = extracted.get('explicit_preferences', {})
        keywords = extracted.get('extracted_keywords', [])
        
        # learning_interests の追加
        if 'learning_interest' in explicit_prefs:
            if 'learning_interests' not in current_data:
                current_data['learning_interests'] = []
            
            interest = explicit_prefs['learning_interest']
            if interest not in current_data['learning_interests']:
                current_data['learning_interests'].append(interest)
        
        # career_goal の更新
        if 'career_goal' in explicit_prefs:
            current_data['career_goal'] = explicit_prefs['career_goal']
        
        # pain_points の追加
        if 'pain_point' in explicit_prefs:
            if 'pain_points' not in current_data:
                current_data['pain_points'] = []
            current_data['pain_points'].append(explicit_prefs['pain_point'])
        
        # キーワードの蓄積
        if 'all_keywords' not in current_data:
            current_data['all_keywords'] = []
        current_data['all_keywords'].extend(keywords)
        current_data['all_keywords'] = list(set(current_data['all_keywords']))  # 重複削除
        
        # JSONBを更新
        cur.execute("""
            INSERT INTO user_dynamic_profile (user_id, profile_data)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE
            SET profile_data = %s,
                updated_at = NOW()
        """, (
            self.user_id,
            json.dumps(current_data),
            json.dumps(current_data)
        ))
        
        cur.close()
    
    def update_conversation_embedding(self, session_id):
        """
        会話エンベディングを生成＆更新
        """
        cur = self.conn.cursor()
        
        # 最近の会話を取得
        cur.execute("""
            SELECT message
            FROM chat_history
            WHERE user_id = %s
              AND session_id = %s
              AND sender = 'user'
            ORDER BY created_at DESC
            LIMIT 10
        """, (self.user_id, session_id))
        
        messages = [row[0] for row in cur.fetchall()]
        
        if not messages:
            cur.close()
            return
        
        # 会話テキストを結合
        conversation_text = "\n".join(reversed(messages))
        
        # エンベディング生成
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=conversation_text
        )
        
        embedding = response.data[0].embedding
        
        # エンベディング履歴に保存
        cur.execute("""
            INSERT INTO user_embedding_history (
                user_id, session_id, embedding, 
                source_type, source_text, created_at
            ) VALUES (%s, %s, %s, %s, %s, NOW())
        """, (
            self.user_id,
            session_id,
            embedding,
            'conversation',
            conversation_text[:500]  # 最初の500文字
        ))
        
        # user_profile のエンベディングを更新
        cur.execute("""
            UPDATE user_profile
            SET conversation_embedding = %s::vector,
                last_updated = NOW()
            WHERE user_id = %s
        """, (embedding, self.user_id))
        
        self.conn.commit()
        cur.close()
    
    def close(self):
        self.conn.close()


# ============================================
# 使用例
# ============================================

def handle_user_message(user_id, session_id, message):
    """
    ユーザーメッセージを受信したときの処理
    """
    
    manager = UserProfileManager(user_id)
    
    # 1. チャットメッセージを保存
    message_id = manager.save_chat_message(
        session_id=session_id,
        sender='user',
        message=message
    )
    
    # 2. AIで情報抽出＆保存
    manager.extract_and_save_insights(message, message_id)
    
    # 3. エンベディング更新
    manager.update_conversation_embedding(session_id)
    
    manager.close()
    
    print(f"""
    ✅ ユーザーメッセージを処理しました
    
    保存先:
    - chat_history: 完全テキスト
    - extracted_insights: AI抽出情報
    - user_profile: 固定カラム更新
    - user_dynamic_profile: JSONB更新
    - user_embedding_history: エンベディング
    """)


# 実行例
if __name__ == "__main__":
    handle_user_message(
        user_id=5001,
        session_id="session_abc123",
        message="通勤時間が片道1.5時間で、家族との時間とReactの勉強に使いたいです"
    )
```

---

## 4-2. データ取得の例

```python
def get_comprehensive_user_profile(user_id):
    """
    ユーザーの包括的なプロファイルを取得
    固定カラム + JSONB + 会話履歴 + エンベディング
    """
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    # 1. 固定カラムデータ
    cur.execute("""
        SELECT 
            job_title,
            location_prefecture,
            salary_min,
            work_life_balance_priority,
            career_growth_priority,
            decision_style,
            career_stage
        FROM user_profile
        WHERE user_id = %s
    """, (user_id,))
    
    fixed_data = cur.fetchone()
    
    # 2. JSONB柔軟データ
    cur.execute("""
        SELECT profile_data
        FROM user_dynamic_profile
        WHERE user_id = %s
    """, (user_id,))
    
    dynamic_data = cur.fetchone()
    dynamic_profile = dynamic_data[0] if dynamic_data else {}
    
    # 3. 最近の会話履歴
    cur.execute("""
        SELECT sender, message, created_at
        FROM chat_history
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 20
    """, (user_id,))
    
    chat_history = cur.fetchall()
    
    # 4. 抽出済みインサイト
    cur.execute("""
        SELECT insights, confidence_score, created_at
        FROM extracted_insights
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 10
    """, (user_id,))
    
    insights = cur.fetchall()
    
    cur.close()
    conn.close()
    
    # 統合されたプロファイル
    return {
        'basic_info': {
            'job_title': fixed_data[0],
            'location': fixed_data[1],
            'salary_min': fixed_data[2]
        },
        'priorities': {
            'work_life_balance': fixed_data[3],
            'career_growth': fixed_data[4]
        },
        'characteristics': {
            'decision_style': fixed_data[5],
            'career_stage': fixed_data[6]
        },
        'detailed_preferences': dynamic_profile,
        'recent_conversations': [
            {
                'sender': row[0],
                'message': row[1],
                'time': row[2]
            }
            for row in chat_history
        ],
        'ai_insights': [
            {
                'data': row[0],
                'confidence': row[1],
                'extracted_at': row[2]
            }
            for row in insights
        ]
    }


# 使用例
profile = get_comprehensive_user_profile(5001)
print(json.dumps(profile, indent=2, ensure_ascii=False))
```

---

# 🎯 まとめ

## ✅ 保存されるデータ

1. **基本的な行動履歴**（user_interactions）
2. **完全な会話テキスト**（chat_history）
3. **AI抽出情報**（extracted_insights）
4. **固定カラム**（user_profile）
5. **柔軟JSONB**（user_dynamic_profile）
6. **エンベディングベクトル**（user_embedding_history）

## ✅ 柔軟性の実現方法

- **固定カラム**: よく使う情報（高速）
- **JSONB**: 予測不能な情報（柔軟）
- **テキスト**: 完全な会話保存（再解析可能）
- **エンベディング**: 意味検索（AI活用）

## ✅ なぜこの設計なのか

```
質問: 新しい質問に対応できるのか？
回答: できます！

理由:
1. 会話は完全テキストで保存
2. AIが随時再解析
3. JSONBで柔軟に保存
4. スキーマ変更不要

例:
- 今日「副業」について聞き始める
- ユーザー「副業したいです」
- chat_history に保存
- AIが「副業希望」を抽出
- JSONBに追加: {"side_job": "希望"}
- 即座に検索可能！
```

---

**この設計で、無限に進化できるシステムが完成します！** 🚀
