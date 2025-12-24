# JobMatch AI - データベーステーブル一覧

## 📋 **テーブル一覧**

### 1. **personal_date** (ユーザー基本情報)
個人情報を格納するテーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | integer (PK) | ユーザーID |
| user_id | integer | ユーザーID（重複） |
| email | varchar | メールアドレス |
| password_hash | varchar | パスワードハッシュ |
| user_name | varchar | ユーザー名 |
| phone_number | varchar | 電話番号 |
| birth_day | date | 生年月日 |
| address | text | 住所 |
| created_at | timestamp | 作成日時 |
| updated_at | timestamp | 更新日時 |

---

### 2. **user_profile** (ユーザープロフィール)
求人検索に使うユーザー情報

| カラム名 | 型 | 説明 |
|---------|-----|------|
| user_id | integer (PK) | ユーザーID |
| job_title | varchar | 希望職種 |
| location_prefecture | varchar | 希望勤務地 |
| salary_min | integer | 希望最低年収 |
| conversation_embedding | vector(1536) | 会話履歴のエンベディング |
| created_at | timestamp | 作成日時 |
| updated_at | timestamp | 更新日時 |

---

### 3. **company_date** (企業基本情報)
企業の基本情報

| カラム名 | 型 | 説明 |
|---------|-----|------|
| company_id | uuid (PK) | 企業ID |
| company_name | varchar | 企業名 |
| industry | varchar | 業種 |
| employee_count | integer | 従業員数 |
| established_year | integer | 設立年 |
| created_at | timestamp | 作成日時 |

---

### 4. **company_profile** (求人情報)
企業が出している求人の詳細

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | uuid (PK) | 求人ID |
| company_id | uuid (FK) | 企業ID |
| job_title | varchar | 職種名 |
| location_prefecture | varchar | 勤務地 |
| salary_min | integer | 最低年収 |
| salary_max | integer | 最高年収 |
| remote_work | boolean | リモートワーク可否 |
| flex_time | boolean | フレックス制度 |
| side_job | boolean | 副業可否 |
| training | boolean | 研修制度 |
| growth | boolean | 成長機会 |
| company_size | varchar | 企業規模 |
| embedding | vector(1536) | 求人のエンベディング |
| click_count | integer | クリック数 |
| favorite_count | integer | お気に入り数 |
| apply_count | integer | 応募数 |
| created_at | timestamp | 作成日時 |

---

### 5. **user_interactions** (ユーザー行動履歴)
ユーザーが求人に対して行った行動

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | serial (PK) | ID |
| user_id | integer (FK) | ユーザーID |
| job_id | uuid (FK) | 求人ID |
| interaction_type | varchar | 行動タイプ（click/favorite/apply/view） |
| created_at | timestamp | 行動日時 |

---

### 6. **chat_history** (チャット履歴)
ユーザーとAIの会話履歴

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | serial (PK) | ID |
| user_id | integer (FK) | ユーザーID |
| role | varchar | 発言者（user/bot） |
| message | text | メッセージ内容 |
| session_id | varchar | セッションID |
| created_at | timestamp | 発言日時 |

---

### 7. **user_question_responses** (質問回答履歴)
AIがユーザーに質問した回答

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | serial (PK) | ID |
| user_id | integer (FK) | ユーザーID |
| question_id | integer (FK) | 質問ID（NULL可） |
| question_key | varchar | 質問キー（remote/flex_time等） |
| response_text | text | 回答テキスト |
| normalized_response | varchar | 正規化された回答 |
| created_at | timestamp | 回答日時 |

---

### 8. **dynamic_questions** (動的質問マスタ)
AIが生成する質問のマスタ

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | serial (PK) | ID |
| question_key | varchar | 質問キー |
| question_text | text | 質問文 |
| category | varchar | カテゴリ |
| usage_count | integer | 使用回数 |
| positive_response_count | integer | ポジティブ回答数 |
| created_at | timestamp | 作成日時 |

---

### 9. **user_filtering_history** (絞り込み履歴)
各セッションでの求人絞り込み履歴

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | serial (PK) | ID |
| user_id | integer (FK) | ユーザーID |
| session_id | varchar | セッションID |
| filtered_job_ids | text[] | 絞り込まれた求人IDリスト |
| created_at | timestamp | 作成日時 |

---

### 10. **search_history** (検索履歴)
ユーザーの検索履歴

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | serial (PK) | ID |
| user_id | integer (FK) | ユーザーID |
| query | text | 検索クエリ |
| created_at | timestamp | 検索日時 |

---

### 11. **user_interaction_summary** (ユーザー行動サマリー)
ユーザーの行動統計（マテリアライズドビュー）

| カラム名 | 型 | 説明 |
|---------|-----|------|
| user_id | integer | ユーザーID |
| total_clicks | bigint | 総クリック数 |
| total_favorites | bigint | 総お気に入り数 |
| total_applies | bigint | 総応募数 |
| last_interaction | timestamp | 最終行動日時 |

---

### 12. **user_conversation_embeddings** (会話エンベディング)
ユーザーの会話履歴のベクトル表現（廃止予定）

※ 現在は `user_profile.conversation_embedding` に統合

---

## 📊 **テーブル関連図**

```
personal_date (ユーザー基本情報)
    ↓ (1:1)
user_profile (ユーザープロフィール)
    ↓ (1:N)
user_interactions (行動履歴)
    ↓ (N:1)
company_profile (求人情報)
    ↓ (N:1)
company_date (企業情報)

user_question_responses (質問回答)
    ↓ (N:1)
dynamic_questions (質問マスタ)

chat_history (チャット履歴)
    ↓ (N:1)
personal_date (ユーザー)
```

---

## 🔑 **重要なテーブル**

### 協調フィルタリングに必要
- `user_interactions` ← 必須（ユーザー行動データ）

### コンテンツベースフィルタリングに必要
- `user_profile` ← 必須（ユーザープロフィール）
- `company_profile` ← 必須（求人情報）

### エンベディング検索に必要
- `user_profile.conversation_embedding` ← チャット履歴から生成
- `company_profile.embedding` ← 求人説明から生成

### チャット機能に必要
- `chat_history` ← 会話履歴
- `user_question_responses` ← 質問回答
- `dynamic_questions` ← 質問マスタ
