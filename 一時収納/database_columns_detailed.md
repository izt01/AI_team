# データベーステーブル カラム詳細一覧

このドキュメントでは、各テーブルのカラムについて、どのような値が入るのか、どこで使われているのかを詳細に説明します。

---

## 1. personal_date（個人情報テーブル）

ユーザーの基本的な個人情報を格納します。

| カラム名 | 型 | 内容 | 使用箇所 | 例 |
|---------|-----|------|---------|-----|
| `user_id` | INTEGER | ユーザーの一意識別ID（自動採番） | app.py:84（MAX+1で生成）、ログイン、セッション管理全般 | 1, 2, 3... |
| `email` | VARCHAR | メールアドレス | app.py:74（登録）、app.py:143（ログイン） | `user@example.com` |
| `password_hash` | VARCHAR | ハッシュ化されたパスワード | app.py:75（generate_password_hash）、app.py:149（check_password_hash） | `pbkdf2:sha256:...` |
| `user_name` | VARCHAR | ユーザーの名前 | app.py:73（登録）、app.py:143（ログイン時の識別子） | `山田太郎` |
| `birth_day` | DATE | 生年月日 | app.py:76（オプション） | `1990-01-01` |
| `phone_number` | VARCHAR | 電話番号 | app.py:77（オプション） | `090-1234-5678` |
| `address` | VARCHAR | 住所 | app.py:78（オプション） | `東京都渋谷区...` |
| `created_at` | TIMESTAMP | レコード作成日時 | app.py:88（CURRENT_TIMESTAMP） | `2024-01-01 12:00:00` |
| `updated_at` | TIMESTAMP | レコード更新日時 | app.py:88（CURRENT_TIMESTAMP） | `2024-01-01 12:00:00` |

**使用フロー:**
1. ユーザー登録時（app.py:70-104）: 個人情報を入力 → password_hashを生成 → DBに保存
2. ログイン時（app.py:135-156）: email/user_nameとpasswordで認証
3. セッション（app.py:101）: `session["user_id"]`にuser_idを保存

---

## 2. user_profile（ユーザープロファイルテーブル）

ユーザーの希望条件や好みを管理します。

| カラム名 | 型 | 内容 | 使用箇所 | 例 |
|---------|-----|------|---------|-----|
| `user_id` | INTEGER | personal_dateへの外部キー | app.py:93（登録時に自動作成） | 1, 2, 3... |
| `job_title` | VARCHAR | 希望職種 | app.py:111（入力）、app.py:1949（intent抽出で更新） | `Webエンジニア` |
| `location_prefecture` | VARCHAR | 希望勤務地（都道府県） | app.py:112（入力）、app.py:1964（intent抽出で更新） | `東京都` |
| `salary_min` | INTEGER | 希望最低年収（万円） | app.py:113（入力）、app.py:1965（intent抽出で更新） | 500 |
| `intent_label` | TEXT | ユーザーの意図ラベル | multi_axis_evaluator.py:251（プロファイル構築） | `リモートワーク,フレックス` |
| `created_at` | TIMESTAMP | レコード作成日時 | app.py:93 | `2024-01-01 12:00:00` |
| `updated_at` | TIMESTAMP | レコード更新日時 | app.py:122（条件更新時）、app.py:1973（intent更新時） | `2024-01-01 15:30:00` |

**使用フロー:**
1. Step1（個人情報登録）: user_idだけで空レコード作成（app.py:92-95）
2. Step2（希望条件入力）: job_title, location_prefecture, salary_minを更新（app.py:107-131）
3. チャット中: AIがユーザーの発言から意図を抽出 → user_profileを自動更新（app.py:1933-1979）
4. 推薦システム: この情報を元に求人をフィルタリング

---

## 3. company_date（企業マスタテーブル）

企業の基本情報を管理します。

