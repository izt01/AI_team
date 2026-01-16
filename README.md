# FastAPI Job Matching System

## プロジェクト構成

```
fastapi_job_matching/
├── main.py                          # メインアプリケーション（全サービス統合）
├── requirements.txt                 # Python依存パッケージ
├── .env.example                     # 環境変数サンプル
├── config/
│   └── database.py                 # DB接続設定
├── models/
│   ├── user.py                     # ユーザー関連モデル
│   ├── job.py                      # 求人関連モデル
│   └── conversation.py             # 会話関連モデル
├── schemas/
│   ├── user.py                     # ユーザーAPIスキーマ
│   ├── job.py                      # 求人APIスキーマ
│   └── matching.py                 # マッチングAPIスキーマ
├── services/
│   ├── auth_service.py             # 認証サービス
│   ├── matching_service.py         # マッチングサービス
│   ├── conversation_service.py     # 会話管理サービス
│   ├── enrichment_service.py       # エンリッチメントサービス
│   ├── scout_service.py            # スカウトサービス
│   └── analytics_service.py        # 分析サービス
├── api/
│   ├── user_api.py                 # ユーザー向けAPI
│   ├── company_api.py              # 企業向けAPI
│   └── admin_api.py                # 管理者向けAPI
└── utils/
    ├── ai_utils.py                 # AI関連ユーティリティ
    ├── scoring_utils.py            # スコアリングユーティリティ
    └── helpers.py                  # 汎用ヘルパー

```

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、必要な値を設定してください。

```bash
cp .env.example .env
```

### 3. データベースのセットアップ

PostgreSQLデータベースを作成し、`.env` に接続情報を設定してください。

## 起動方法

### 開発環境での起動

```bash
# 方法1: uvicornで直接起動
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 方法2: Pythonスクリプトとして起動
python main.py
```

### 本番環境での起動

```bash
# gunicornを使用（ワーカー4つ）
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## API エンドポイント

### ユーザー向けAPI (`/api/user`)

- `POST /api/user/register` - ユーザー登録
- `POST /api/user/login` - ログイン
- `GET /api/user/profile` - プロフィール取得
- `PUT /api/user/profile` - プロフィール更新
- `POST /api/user/chat` - 求人チャット
- `GET /api/user/recommendations` - おすすめ求人取得

### 企業向けAPI (`/api/company`)

- `POST /api/company/register` - 企業登録
- `POST /api/company/login` - ログイン
- `POST /api/company/jobs` - 求人登録
- `GET /api/company/jobs` - 求人一覧取得
- `PUT /api/company/jobs/{job_id}` - 求人更新
- `POST /api/company/scout/search` - スカウト候補検索
- `POST /api/company/scout/send` - スカウト送信
- `GET /api/company/enrichment/requests` - エンリッチメント要求一覧

### 管理者向けAPI (`/api/admin`)

- `GET /api/admin/stats` - システム統計
- `GET /api/admin/trends` - トレンド分析
- `POST /api/admin/data/seed` - ダミーデータ生成

## ドキュメント

起動後、以下のURLでインタラクティブなAPIドキュメントを確認できます：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 開発ガイド

### 新しいエンドポイントの追加

1. `schemas/` に必要なPydanticモデルを定義
2. `services/` にビジネスロジックを実装
3. `api/` にエンドポイントを追加
4. `main.py` でルーターを登録

### テストの実行

```bash
pytest tests/
```

## トラブルシューティング

### データベース接続エラー

- `.env` ファイルのDB接続情報を確認
- PostgreSQLサービスが起動しているか確認

### OpenAI APIエラー

- `.env` ファイルの `OPENAI_API_KEY` を確認
- APIクォータを確認

## ライセンス

Proprietary
