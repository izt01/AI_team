# データベーステーブル カラム一覧

## 1. personal_date（個人情報テーブル）

| No | PK | UK | カラム名 | 項目名 | 概要 | データ型 | 長さ（バイト） | NOT NULL | 備考 |
|---|---|---|---------|--------|------|---------|--------------|---------|------|
| 1 | ○ | - | user_id | ユーザーID | ユーザーの一意識別ID | INTEGER | 4 | ○ | 自動採番（MAX+1） |
| 2 | - | ○ | email | メールアドレス | ユーザーのメールアドレス | VARCHAR | 255 | ○ | ログイン認証に使用 |
| 3 | - | - | password_hash | パスワードハッシュ | ハッシュ化されたパスワード | VARCHAR | 255 | ○ | Werkzeugでハッシュ化 |
| 4 | - | - | user_name | ユーザー名 | ユーザーの名前 | VARCHAR | 100 | ○ | ログイン認証にも使用可 |
| 5 | - | - | birth_day | 生年月日 | ユーザーの生年月日 | DATE | 4 | - | オプション項目 |
| 6 | - | - | phone_number | 電話番号 | 連絡先電話番号 | VARCHAR | 20 | - | オプション項目 |
| 7 | - | - | address | 住所 | ユーザーの住所 | VARCHAR | 255 | - | オプション項目 |
| 8 | - | - | created_at | 作成日時 | レコード作成日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |
| 9 | - | - | updated_at | 更新日時 | レコード更新日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |

**使用箇所:** app.py:70-104（登録）, app.py:135-156（ログイン）

---

## 2. user_profile（ユーザープロファイルテーブル）

| No | PK | UK | カラム名 | 項目名 | 概要 | データ型 | 長さ（バイト） | NOT NULL | 備考 |
|---|---|---|---------|--------|------|---------|--------------|---------|------|
| 1 | ○ | - | user_id | ユーザーID | personal_dateへの外部キー | INTEGER | 4 | ○ | personal_date.user_id参照 |
| 2 | - | - | job_title | 希望職種 | ユーザーが希望する職種 | VARCHAR | 100 | - | 初期値は空文字列 |
| 3 | - | - | location_prefecture | 希望勤務地 | 希望する都道府県 | VARCHAR | 50 | - | 初期値は空文字列 |
| 4 | - | - | salary_min | 希望最低年収 | 希望する最低年収（万円） | INTEGER | 4 | - | 初期値は0 |
| 5 | - | - | intent_label | 意図ラベル | ユーザーの意図・希望条件 | TEXT | 可変 | - | カンマ区切りのラベル |
| 6 | - | - | created_at | 作成日時 | レコード作成日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |
| 7 | - | - | updated_at | 更新日時 | レコード更新日時 | TIMESTAMP | 8 | ○ | AIによる意図抽出時も更新 |

**使用箇所:** app.py:92-95（作成）, app.py:107-131（更新）, app.py:1933-1979（意図抽出で更新）

---

## 3. company_date（企業マスタテーブル）

| No | PK | UK | カラム名 | 項目名 | 概要 | データ型 | 長さ（バイト） | NOT NULL | 備考 |
|---|---|---|---------|--------|------|---------|--------------|---------|------|
| 1 | ○ | - | id | レコードID | 主キー | UUID | 16 | ○ | uuid.uuid4()で生成 |
| 2 | - | - | company_id | 企業ID | 企業識別子 | UUID | 16 | ○ | uuid.uuid4()で生成 |
| 3 | - | ○ | email | メールアドレス | 企業担当者メールアドレス | VARCHAR | 255 | ○ | ログイン認証に使用 |
| 4 | - | - | password | パスワードハッシュ | ハッシュ化されたパスワード | VARCHAR | 255 | ○ | Werkzeugでハッシュ化 |
| 5 | - | - | company_name | 企業名 | 企業の正式名称 | VARCHAR | 200 | ○ | 求人表示時に使用 |
| 6 | - | - | address | 企業住所 | 企業の所在地 | VARCHAR | 255 | - | オプション項目 |
| 7 | - | - | phone_number | 電話番号 | 企業の代表電話番号 | VARCHAR | 20 | - | オプション項目 |
| 8 | - | - | website_url | ウェブサイトURL | 企業の公式サイトURL | VARCHAR | 255 | - | オプション項目 |
| 9 | - | - | created_at | 作成日時 | レコード作成日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |
| 10 | - | - | updated_at | 更新日時 | レコード更新日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |

**使用箇所:** company_app.py:26-42（ログイン）, company_app.py:46-72（登録）

---

## 4. company_profile（求人情報テーブル）

