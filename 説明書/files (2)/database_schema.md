# JobMatch AI - データベーススキーマ

## データベース名
`jobmatch`

---

## テーブル一覧

### 1. personal_date (ユーザー個人情報)
ユーザーの基本情報を管理するテーブル

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| id | INTEGER | PRIMARY KEY | レコードID |
| user_id | INTEGER | NOT NULL, UNIQUE | ユーザーID（idと同じ値） |
| email | VARCHAR(255) | NOT NULL, UNIQUE | メールアドレス |
| password_hash | VARCHAR(255) | NOT NULL | パスワードハッシュ |
| user_name | VARCHAR(100) | NOT NULL | ユーザー名 |
| birth_day | DATE | NULL | 生年月日 |
| phone_number | VARCHAR(20) | NULL | 電話番号 |
| address | TEXT | NULL | 住所 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新日時 |

---

### 2. user_profile (ユーザー希望条件プロフィール)
ユーザーの希望職種・勤務地・年収などを管理

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| id | SERIAL | PRIMARY KEY | レコードID |
| user_id | INTEGER | NOT NULL, UNIQUE | ユーザーID |
| job_title | VARCHAR(100) | NULL | 希望職種 |
| location_prefecture | VARCHAR(50) | NULL | 希望勤務地（都道府県） |
| salary_min | INTEGER | DEFAULT 0 | 希望最低年収（万円） |
| employment_type | VARCHAR(50) | NULL | 雇用形態（正社員/契約社員等） |
| work_hours | VARCHAR(100) | NULL | 勤務時間帯 |
| holiday_policy | VARCHAR(100) | NULL | 休日制度 |
| workplace_atmosphere | VARCHAR(100) | NULL | 職場の雰囲気 |
| remote | VARCHAR(50) | NULL | リモート勤務可否 |
| employee_benefits | TEXT | NULL | 福利厚生 |
| job_summary | TEXT | NULL | 業務内容 |
| skills | TEXT | NULL | スキル |
| certifications | TEXT | NULL | 資格・検定 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新日時 |

---

### 3. company_date (企業基本情報)
企業の基本情報を管理

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| id | SERIAL | PRIMARY KEY | レコードID |
| company_id | INTEGER | NOT NULL, UNIQUE | 企業ID |
| company_name | VARCHAR(200) | NOT NULL | 企業名 |
| industry | VARCHAR(100) | NULL | 業界 |
| employee_count | INTEGER | NULL | 従業員数 |
| founded_year | INTEGER | NULL | 設立年 |
| headquarters | VARCHAR(200) | NULL | 本社所在地 |
| website | VARCHAR(255) | NULL | ウェブサイト |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新日時 |

---

### 4. company_profile (求人情報)
企業が掲載する求人情報

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| id | SERIAL | PRIMARY KEY | 求人ID |
| company_id | INTEGER | NOT NULL | 企業ID（company_dateへの外部キー） |
| job_title | VARCHAR(100) | NOT NULL | 職種名 |
| location_prefecture | VARCHAR(50) | NOT NULL | 勤務地（都道府県） |
| location_city | VARCHAR(100) | NULL | 勤務地（市区町村） |
| salary_min | INTEGER | NOT NULL | 最低年収（万円） |
| salary_max | INTEGER | NOT NULL | 最高年収（万円） |
| employment_type | VARCHAR(50) | NULL | 雇用形態 |
| job_summary | TEXT | NULL | 仕事内容 |
| required_skills | TEXT | NULL | 必須スキル |
| preferred_skills | TEXT | NULL | 歓迎スキル |
| remote_option | VARCHAR(50) | NULL | リモートワーク（完全リモート可/ハイブリッド/なし） |
| remote_work | VARCHAR(50) | NULL | リモート勤務（別名カラム） |
| company_culture | TEXT | NULL | 企業文化・社風 |
| work_flexibility | VARCHAR(100) | NULL | 働き方の柔軟性 |
| benefits | TEXT | NULL | 福利厚生 |
| work_hours | VARCHAR(100) | NULL | 勤務時間 |
| holidays | VARCHAR(100) | NULL | 休日・休暇 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新日時 |

---

### 5. user_sessions (セッション管理)
チャットセッションのデータを保存（クッキー制限回避）

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| session_id | VARCHAR(100) | PRIMARY KEY | セッションID（UUID） |
| user_id | INTEGER | NULL | ユーザーID |
| session_data | JSONB | NULL | セッションデータ（候補リスト等） |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新日時 |

**session_data の構造例:**
```json
{
  "candidates": [...],
  "initial_candidate_count": 10,
  "conversation_turn": 0,
  "score_history": [],
  "accumulated_insights": {
    "explicit_preferences": {},
    "implicit_values": {},
    "pain_points": [],
    "keywords": []
  }
}
```

---

### 6. conversation_turns (会話ターン記録)
AIとの会話の各ターンを記録

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| id | SERIAL | PRIMARY KEY | レコードID |
| user_id | INTEGER | NOT NULL | ユーザーID |
| session_id | VARCHAR(100) | NOT NULL | セッションID |
| turn_number | INTEGER | NOT NULL | ターン番号（1-10） |
| user_message | TEXT | NULL | ユーザーの発言 |
| bot_message | TEXT | NULL | ボットの応答 |
| extracted_info | JSONB | NULL | 抽出された情報 |
| top_score | FLOAT | NULL | トップスコア |
| top_match_percentage | FLOAT | NULL | トップマッチ度（%） |
| candidate_count | INTEGER | NULL | 候補数 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 作成日時 |