| カラム名 | 型 | 内容 | 使用箇所 | 例 |
|---------|-----|------|---------|-----|
| `id` | UUID | レコードID | company_app.py:61（uuid生成） | `550e8400-e29b-41d4-a716-...` |
| `company_id` | UUID | 企業識別子（複数拠点でも同じ企業） | company_app.py:61（uuid生成） | `660f9511-f3ac-52e5-b827-...` |
| `email` | VARCHAR | 企業担当者メールアドレス | company_app.py:33（ログイン）、company_app.py:52（登録） | `hr@company.com` |
| `password` | VARCHAR | ハッシュ化パスワード | company_app.py:54（generate_password_hash）、company_app.py:38（check_password_hash） | `pbkdf2:sha256:...` |
| `company_name` | VARCHAR | 企業名 | company_app.py:51（登録）、multi_axis_evaluator.py:159（求人属性抽出時） | `株式会社サンプル` |
| `address` | VARCHAR | 企業住所 | company_app.py:62（オプション） | `東京都港区...` |
| `phone_number` | VARCHAR | 電話番号 | company_app.py:63（オプション） | `03-1234-5678` |
| `website_url` | VARCHAR | 企業ウェブサイト | company_app.py:64（オプション） | `https://company.com` |
| `created_at` | TIMESTAMP | レコード作成日時 | company_app.py:60 | `2024-01-01 10:00:00` |
| `updated_at` | TIMESTAMP | レコード更新日時 | company_app.py:60 | `2024-01-01 10:00:00` |

**使用フロー:**
1. 企業登録（company_app.py:46-72）: 企業情報を入力 → UUIDを2つ生成（id, company_id）
2. 企業ログイン（company_app.py:26-42）: emailとpasswordで認証
3. 求人情報表示: company_profileと結合して企業名を表示（multi_axis_evaluator.py:156-163）

---

## 4. company_profile（求人情報テーブル）

企業が登録した求人の詳細情報を管理します。

| カラム名 | 型 | 内容 | 使用箇所 | 例 |
|---------|-----|------|---------|-----|
| `id` | UUID | 求人ID（主キー） | company_app.py:99（uuid生成） | `770g0622-g4bd-63f6-c938-...` |
| `company_id` | UUID | company_dateへの外部キー | company_app.py:99（セッションから取得） | `660f9511-f3ac-52e5-b827-...` |
| `job_title` | VARCHAR | 職種名 | company_app.py:79（入力）、app.py:175（推薦表示） | `バックエンドエンジニア` |
| `salary_min` | INTEGER | 最低年収（万円） | company_app.py:80（入力）、app.py:215（表示） | 500 |
| `salary_max` | INTEGER | 最高年収（万円） | company_app.py:81（入力）、app.py:215（表示） | 800 |
| `location_prefecture` | VARCHAR | 勤務地（都道府県） | hybrid_recommender.py:348（フィルタリング）、app.py:214（表示） | `東京都` |
| `intent_labels` | TEXT | 求人の特徴ラベル（カンマ区切り） | company_app.py:88-91（ボーナス、残業、雰囲気を結合） | `ボーナスあり,残業少,フラット` |
| `embedding` | VECTOR | 求人情報のエンベディング（1536次元） | company_app.py:94-96（OpenAI Embedding API）、app.py:1095（類似度検索） | `[0.023, -0.145, ...]` |
| `click_count` | INTEGER | クリック数 | tracking.py:50（インクリメント） | 0, 15, 234... |
| `favorite_count` | INTEGER | お気に入り数 | tracking.py:52（インクリメント）、tracking.py:72（デクリメント） | 0, 5, 42... |
| `apply_count` | INTEGER | 応募数 | tracking.py:54（インクリメント）、app.py:240（表示） | 0, 3, 18... |
| `view_count` | INTEGER | 閲覧数 | tracking.py:56（インクリメント） | 0, 100, 500... |
| `created_at` | TIMESTAMP | レコード作成日時 | company_app.py:99 | `2024-01-01 11:00:00` |
| `updated_at` | TIMESTAMP | レコード更新日時 | company_app.py:99 | `2024-01-01 11:00:00` |

**使用フロー:**
1. 求人登録（company_app.py:75-105）:
   - 企業が求人情報を入力
   - intent_labelsを生成（ボーナス、残業、雰囲気を結合）
   - profile_text = `job_title + salary_min + salary_max + intent_labels`
   - OpenAI Embedding APIでembeddingを生成
   - DBに保存

2. 推薦システム（app.py:168-257）:
   - user_profileの条件でフィルタリング
   - embeddingでユーザーとの類似度計算
   - 結果を表示

3. 行動追跡（tracking.py:26-58）:
   - ユーザーがクリック/お気に入り/応募 → 対応するカウントをインクリメント

---

## 5. user_interactions（ユーザー行動記録テーブル）

ユーザーの求人に対する行動を記録します。