| No | PK | UK | カラム名 | 項目名 | 概要 | データ型 | 長さ（バイト） | NOT NULL | 備考 |
|---|---|---|---------|--------|------|---------|--------------|---------|------|
| 1 | ○ | - | id | 求人ID | 主キー | UUID | 16 | ○ | uuid.uuid4()で生成 |
| 2 | - | - | company_id | 企業ID | company_dateへの外部キー | UUID | 16 | ○ | company_date.company_id参照 |
| 3 | - | - | job_title | 職種名 | 求人の職種名 | VARCHAR | 200 | ○ | エンベディング生成に使用 |
| 4 | - | - | salary_min | 最低年収 | 最低年収（万円） | INTEGER | 4 | ○ | フィルタリング条件 |
| 5 | - | - | salary_max | 最高年収 | 最高年収（万円） | INTEGER | 4 | ○ | フィルタリング条件 |
| 6 | - | - | location_prefecture | 勤務地 | 勤務地（都道府県） | VARCHAR | 50 | - | フィルタリング条件 |
| 7 | - | - | intent_labels | 意図ラベル | 求人の特徴ラベル | TEXT | 可変 | - | カンマ区切り（ボーナス、残業等） |
| 8 | - | - | embedding | エンベディング | OpenAI Embeddingベクトル | VECTOR | 6144 | - | 1536次元ベクトル（pgvector） |
| 9 | - | - | click_count | クリック数 | 求人がクリックされた回数 | INTEGER | 4 | - | デフォルト: 0 |
| 10 | - | - | favorite_count | お気に入り数 | お気に入り登録された回数 | INTEGER | 4 | - | デフォルト: 0 |
| 11 | - | - | apply_count | 応募数 | 応募された回数 | INTEGER | 4 | - | デフォルト: 0 |
| 12 | - | - | view_count | 閲覧数 | 詳細が閲覧された回数 | INTEGER | 4 | - | デフォルト: 0 |
| 13 | - | - | created_at | 作成日時 | レコード作成日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |
| 14 | - | - | updated_at | 更新日時 | レコード更新日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |

**使用箇所:** company_app.py:75-105（登録）, app.py:168-257（推薦表示）, tracking.py:38-56（カウント更新）

---

## 5. user_interactions（ユーザー行動記録テーブル）

| No | PK | UK | カラム名 | 項目名 | 概要 | データ型 | 長さ（バイト） | NOT NULL | 備考 |
|---|---|---|---------|--------|------|---------|--------------|---------|------|
| 1 | ○ | - | id | レコードID | 主キー | SERIAL | 4 | ○ | 自動採番 |
| 2 | - | - | user_id | ユーザーID | personal_dateへの外部キー | INTEGER | 4 | ○ | personal_date.user_id参照 |
| 3 | - | - | job_id | 求人ID | company_profileへの外部キー | UUID | 16 | ○ | company_profile.id参照 |
| 4 | - | - | interaction_type | 行動タイプ | 行動の種類 | VARCHAR | 50 | ○ | click/favorite/apply/view/chat_mention |
| 5 | - | - | interaction_value | 行動値 | 数値データ（閲覧時間など） | FLOAT | 8 | - | デフォルト: 0.0 |
| 6 | - | - | metadata | メタデータ | 追加情報（JSON形式） | JSONB | 可変 | - | オプション |
| 7 | - | - | created_at | 作成日時 | レコード作成日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |

**使用箇所:** tracking.py:26-58（記録）, hybrid_recommender.py:46-196（協調フィルタリング）

**interaction_typeの値とスコア:**
- `apply`: 応募（5.0）
- `favorite`: お気に入り（3.0）
- `click`: クリック（1.0）
- `view`: 閲覧（0.5）
- `chat_mention`: チャット内言及（0.0）

---

## 6. chat_history（チャット履歴テーブル）

| No | PK | UK | カラム名 | 項目名 | 概要 | データ型 | 長さ（バイト） | NOT NULL | 備考 |
|---|---|---|---------|--------|------|---------|--------------|---------|------|
| 1 | ○ | - | id | レコードID | 主キー | SERIAL | 4 | ○ | 自動採番 |
| 2 | - | - | user_id | ユーザーID | personal_dateへの外部キー | INTEGER | 4 | ○ | personal_date.user_id参照 |
| 3 | - | - | message_type | メッセージタイプ | メッセージの送信者 | VARCHAR | 20 | ○ | user/bot |
| 4 | - | - | message_text | メッセージ本文 | 会話の内容 | TEXT | 可変 | ○ | ユーザーまたはボットのメッセージ |
| 5 | - | - | extracted_intent | 抽出意図 | AIが抽出した意図（JSON） | JSONB | 可変 | - | オプション |
| 6 | - | - | session_id | セッションID | チャットセッションの識別子 | VARCHAR | 50 | - | uuid.uuid4()で生成 |
| 7 | - | - | created_at | 作成日時 | レコード作成日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |

