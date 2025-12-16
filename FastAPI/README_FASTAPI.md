# AI求人マッチングシステム - FastAPI版

Flask版をFastAPIに変換した求人マッチングシステムです。各機能をRESTful APIとして提供します。

## 主な機能

### 1. 認証機能（`/api/auth`）
- ユーザー登録・ログイン
- 企業登録・ログイン

### 2. ユーザー管理（`/api/users`）
- ユーザープロファイル取得・更新
- 希望条件管理

### 3. 企業管理（`/api/companies`）
- 企業情報取得
- 求人数統計

### 4. 求人管理（`/api/jobs`）
- 求人登録・取得・一覧・削除
- 自動エンベディング生成
- フィルタリング・検索

### 5. チャット機能（`/api/chat`）
- AIチャットボット
- 意図抽出
- チャット履歴管理

### 6. 推薦システム（`/api/recommendations`）
- ハイブリッド推薦（協調フィルタリング + コンテンツベース）
- 協調フィルタリング推薦
- コンテンツベース推薦

### 7. 行動追跡（`/api/interactions`）
- クリック・閲覧・お気に入り・応募の記録
- お気に入り管理
- 行動サマリー

### 8. 動的質問（`/api/questions`）
- AI質問生成
- 質問への回答保存
- 回答履歴管理

## プロジェクト構成

```
.
├── main.py                          # メインアプリケーション
├── requirements_fastapi.txt         # 依存パッケージ
├── routers/                         # APIルーター
│   ├── __init__.py
│   ├── auth_router.py              # 認証API
│   ├── user_router.py              # ユーザーAPI
│   ├── company_router.py           # 企業API
│   ├── job_router.py               # 求人API
│   ├── chat_router.py              # チャットAPI
│   ├── recommendation_router.py    # 推薦API
│   ├── interaction_router.py       # 行動追跡API
│   └── question_router.py          # 動的質問API
├── models/                          # Pydanticモデル
│   ├── __init__.py
│   ├── auth_models.py              # 認証関連モデル
│   └── api_models.py               # API関連モデル
├── db_config.py                     # データベース設定
├── tracking.py                      # 行動追跡モジュール
├── dynamic_questions.py             # 動的質問モジュール
├── hybrid_recommender.py            # 推薦システムモジュール
└── multi_axis_evaluator.py         # 多軸評価モジュール
```

## セットアップ

### 1. 環境変数設定

`.env`ファイルを作成します：

```bash
# OpenAI API
OPENAI_API_KEY=sk-proj-...

# データベース
DB_HOST=localhost
DB_PORT=5432
DB_NAME=jobmatch
DB_USER=devuser
DB_PASSWORD=devpass
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements_fastapi.txt
```

### 3. データベースのセットアップ

PostgreSQLデータベースを作成し、必要なテーブルを作成します。

### 4. アプリケーションの起動