| カラム名 | 型 | 内容 | 使用箇所 | 例 |
|---------|-----|------|---------|-----|
| `id` | SERIAL | レコードID（自動採番） | - | 1, 2, 3... |
| `user_id` | INTEGER | personal_dateへの外部キー | tracking.py:38（行動記録時） | 1, 2, 3... |
| `job_id` | INTEGER/UUID | company_profileへの外部キー | tracking.py:38（行動記録時） | `770g0622-g4bd-63f6-c938-...` |
| `interaction_type` | VARCHAR | 行動タイプ | tracking.py:38（行動種別）、hybrid_recommender.py:49-54（スコア計算） | `click`, `favorite`, `apply`, `view`, `chat_mention` |
| `interaction_value` | FLOAT | 数値データ（閲覧時間など） | tracking.py:38（オプション） | 30.5（秒）, 0.0 |
| `metadata` | JSONB | 追加情報（JSON形式） | tracking.py:38（オプション） | `{"from": "chat", "context": "..."}` |
| `created_at` | TIMESTAMP | レコード作成日時 | tracking.py:38（自動設定） | `2024-01-01 14:20:00` |

**interaction_typeの値とスコア:**
- `apply`: 応募（スコア: 5.0） - 最も重要
- `favorite`: お気に入り（スコア: 3.0）
- `click`: クリック（スコア: 1.0）
- `view`: 閲覧（スコア: 0.5）
- `chat_mention`: チャット内で言及（スコア: 0.0）

**使用フロー:**
1. 行動記録（tracking.py:26-58）:
   - `UserInteractionTracker.track_interaction(user_id, job_id, 'click')`
   - user_interactionsテーブルに記録
   - company_profileの対応カウントを更新

2. 協調フィルタリング（hybrid_recommender.py:27-196）:
   - user_interactionsから全ユーザーの行動を取得
   - ユーザー×求人のマトリックスを構築
   - 類似ユーザーを見つけて推薦

3. お気に入り管理（tracking.py:68-105）:
   - お気に入り追加: interaction_type='favorite'を記録
   - お気に入り削除: 最新のfavorite記録を削除

---

## 6. chat_history（チャット履歴テーブル）

ユーザーとAIの会話履歴を保存します。

| カラム名 | 型 | 内容 | 使用箇所 | 例 |
|---------|-----|------|---------|-----|
| `id` | SERIAL | レコードID（自動採番） | - | 1, 2, 3... |
| `user_id` | INTEGER | personal_dateへの外部キー | tracking.py:315（メッセージ保存時） | 1, 2, 3... |
| `message_type` | VARCHAR | メッセージタイプ | tracking.py:315（'user' or 'bot'） | `user`, `bot` |
| `message_text` | TEXT | メッセージ本文 | tracking.py:315（会話内容） | `リモートワーク可能な求人を探しています` |
| `extracted_intent` | JSONB | AIが抽出した意図（JSON） | tracking.py:315（app.pyから渡される） | `{"job_title": "エンジニア", "remote": true}` |
| `session_id` | VARCHAR | セッションID | tracking.py:315（app.py:56-60で生成） | `a1b2c3d4-e5f6-7890-abcd-...` |
| `created_at` | TIMESTAMP | レコード作成日時 | tracking.py:315（自動設定） | `2024-01-01 14:25:00` |

**使用フロー:**
1. チャット送信時（app.py:280-465）:
   ```python
   # ユーザーメッセージを保存
   ChatHistoryManager.save_message(
       user_id=user_id,
       message_type='user',
       message_text=user_message,
       session_id=session_id
   )
   
   # AIが意図を抽出
   intent = extract_intent_with_ai(user_message)
   
   # ボット応答を保存
   ChatHistoryManager.save_message(
       user_id=user_id,
       message_type='bot',
       message_text=bot_response,
       extracted_intent=intent,
       session_id=session_id
   )
   ```

2. 会話履歴取得（tracking.py:330-361）:
   - `get_chat_history(user_id, session_id, limit=50)`
   - セッション別または全履歴を取得
   - エンベディング生成時に使用（app.py:1076-1090）

---

## 7. user_question_responses（動的質問への回答テーブル）

ユーザーが動的に生成された質問に対して回答した内容を保存します。