**使用箇所:** tracking.py:299-361（保存・取得）, app.py:280-465（チャット処理）, app.py:1076-1090（エンベディング生成）

---

## 7. user_question_responses（動的質問への回答テーブル）

| No | PK | UK | カラム名 | 項目名 | 概要 | データ型 | 長さ（バイト） | NOT NULL | 備考 |
|---|---|---|---------|--------|------|---------|--------------|---------|------|
| 1 | ○ | - | id | レコードID | 主キー | SERIAL | 4 | ○ | 自動採番 |
| 2 | - | ○ | user_id | ユーザーID | personal_dateへの外部キー | INTEGER | 4 | ○ | personal_date.user_id参照 |
| 3 | - | ○ | question_id | 質問ID | dynamic_questionsへの外部キー | INTEGER | 4 | ○ | dynamic_questions.id参照 |
| 4 | - | - | question_key | 質問キー | 質問の識別キー | VARCHAR | 100 | - | question_idから生成 |
| 5 | - | - | response_text | 回答テキスト | ユーザーの回答（生の文字列） | TEXT | 可変 | ○ | ユーザー入力そのまま |
| 6 | - | - | normalized_response | 正規化回答 | 正規化された回答 | TEXT | 可変 | - | AIで正規化（true/false等） |
| 7 | - | - | confidence_score | 確信度スコア | AIの確信度（0.0-1.0） | FLOAT | 8 | - | デフォルト: 0.0 |
| 8 | - | - | created_at | 作成日時 | レコード作成日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |

**UNIQUE制約:** (user_id, question_id) - 同じユーザーが同じ質問に複数回答不可

**使用箇所:** tracking.py:397-468（保存・取得）, multi_axis_evaluator.py:257-264（プロファイル構築）

---

## 8. dynamic_questions（動的質問マスタテーブル）

| No | PK | UK | カラム名 | 項目名 | 概要 | データ型 | 長さ（バイト） | NOT NULL | 備考 |
|---|---|---|---------|--------|------|---------|--------------|---------|------|
| 1 | ○ | - | id | 質問ID | 主キー | SERIAL | 4 | ○ | 自動採番 |
| 2 | - | ○ | question_key | 質問キー | 質問の一意識別子 | VARCHAR | 100 | ○ | remote/flex_time等 |
| 3 | - | - | question_text | 質問文 | 実際の質問文 | TEXT | 可変 | ○ | ユーザーに表示される質問 |
| 4 | - | - | category | カテゴリ | 質問のカテゴリ | VARCHAR | 100 | ○ | 働き方の柔軟性/企業文化等 |
| 5 | - | - | question_type | 質問タイプ | 回答の形式 | VARCHAR | 50 | - | boolean/choice/text |
| 6 | - | - | usage_count | 使用回数 | 質問が使用された回数 | INTEGER | 4 | - | デフォルト: 0 |
| 7 | - | - | positive_response_count | ポジティブ回答数 | 有効だった回答の数 | INTEGER | 4 | - | デフォルト: 0 |
| 8 | - | - | effectiveness_score | 有効性スコア | 質問の有効性（0.0-1.0） | FLOAT | 8 | - | デフォルト: 0.0 |
| 9 | - | - | created_at | 作成日時 | レコード作成日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |
| 10 | - | - | updated_at | 更新日時 | レコード更新日時 | TIMESTAMP | 8 | ○ | 使用時に更新 |

**使用箇所:** app.py:1996-2037（初期化）, dynamic_questions.py:24-436（生成・選択）, tracking.py:424-468（更新）

---

## 9. job_attributes（求人属性テーブル）

| No | PK | UK | カラム名 | 項目名 | 概要 | データ型 | 長さ（バイト） | NOT NULL | 備考 |
|---|---|---|---------|--------|------|---------|--------------|---------|------|
| 1 | ○ | - | id | レコードID | 主キー | SERIAL | 4 | ○ | 自動採番 |
| 2 | - | ○ | job_id | 求人ID | company_profileへの外部キー | UUID | 16 | ○ | company_profile.id参照 |
| 3 | - | - | company_culture | 企業文化 | 企業文化・雰囲気（JSON） | JSONB | 可変 | - | AIで抽出 |
| 4 | - | - | work_flexibility | 働き方の柔軟性 | 働き方の柔軟性（JSON） | JSONB | 可変 | - | AIで抽出 |
| 5 | - | - | career_path | キャリアパス | キャリアパス情報（JSON） | JSONB | 可変 | - | AIで抽出 |
| 6 | - | - | created_at | 作成日時 | レコード作成日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |
| 7 | - | - | updated_at | 更新日時 | レコード更新日時 | TIMESTAMP | 8 | ○ | ON CONFLICT時更新 |

