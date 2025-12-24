# JobMatch AI - データベーステーブル一覧

## 📋 使用テーブル一覧

### 1️⃣ ユーザー関連テーブル

#### `personal_date` (ユーザー基本情報)
- **id** (PK): ユーザーID
- **user_id**: ユーザーID（idと同じ）
- **email**: メールアドレス
- **password_hash**: パスワードハッシュ
- **user_name**: ユーザー名
- **phone_number**: 電話番号
- **Birth_day**: 生年月日
- **address**: 住所
- **created_at**: 作成日時
- **updated_at**: 更新日時

#### `user_profile` (ユーザープロフィール)
- **id** (PK): プロフィールID
- **user_id** (FK): ユーザーID → personal_date.id
- **job_title**: 希望職種
- **location_prefecture**: 希望勤務地（都道府県）
- **salary_min**: 希望最低年収
- **conversation_embedding**: 会話履歴のエンベディング (vector型)
- **created_at**: 作成日時
- **updated_at**: 更新日時

### 2️⃣ 企業・求人関連テーブル

#### `company_date` (企業基本情報)
- **company_id** (PK): 企業ID
- **company_name**: 企業名
- **industry**: 業界
- **employee_count**: 従業員数
- **founded_year**: 設立年
- **created_at**: 作成日時
- **updated_at**: 更新日時

#### `company_profile` (求人情報)
- **id** (PK): 求人ID (UUID)
- **company_id** (FK): 企業ID → company_date.company_id
- **job_title**: 職種
- **location_prefecture**: 勤務地（都道府県）
- **salary_min**: 最低年収
- **salary_max**: 最高年収
- **remote**: リモートワーク可否 (boolean)
- **flex_time**: フレックスタイム制度 (boolean)
- **side_job**: 副業可否 (boolean)
- **training**: 研修制度 (boolean)
- **growth**: 成長機会 (boolean)
- **embedding**: 求人説明文のエンベディング (vector型)
- **click_count**: クリック数
- **favorite_count**: お気に入り数
- **apply_count**: 応募数
- **created_at**: 作成日時
- **updated_at**: 更新日時

### 3️⃣ ユーザー行動関連テーブル

#### `user_interactions` (ユーザー行動履歴)
- **id** (PK): 行動ID
- **user_id** (FK): ユーザーID → personal_date.id
- **job_id** (FK): 求人ID → company_profile.id
- **interaction_type**: 行動タイプ ('click', 'favorite', 'apply', 'view')
- **created_at**: 行動日時

#### `user_filtering_history` (絞り込み履歴)
- **id** (PK): 履歴ID
- **user_id** (FK): ユーザーID
- **session_id**: セッションID
- **filtered_job_ids**: 絞り込み後の求人IDリスト (text[])
- **created_at**: 作成日時

### 4️⃣ チャット・質問関連テーブル

#### `chat_history` (チャット履歴)
- **id** (PK): メッセージID
- **user_id** (FK): ユーザーID
- **session_id**: セッションID
- **sender**: 送信者 ('user' or 'bot')
- **message**: メッセージ内容
- **created_at**: 送信日時

#### `dynamic_questions` (動的質問マスタ)
- **id** (PK): 質問ID
- **question_key**: 質問キー ('remote', 'flex_time', etc.)
- **category**: カテゴリ ('働き方の柔軟性', 'キャリアパス', etc.)
- **usage_count**: 使用回数
- **positive_response_count**: ポジティブ回答数
- **created_at**: 作成日時
- **updated_at**: 更新日時

#### `user_question_responses` (ユーザー質問回答)
- **id** (PK): 回答ID
- **user_id** (FK): ユーザーID
- **question_id** (FK, nullable): 質問ID → dynamic_questions.id
- **question_key**: 質問キー
- **response_text**: 回答テキスト
- **normalized_response**: 正規化された回答
- **created_at**: 回答日時

### 5️⃣ その他のテーブル（使用していない可能性あり）

- `company_jobs`: 使用状況不明
- `conversation_log`: 使用状況不明
- `employees`: 使用状況不明
- `job_attributes`: 使用状況不明
- `jobs`: 使用状況不明
- `ml_model_scores`: 使用状況不明
- `scout_messages`: 使用状況不明
- `search_history`: 使用状況不明
- `user_conversation_embeddings`: 使用状況不明
- `user_filtered_jobs`: 使用状況不明
- `user_interaction_summary`: 使用状況不明
- `user_personality_analysis`: 使用状況不明
- `user_preferences`: 使用状況不明
- `user_profile_history`: 使用状況不明

---

## 🔗 テーブル関係図

```
personal_date (ユーザー)
    ├─→ user_profile (プロフィール)
    ├─→ user_interactions (行動履歴)
    ├─→ user_filtering_history (絞り込み履歴)
    ├─→ chat_history (チャット履歴)
    └─→ user_question_responses (質問回答)

company_date (企業)
    └─→ company_profile (求人)
            └─→ user_interactions (行動履歴)

dynamic_questions (質問マスタ)
    └─→ user_question_responses (質問回答)
```

---

## 📊 必須データフロー

1. **ユーザー登録** → `personal_date` + `user_profile`
2. **チャット開始** → `chat_history`
3. **質問回答** → `user_question_responses`
4. **求人絞り込み** → `user_filtering_history`
5. **求人閲覧/お気に入り/応募** → `user_interactions`
6. **類似ユーザー検索** → `user_interactions` を分析
7. **エンベディング検索** → `user_profile.conversation_embedding` と `company_profile.embedding` を比較