| カラム名 | 型 | 内容 | 使用箇所 | 例 |
|---------|-----|------|---------|-----|
| `id` | SERIAL | レコードID（自動採番） | - | 1, 2, 3... |
| `user_id` | INTEGER | personal_dateへの外部キー | tracking.py:416（回答保存時） | 1, 2, 3... |
| `question_id` | INTEGER | dynamic_questionsへの外部キー | tracking.py:416（質問ID） | 5, 12, 23... |
| `question_key` | VARCHAR(100) | 質問キー（後から追加） | fix_all_issues.py:40-51（生成）、dynamic_question_generator_v2.py（使用） | `remote`, `flex_time`, `overtime` |
| `response_text` | TEXT | ユーザーの回答（生の文字列） | tracking.py:416（ユーザー入力） | `はい、リモートワークを希望します` |
| `normalized_response` | TEXT | 正規化された回答 | tracking.py:416（AIで正規化） | `true`, `false`, `high`, `low` |
| `confidence_score` | FLOAT | 確信度スコア（0.0-1.0） | tracking.py:416（AIの確信度） | 0.95, 0.7, 0.3 |
| `created_at` | TIMESTAMP | レコード作成日時 | tracking.py:416（自動設定） | `2024-01-01 14:30:00` |

**UNIQUE制約:** (user_id, question_id) - 同じユーザーが同じ質問に複数回答できない

**使用フロー:**
1. 質問応答（tracking.py:397-434）:
   ```python
   QuestionResponseManager.save_response(
       user_id=1,
       question_id=5,
       response_text="はい",
       normalized_response="true",
       confidence_score=0.95
   )
   ```
   - UPSERT: 既存の回答がある場合は上書き
   - dynamic_questionsのusage_countをインクリメント

2. ユーザープロファイル構築（multi_axis_evaluator.py:234-300）:
   - user_question_responsesから回答を取得
   - カテゴリ別に整理してプロファイルテキストを生成
   - 推薦システムで活用

3. 推薦理由の生成（app.py:1836-1853）:
   - ユーザーの回答履歴を取得
   - AIに渡して推薦理由を生成

---

## 8. dynamic_questions（動的質問マスタテーブル）

AIが生成した質問や固定の質問テンプレートを管理します。

| カラム名 | 型 | 内容 | 使用箇所 | 例 |
|---------|-----|------|---------|-----|
| `id` | SERIAL | 質問ID（自動採番） | dynamic_questions.py:205（回答済み質問の確認） | 1, 2, 3... |
| `question_key` | VARCHAR(100) | 質問の一意キー | app.py:2023（初期化）、dynamic_questions.py:141（生成） | `remote`, `flex_time`, `side_job` |
| `question_text` | TEXT | 質問文 | app.py:2012-2020（初期質問）、dynamic_questions.py:126-133（テンプレート） | `リモートワーク可能な求人を希望しますか？` |
| `category` | VARCHAR | カテゴリ | app.py:2012-2020（初期化）、dynamic_questions.py:242（優先順位判定） | `働き方の柔軟性`, `企業文化・雰囲気`, `キャリアパス` |
| `question_type` | VARCHAR | 質問タイプ | app.py:2012-2020（初期化） | `boolean`, `choice`, `text` |
| `usage_count` | INTEGER | 使用回数（何人が回答したか） | tracking.py:424-427（インクリメント）、dynamic_questions.py:218（ソート） | 0, 15, 234... |
| `positive_response_count` | INTEGER | ポジティブな回答数 | tracking.py:464（有効な質問をマーク） | 0, 8, 89... |
| `effectiveness_score` | FLOAT | 質問の有効性スコア | dynamic_questions.py:218（ソート優先度） | 0.0〜1.0 |
| `created_at` | TIMESTAMP | レコード作成日時 | app.py:2026（初期化時） | `2024-01-01 09:00:00` |
| `updated_at` | TIMESTAMP | レコード更新日時 | tracking.py:425（使用時更新） | `2024-01-01 14:35:00` |

**UNIQUE制約:** question_key - 同じキーの質問は1つのみ

**使用フロー:**
1. 初期化（app.py:1996-2037）:
   - アプリ起動時に基本質問を登録
   - ON CONFLICT DO NOTHINGで重複回避

2. AI生成質問（dynamic_questions.py:24-183）:
   - 求人データから属性を分析
   - 頻出する属性から質問を自動生成
   - DBに保存

3. 質問選択（dynamic_questions.py:185-250）:
   - 回答済みの質問を除外
   - effectiveness_scoreが高い質問を優先
   - 検索結果の差分がある項目の質問を選択