**JSON構造:**
- **company_culture:** `{"type": "startup", "atmosphere": "flat", "size": "small"}`
- **work_flexibility:** `{"remote": true, "flex_time": true, "overtime": "low"}`
- **career_path:** `{"growth_opportunities": true, "training": true, "promotion_speed": "fast"}`

**使用箇所:** multi_axis_evaluator.py:24-229（抽出・保存）, app.py:2040-2080（バックグラウンド抽出）

---

## 10. user_preferences（ユーザープロファイルテーブル）

| No | PK | UK | カラム名 | 項目名 | 概要 | データ型 | 長さ（バイト） | NOT NULL | 備考 |
|---|---|---|---------|--------|------|---------|--------------|---------|------|
| 1 | ○ | - | id | レコードID | 主キー | SERIAL | 4 | ○ | 自動採番 |
| 2 | - | ○ | user_id | ユーザーID | personal_dateへの外部キー | INTEGER | 4 | ○ | personal_date.user_id参照 |
| 3 | - | - | preference_vector | プロファイルベクトル | エンベディングベクトル（文字列） | TEXT | 可変 | - | OpenAI Embeddingで生成 |
| 4 | - | - | preference_text | プロファイルテキスト | プロファイルの文章表現 | TEXT | 可変 | - | 回答履歴から生成 |
| 5 | - | - | company_culture_pref | 企業文化の好み | 企業文化の好み（JSON） | JSONB | 可変 | - | 回答から抽出 |
| 6 | - | - | work_flexibility_pref | 働き方の好み | 働き方の好み（JSON） | JSONB | 可変 | - | 回答から抽出 |
| 7 | - | - | career_path_pref | キャリアパスの好み | キャリアパスの好み（JSON） | JSONB | 可変 | - | 回答から抽出 |
| 8 | - | - | created_at | 作成日時 | レコード作成日時 | TIMESTAMP | 8 | ○ | デフォルト: CURRENT_TIMESTAMP |
| 9 | - | - | updated_at | 更新日時 | レコード更新日時 | TIMESTAMP | 8 | ○ | ON CONFLICT時更新 |

**使用箇所:** multi_axis_evaluator.py:231-523（プロファイル更新・スコア計算）

---

## 11. user_interaction_summary（ビュー）

| No | PK | UK | カラム名 | 項目名 | 概要 | データ型 | 長さ（バイト） | NOT NULL | 備考 |
|---|---|---|---------|--------|------|---------|--------------|---------|------|
| 1 | - | - | user_id | ユーザーID | ユーザー識別子 | INTEGER | 4 | ○ | personal_date.user_id参照 |
| 2 | - | - | total_clicks | 総クリック数 | クリックの総数 | BIGINT | 8 | - | user_interactionsから集計 |
| 3 | - | - | total_favorites | 総お気に入り数 | お気に入りの総数 | BIGINT | 8 | - | user_interactionsから集計 |
| 4 | - | - | total_applies | 総応募数 | 応募の総数 | BIGINT | 8 | - | user_interactionsから集計 |
| 5 | - | - | total_views | 総閲覧数 | 閲覧の総数 | BIGINT | 8 | - | user_interactionsから集計 |
| 6 | - | - | last_interaction | 最終行動日時 | 最後に行動した日時 | TIMESTAMP | 8 | - | MAX(created_at) |

**注記:** これはVIEW（ビュー）であり実テーブルではありません

**使用箇所:** tracking.py:176-192（サマリー取得）

---

## テーブル関連図

```
personal_date (ユーザー基本情報)
    │
    ├─→ user_profile (希望条件)
    │
    ├─→ user_interactions (行動履歴)
    │       └─→ company_profile (求人情報)
    │
    ├─→ chat_history (会話履歴)
    │
    ├─→ user_question_responses (質問への回答)
    │       └─→ dynamic_questions (質問マスタ)
    │
    └─→ user_preferences (プロファイル)

company_date (企業基本情報)
    │
    └─→ company_profile (求人情報)
            │
            └─→ job_attributes (求人属性)
```

## 凡例

- **PK**: Primary Key（主キー）
- **UK**: Unique Key（一意制約）
- **NOT NULL**: NULL値を許可しない
- **SERIAL**: 自動採番される整数型
- **UUID**: 128ビットの一意識別子
- **JSONB**: JSON Binary形式（PostgreSQL）
- **VECTOR**: pgvector拡張によるベクトル型
- **TIMESTAMP**: 日時型（タイムゾーン無し）