**インデックス:**
- `idx_conversation_turns_session` ON (user_id, session_id)

---

### 7. user_insights (ユーザー洞察蓄積)
会話を通じて得られたユーザーの希望や価値観を蓄積

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| id | SERIAL | PRIMARY KEY | レコードID |
| user_id | INTEGER | NOT NULL | ユーザーID |
| session_id | VARCHAR(100) | NOT NULL | セッションID |
| insights | JSONB | NULL | 蓄積された洞察データ |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新日時 |

**制約:**
- UNIQUE(user_id, session_id)

**insights の構造例:**
```json
{
  "explicit_preferences": {
    "remote_work": "完全リモート希望",
    "learning_interest": "Python"
  },
  "implicit_values": {
    "work_life_balance": "重視"
  },
  "pain_points": ["長時間労働", "通勤時間"],
  "keywords": ["AI", "機械学習"],
  "confidence": 0.8
}
```

---

### 8. conversation_sessions (会話セッションサマリー)
各会話セッションの終了情報を記録

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| id | SERIAL | PRIMARY KEY | レコードID |
| user_id | INTEGER | NOT NULL | ユーザーID |
| session_id | VARCHAR(100) | NOT NULL, UNIQUE | セッションID |
| total_turns | INTEGER | NULL | 総ターン数 |
| end_reason | VARCHAR(50) | NULL | 終了理由 |
| final_match_percentage | FLOAT | NULL | 最終マッチ度 |
| presented_jobs | JSONB | NULL | 提示した求人IDリスト |
| ended_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 終了日時 |

**end_reason の値例:**
- `high_match`: 高マッチ達成
- `score_converged`: スコア収束
- `user_requested`: ユーザー要求
- `max_turns`: 最大ターン到達

---

### 9. score_history (スコア履歴)
各ターンでの求人スコアの変化を記録

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| id | SERIAL | PRIMARY KEY | レコードID |
| user_id | INTEGER | NOT NULL | ユーザーID |
| session_id | VARCHAR(100) | NOT NULL | セッションID |
| turn_number | INTEGER | NOT NULL | ターン番号 |
| job_id | VARCHAR(100) | NOT NULL | 求人ID |
| score | FLOAT | NULL | スコア |
| match_percentage | FLOAT | NULL | マッチ度（%） |
| score_details | JSONB | NULL | スコア詳細 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 作成日時 |

**インデックス:**
- `idx_score_history_session` ON (user_id, session_id, turn_number)

**score_details の構造例:**
```json
[
  ["リモートワーク一致", 15],
  ["希望年収範囲内", 10],
  ["スキルマッチ", 8]
]
```

---

### 10. user_interactions (ユーザー行動追跡)
ユーザーの求人に対する行動（クリック、お気に入り、応募）を記録

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| id | SERIAL | PRIMARY KEY | レコードID |
| user_id | INTEGER | NOT NULL | ユーザーID |
| job_id | UUID | NOT NULL | 求人ID |
| interaction_type | VARCHAR(20) | NOT NULL | 行動タイプ |
| metadata | JSONB | NULL | 追加情報 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 作成日時 |

**interaction_type の値:**
- `click`: クリック
- `favorite`: お気に入り
- `apply`: 応募

**インデックス:**
- (user_id, job_id, interaction_type)

---

### 11. chat_history (チャット履歴)
ユーザーとボットの全チャット履歴を保存

| カラム名 | データ型 | 制約 | 説明 |
|---------|---------|------|------|
| id | SERIAL | PRIMARY KEY | レコードID |
| user_id | INTEGER | NOT NULL | ユーザーID |
| session_id | VARCHAR(100) | NOT NULL | セッションID |
| sender | VARCHAR(10) | NOT NULL | 送信者（user/bot） |
| message | TEXT | NULL | メッセージ本文 |
| extracted_intent | JSONB | NULL | AIが抽出した意図 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 作成日時 |

---

## ER図（主要な関係）

```
personal_date (1) ----< (N) user_profile
personal_date (1) ----< (N) user_sessions
personal_date (1) ----< (N) conversation_turns
personal_date (1) ----< (N) user_interactions

company_date (1) ----< (N) company_profile

company_profile (1) ----< (N) user_interactions
company_profile (1) ----< (N) score_history
```

---

## 注意事項

1. **personal_date テーブルの id と user_id**
   - 同じ値を使用（新規登録時に `MAX(user_id) + 1` で設定）

2. **JSONB型カラム**
   - PostgreSQL の JSONB 型を使用
   - 柔軟なデータ構造の保存が可能

3. **セッション管理**
   - クッキーサイズ制限を回避するため、大きなデータは `user_sessions` テーブルに保存
   - セッションIDのみをクッキーに保持

4. **タイムスタンプ**
   - すべてのテーブルに `created_at` を設定
   - 更新可能なテーブルには `updated_at` も設定