4. 有効性追跡（tracking.py:446-468）:
   - お気に入りや応募があった場合
   - その質問のpositive_response_countをインクリメント
   - effectiveness_scoreを再計算

---

## 9. job_attributes（求人属性テーブル）

求人情報から抽出した多軸属性を保存します。

| カラム名 | 型 | 内容 | 使用箇所 | 例 |
|---------|-----|------|---------|-----|
| `id` | SERIAL | レコードID（自動採番） | - | 1, 2, 3... |
| `job_id` | UUID | company_profileへの外部キー | multi_axis_evaluator.py:116（保存時）、app.py:2044（全求人属性抽出） | `770g0622-g4bd-63f6-c938-...` |
| `company_culture` | JSONB | 企業文化・雰囲気（JSON） | multi_axis_evaluator.py:126（保存）、multi_axis_evaluator.py:460（スコア計算） | `{"type": "startup", "atmosphere": "flat", "size": "small"}` |
| `work_flexibility` | JSONB | 働き方の柔軟性（JSON） | multi_axis_evaluator.py:127（保存）、multi_axis_evaluator.py:469（スコア計算） | `{"remote": true, "flex_time": true, "overtime": "low"}` |
| `career_path` | JSONB | キャリアパス（JSON） | multi_axis_evaluator.py:128（保存）、multi_axis_evaluator.py:478（スコア計算） | `{"growth_opportunities": true, "training": true, "promotion_speed": "fast"}` |
| `created_at` | TIMESTAMP | レコード作成日時 | multi_axis_evaluator.py:116（自動設定） | `2024-01-01 11:05:00` |
| `updated_at` | TIMESTAMP | レコード更新日時 | multi_axis_evaluator.py:123（ON CONFLICT時更新） | `2024-01-01 15:00:00` |

**UNIQUE制約:** job_id - 1つの求人に1つの属性レコード

**JSON構造の詳細:**

### company_culture（企業文化・雰囲気）
```json
{
  "type": "startup" | "venture" | "mid-size" | "large-enterprise",
  "atmosphere": "flat" | "hierarchical" | "challenging" | "stable",
  "size": "small" | "medium" | "large"
}
```

### work_flexibility（働き方の柔軟性）
```json
{
  "remote": true | false,
  "flex_time": true | false,
  "side_job": true | false,
  "overtime": "low" | "medium" | "high"
}
```

### career_path（キャリアパス）
```json
{
  "growth_opportunities": true | false,
  "training": true | false,
  "promotion_speed": "fast" | "normal" | "slow",
  "skill_support": true | false
}
```

**使用フロー:**
1. 属性抽出（multi_axis_evaluator.py:141-190）:
   ```python
   # 求人情報を取得
   job_text = f"{company_name} {job_title} {location} {salary}..."
   
   # AIで属性を抽出
   attributes = JobAttributeExtractor.extract_attributes_with_ai(job_text)
   
   # DBに保存（UPSERT）
   JobAttributeExtractor.save_job_attributes(job_id, attributes)
   ```

2. バックグラウンド抽出（app.py:2040-2080）:
   - アプリ起動時にjob_attributesが空なら
   - 全求人の属性を抽出（別スレッドで実行）

3. マッチングスコア計算（multi_axis_evaluator.py:418-490）:
   - ユーザーの好みとjob_attributesを比較
   - カテゴリ別に一致度を計算
   - 総合スコアを返す

4. 質問生成（dynamic_questions.py:36-103）:
   - job_attributesから頻出する属性を分析
   - それに基づいて質問を生成

---

## 10. user_preferences（ユーザープロファイルテーブル）

ユーザーの多軸評価プロファイルを保存します（追加テーブル）。