```bash
# 開発環境（ホットリロード有効）
python main.py

# または
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 本番環境
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API ドキュメント

アプリケーション起動後、以下のURLでインタラクティブなAPIドキュメントにアクセスできます：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## エンドポイント一覧

### 認証（`/api/auth`）

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | `/api/auth/register/user` | ユーザー登録 |
| POST | `/api/auth/login/user` | ユーザーログイン |
| POST | `/api/auth/register/company` | 企業登録 |
| POST | `/api/auth/login/company` | 企業ログイン |

### ユーザー（`/api/users`）

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | `/api/users/{user_id}` | ユーザー情報取得 |
| GET | `/api/users/{user_id}/profile` | プロファイル取得 |
| PUT | `/api/users/{user_id}/profile` | プロファイル更新 |

### 企業（`/api/companies`）

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | `/api/companies/{company_id}` | 企業情報取得 |
| GET | `/api/companies/{company_id}/jobs/count` | 求人数取得 |

### 求人（`/api/jobs`）

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | `/api/jobs/` | 求人登録 |
| GET | `/api/jobs/{job_id}` | 求人詳細取得 |
| GET | `/api/jobs/` | 求人一覧取得（ページネーション付き） |
| DELETE | `/api/jobs/{job_id}` | 求人削除 |

### チャット（`/api/chat`）

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | `/api/chat/message` | メッセージ送信 |
| GET | `/api/chat/history/{user_id}` | チャット履歴取得 |
| DELETE | `/api/chat/history/{user_id}/session/{session_id}` | セッション削除 |

### 推薦（`/api/recommendations`）

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | `/api/recommendations/hybrid` | ハイブリッド推薦 |
| GET | `/api/recommendations/collaborative/{user_id}` | 協調フィルタリング推薦 |
| GET | `/api/recommendations/content-based/{user_id}` | コンテンツベース推薦 |

### 行動追跡（`/api/interactions`）

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | `/api/interactions/track` | 行動記録 |
| POST | `/api/interactions/favorites/add` | お気に入り追加 |
| DELETE | `/api/interactions/favorites/remove` | お気に入り削除 |
| GET | `/api/interactions/favorites/{user_id}` | お気に入り一覧 |
| GET | `/api/interactions/favorites/{user_id}/check/{job_id}` | お気に入り確認 |
| POST | `/api/interactions/apply` | 応募記録 |
| GET | `/api/interactions/apply/{user_id}/check/{job_id}` | 応募確認 |
| GET | `/api/interactions/summary/{user_id}` | 行動サマリー |

### 動的質問（`/api/questions`）

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | `/api/questions/all` | 全質問取得 |
| GET | `/api/questions/{question_id}` | 質問詳細取得 |
| GET | `/api/questions/key/{question_key}` | 質問取得（キー指定） |
| GET | `/api/questions/next/{user_id}` | 次の質問取得 |
| POST | `/api/questions/answer` | 回答保存 |
| GET | `/api/questions/responses/{user_id}` | 回答一覧取得 |
| POST | `/api/questions/generate` | 質問生成（管理者用） |
| PUT | `/api/questions/{question_id}/mark-effective` | 質問を有効としてマーク |

## 使用例

### ユーザー登録とログイン

```bash
# ユーザー登録
curl -X POST "http://localhost:8000/api/auth/register/user" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "山田太郎",
    "email": "yamada@example.com",
    "password": "password123",
    "birth_day": "1990-01-01"
  }'

# ログイン
curl -X POST "http://localhost:8000/api/auth/login/user" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "yamada@example.com",
    "password": "password123"
  }'
```

### 求人検索

```bash
# 求人一覧取得（東京都、年収500万円以上）
curl "http://localhost:8000/api/jobs/?location=東京都&salary_min=500&page=1&page_size=20"
```

### ハイブリッド推薦

```bash
# ユーザーID=1への推薦
curl -X POST "http://localhost:8000/api/recommendations/hybrid" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "top_k": 10
  }'
```

### お気に入り追加

```bash
# ユーザーID=1が求人IDをお気に入りに追加
curl -X POST "http://localhost:8000/api/interactions/favorites/add?user_id=1&job_id=550e8400-e29b-41d4-a716-446655440000"
```

## Flask版からの変更点

1. **非同期処理**: 全てのエンドポイントを`async def`に変更
2. **型安全性**: Pydanticモデルによる入力検証
3. **自動ドキュメント**: Swagger UIとReDocによるAPI仕様書自動生成
4. **エラーハンドリング**: HTTPExceptionによる統一的なエラー処理
5. **依存性注入**: FastAPIの依存性注入機能を活用可能
6. **パフォーマンス**: uvicornによる高速な非同期処理

## 今後の拡張

- [ ] JWT認証の実装
- [ ] レート制限の追加
- [ ] WebSocket対応（リアルタイムチャット）
- [ ] キャッシュ機能（Redis）
- [ ] 非同期タスクキュー（Celery）
- [ ] Docker化
- [ ] CI/CDパイプライン

## ライセンス

MIT License