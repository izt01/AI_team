# JobMatch AI - データベースセットアップガイド

このディレクトリには、JobMatch AIシステムのデータベース構築に必要なファイルが含まれています。

## 📁 ファイル一覧

| ファイル名 | 説明 |
|-----------|------|
| `database_schema.md` | データベーススキーマの詳細ドキュメント |
| `create_tables.sql` | テーブル作成SQLスクリプト |
| `insert_dummy_data.py` | ダミーデータ挿入Pythonスクリプト |
| `db_config.py` | データベース接続設定モジュール（既存） |

---

## 🚀 セットアップ手順

### 1. 前提条件

- PostgreSQL 12以降がインストールされていること
- Python 3.8以降がインストールされていること
- 必要なPythonパッケージがインストールされていること

```bash
pip install psycopg2-binary python-dotenv werkzeug
```

### 2. データベース作成

PostgreSQLにログインしてデータベースを作成します。

```bash
# PostgreSQLに接続
psql -U postgres

# データベースとユーザーを作成
CREATE DATABASE jobmatch;
CREATE USER devuser WITH PASSWORD 'devpass';
GRANT ALL PRIVILEGES ON DATABASE jobmatch TO devuser;
\q
```

### 3. 環境変数設定

`.env` ファイルを作成して、データベース接続情報を設定します。

```env
# データベース接続情報
DB_HOST=localhost
DB_PORT=5432
DB_NAME=jobmatch
DB_USER=devuser
DB_PASSWORD=devpass

# OpenAI API（チャット機能用）
OPENAI_API_KEY=your-api-key-here

# Flask セッション秘密鍵
FLASK_SECRET_KEY=your-secret-key-here
```

### 4. テーブル作成

2つの方法があります。

#### 方法A: SQLスクリプトを使用（推奨）

```bash
# PostgreSQLでSQLファイルを実行
psql -U devuser -d jobmatch -f create_tables.sql
```

#### 方法B: Pythonから実行

Pythonコード内でテーブルを作成する場合は、`tracking_evolved.py` の `create_tables_if_not_exist()` 関数が自動的に実行されます。

```python
from tracking_evolved import create_tables_if_not_exist

create_tables_if_not_exist()
```

### 5. ダミーデータ挿入

開発・テスト用のダミーデータを挿入します。

```bash
python insert_dummy_data.py
```

実行時に確認メッセージが表示されます：

```
⚠️  このスクリプトは全テーブルのデータをクリアして、
   ダミーデータを挿入します。

続行しますか？ (yes/no): yes
```

**注意:** このスクリプトは既存のデータを全て削除します。本番環境では実行しないでください。

### 6. データ確認

挿入されたデータを確認します。

```bash
# PostgreSQLに接続
psql -U devuser -d jobmatch

# データ確認
SELECT COUNT(*) FROM company_date;      -- 企業: 10社
SELECT COUNT(*) FROM company_profile;   -- 求人: 50件
SELECT COUNT(*) FROM personal_date;     -- ユーザー: 5名
SELECT COUNT(*) FROM user_profile;      -- プロフィール: 5件
```

---

## 📊 挿入されるダミーデータ

### 企業情報 (10社)

1. 株式会社テックイノベーション
2. デジタルソリューションズ株式会社
3. グローバルデザイン株式会社
4. 株式会社AIテクノロジーズ
5. クラウドシステムズ株式会社
6. 株式会社フィンテックソリューション
7. モバイルアプリケーションズ株式会社
8. 株式会社データアナリティクス
9. セキュリティソリューション株式会社
10. 株式会社ゲームスタジオ

### 求人情報 (50件)

各企業に5件ずつの求人が作成されます。職種例：

- Webエンジニア
- バックエンドエンジニア
- フロントエンドエンジニア
- データサイエンティスト
- UIUXデザイナー
- プロジェクトマネージャー
- インフラエンジニア
- QAエンジニア
- セキュリティエンジニア
- モバイルエンジニア

年収範囲: 400万円～1,100万円

### テストユーザー (5名)

| ユーザー名 | メールアドレス | パスワード | 希望職種 | 希望勤務地 | 希望年収 |
|-----------|--------------|-----------|----------|-----------|----------|
| 山田太郎 | yamada@example.com | password123 | Webエンジニア | 東京都 | 500万円 |
| 佐藤花子 | sato@example.com | password123 | データサイエンティスト | 東京都 | 600万円 |
| 鈴木一郎 | suzuki@example.com | password123 | UIUXデザイナー | 大阪府 | 450万円 |
| 田中美咲 | tanaka@example.com | password123 | バックエンドエンジニア | 福岡県 | 550万円 |
| 高橋健太 | takahashi@example.com | password123 | プロジェクトマネージャー | 愛知県 | 700万円 |

---

## 🧪 テスト方法

### 1. データベース接続テスト

```bash
python db_config.py
```

成功すると以下のメッセージが表示されます：

```
✅ データベース接続成功: PostgreSQL 14.x
```

### 2. アプリケーションの起動

```bash
python main_evolved_complete.py
```

ブラウザで `http://localhost:5000` にアクセスして、テストユーザーでログインできます。

---

## 🗄️ データベース構造

詳細なスキーマ情報は `database_schema.md` を参照してください。

### 主要テーブル

1. **personal_date** - ユーザー個人情報
2. **user_profile** - ユーザー希望条件
3. **company_date** - 企業情報
4. **company_profile** - 求人情報
5. **user_sessions** - セッション管理
6. **conversation_turns** - 会話ターン記録
7. **user_insights** - ユーザー洞察蓄積
8. **conversation_sessions** - 会話セッションサマリー
9. **score_history** - スコア履歴
10. **user_interactions** - ユーザー行動追跡
11. **chat_history** - チャット履歴

---

## 🔧 トラブルシューティング

### エラー: "relation does not exist"

テーブルが作成されていません。`create_tables.sql` を実行してください。

```bash
psql -U devuser -d jobmatch -f create_tables.sql
```

### エラー: "FATAL: database 'jobmatch' does not exist"

データベースが作成されていません。PostgreSQLで作成してください。

```sql
CREATE DATABASE jobmatch;
```

### エラー: "password authentication failed"

`.env` ファイルのデータベース接続情報を確認してください。

### ダミーデータが挿入されない

1. テーブルが正しく作成されているか確認
2. `.env` ファイルの設定を確認
3. PostgreSQLサービスが起動しているか確認

---

## 📝 カスタマイズ

### ダミーデータの量を変更

`insert_dummy_data.py` を編集してください：

```python
# 各企業に5件ずつ求人を作成 → 10件に変更
for i in range(10):  # 5 → 10
    ...
```

### 追加のテストユーザー作成

`insert_dummy_data.py` の `users` リストに追加してください：

```python
users = [
    ...,
    {
        'user_id': 6,
        'name': '新規ユーザー',
        'email': 'newuser@example.com',
        ...
    }
]
```

---

## ⚠️ 注意事項

1. **本番環境での使用について**
   - `insert_dummy_data.py` は開発・テスト専用です
   - 本番環境では絶対に実行しないでください（全データが削除されます）

2. **パスワードのセキュリティ**
   - ダミーデータのパスワードは全て `password123` です
   - 本番環境では必ず安全なパスワードを使用してください

3. **データベース権限**
   - 本番環境では適切な権限設定を行ってください
   - 開発環境の設定をそのまま使用しないでください

---

## 📚 参考資料

- [PostgreSQL公式ドキュメント](https://www.postgresql.org/docs/)
- [psycopg2ドキュメント](https://www.psycopg.org/docs/)
- [FastAPIドキュメント](https://fastapi.tiangolo.com/)