| カラム名 | 型 | 内容 | 使用箇所 | 例 |
|---------|-----|------|---------|-----|
| `id` | SERIAL | レコードID（自動採番） | - | 1, 2, 3... |
| `user_id` | INTEGER | personal_dateへの外部キー | multi_axis_evaluator.py:385（プロファイル更新時） | 1, 2, 3... |
| `preference_vector` | TEXT | エンベディングベクトル（文字列化） | multi_axis_evaluator.py:401（保存） | `[0.023, -0.145, ...]` |
| `preference_text` | TEXT | プロファイルのテキスト表現 | multi_axis_evaluator.py:346（構築）、multi_axis_evaluator.py:402（保存） | `希望職種: エンジニア\n回答: リモートワーク希望...` |
| `company_culture_pref` | JSONB | 企業文化の好み（JSON） | multi_axis_evaluator.py:377-378（構築）、multi_axis_evaluator.py:403（保存） | `{"type": "startup", "atmosphere": "flat"}` |
| `work_flexibility_pref` | JSONB | 働き方の好み（JSON） | multi_axis_evaluator.py:379-380（構築）、multi_axis_evaluator.py:404（保存） | `{"remote": "true", "flex_time": "true"}` |
| `career_path_pref` | JSONB | キャリアパスの好み（JSON） | multi_axis_evaluator.py:381-382（構築）、multi_axis_evaluator.py:405（保存） | `{"growth_opportunities": "true", "training": "true"}` |
| `created_at` | TIMESTAMP | レコード作成日時 | multi_axis_evaluator.py:385（自動設定） | `2024-01-01 14:40:00` |
| `updated_at` | TIMESTAMP | レコード更新日時 | multi_axis_evaluator.py:398（ON CONFLICT時更新） | `2024-01-01 16:20:00` |

**UNIQUE制約:** user_id - 1ユーザーに1プロファイル

**使用フロー:**
1. プロファイル更新（multi_axis_evaluator.py:334-415）:
   ```python
   # 回答履歴からテキスト生成
   preference_text = build_preference_text(user_id)
   
   # エンベディング生成
   embedding = generate_preference_embedding(user_id)
   
   # カテゴリ別に好みを整理
   company_culture_pref = {...}
   work_flexibility_pref = {...}
   career_path_pref = {...}
   
   # DBに保存（UPSERT）
   ```

2. マッチングスコア計算（multi_axis_evaluator.py:418-490）:
   - user_preferencesとjob_attributesを取得
   - 各カテゴリごとに辞書を比較
   - 一致度を計算

---

## 11. user_interaction_summary（ビュー）

ユーザーの行動サマリーを集計するビュー（実テーブルではない）。

**想定カラム:**
- `user_id`: ユーザーID
- `total_clicks`: 総クリック数
- `total_favorites`: 総お気に入り数
- `total_applies`: 総応募数
- `total_views`: 総閲覧数
- `last_interaction`: 最終行動日時

**使用箇所:**
- tracking.py:176-192: `get_user_interaction_summary(user_id)`
- ユーザーのダッシュボード表示などで活用

---

## データの流れ（全体像）

### ユーザー登録〜推薦までのフロー

```
1. ユーザー登録（Step1）
   personal_date ← 個人情報
   user_profile ← 空レコード作成

2. 希望条件入力（Step2）
   user_profile ← job_title, location_prefecture, salary_min

3. チャット開始
   chat_history ← ユーザーメッセージ
   ↓
   AIが意図抽出
   ↓
   user_profile ← 意図から抽出した条件を更新
   ↓
   動的質問生成
   ↓
   dynamic_questions ← 質問選択
   ↓
   user_question_responses ← ユーザー回答保存
   ↓
   user_preferences ← プロファイル更新

4. 推薦実行
   company_profile ← 基本条件でフィルタリング
   ↓
   user_interactions ← 協調フィルタリング（類似ユーザー検索）
   ↓
   job_attributes + user_preferences ← 多軸マッチング
   ↓
   embedding ← コンテンツベース類似度計算
   ↓
   ハイブリッドスコア計算
   ↓
   推薦結果を表示

5. ユーザー行動
   user_interactions ← クリック、お気に入り、応募を記録
   company_profile ← カウンター更新
   dynamic_questions ← effectiveness_score更新
```

---

## まとめ

このシステムは、以下の特徴を持つ高度な求人マッチングプラットフォームです：

1. **ユーザー管理**: personal_date + user_profile
2. **企業・求人管理**: company_date + company_profile
3. **行動追跡**: user_interactions（クリック、お気に入り、応募）
4. **会話履歴**: chat_history（ユーザーとAIの対話）
5. **動的質問システム**: dynamic_questions + user_question_responses
6. **多軸評価**: job_attributes + user_preferences
7. **ハイブリッド推薦**: 協調フィルタリング + コンテンツベース + 多軸マッチング

各テーブルが連携し、ユーザーの行動や回答からプロファイルを動的に更新しながら、最適な求人を推薦するシステムとなっています。
