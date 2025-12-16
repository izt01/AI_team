# FastAPI化プロジェクト 構成一覧

## 作成したファイル

### メインファイル
- `main.py` - FastAPIアプリケーションのエントリーポイント

### ルーター（APIエンドポイント）
- `routers/__init__.py` - ルーターモジュールの初期化
- `routers/auth_router.py` - 認証API（ユーザー・企業登録/ログイン）
- `routers/user_router.py` - ユーザーAPI（プロファイル管理）
- `routers/company_router.py` - 企業API（企業情報管理）
- `routers/job_router.py` - 求人API（求人CRUD操作）
- `routers/chat_router.py` - チャットAPI（AIチャットボット）
- `routers/recommendation_router.py` - 推薦API（3種類の推薦アルゴリズム）
- `routers/interaction_router.py` - 行動追跡API（お気に入り、応募等）
- `routers/question_router.py` - 動的質問API（質問生成・回答管理）

### モデル（Pydanticスキーマ）
- `models/__init__.py` - モデルモジュールの初期化
- `models/auth_models.py` - 認証関連のリクエスト/レスポンスモデル
- `models/api_models.py` - API全般のリクエスト/レスポンスモデル

### その他
- `requirements_fastapi.txt` - FastAPI版の依存パッケージ
- `README_FASTAPI.md` - FastAPI版の詳細ドキュメント
- `PROJECT_STRUCTURE.md` - このファイル（プロジェクト構成）

## 既存ファイル（再利用）

以下のFlask版のモジュールはそのまま再利用されます：

- `db_config.py` - データベース接続設定
- `tracking.py` - ユーザー行動追跡モジュール
- `dynamic_questions.py` - 動的質問生成モジュール
- `hybrid_recommender.py` - ハイブリッド推薦システム
- `multi_axis_evaluator.py` - 多軸評価システム

## API構成

### 1. 認証API (`/api/auth`)

**機能:**
- ユーザー登録・ログイン
- 企業登録・ログイン
- パスワードハッシュ化（Werkzeug）

**エンドポイント:**
- `POST /api/auth/register/user` - ユーザー登録
- `POST /api/auth/login/user` - ユーザーログイン
- `POST /api/auth/register/company` - 企業登録
- `POST /api/auth/login/company` - 企業ログイン

### 2. ユーザーAPI (`/api/users`)

**機能:**
- ユーザー基本情報取得
- プロファイル取得・更新（希望職種、勤務地、年収等）

**エンドポイント:**
- `GET /api/users/{user_id}` - ユーザー情報取得
- `GET /api/users/{user_id}/profile` - プロファイル取得
- `PUT /api/users/{user_id}/profile` - プロファイル更新

### 3. 企業API (`/api/companies`)

**機能:**
- 企業情報取得
- 企業の求人数統計

**エンドポイント:**
- `GET /api/companies/{company_id}` - 企業情報取得
- `GET /api/companies/{company_id}/jobs/count` - 求人数取得

### 4. 求人API (`/api/jobs`)

**機能:**
- 求人登録（自動エンベディング生成）
- 求人詳細取得
- 求人一覧取得（ページネーション、フィルタリング）
- 求人削除

**エンドポイント:**
- `POST /api/jobs/` - 求人登録
- `GET /api/jobs/{job_id}` - 求人詳細取得
- `GET /api/jobs/` - 求人一覧取得
- `DELETE /api/jobs/{job_id}` - 求人削除

### 5. チャットAPI (`/api/chat`)

**機能:**
- AIチャットボット
- 意図抽出（OpenAI GPT-4）
- チャット履歴管理

**エンドポイント:**
- `POST /api/chat/message` - メッセージ送信
- `GET /api/chat/history/{user_id}` - チャット履歴取得
- `DELETE /api/chat/history/{user_id}/session/{session_id}` - セッション削除

### 6. 推薦API (`/api/recommendations`)

**機能:**
- ハイブリッド推薦（協調フィルタリング + コンテンツベース）
- 協調フィルタリング推薦（類似ユーザーベース）
- コンテンツベース推薦（エンベディング類似度）

**エンドポイント:**
- `POST /api/recommendations/hybrid` - ハイブリッド推薦
- `GET /api/recommendations/collaborative/{user_id}` - 協調フィルタリング推薦
- `GET /api/recommendations/content-based/{user_id}` - コンテンツベース推薦

### 7. 行動追跡API (`/api/interactions`)

**機能:**
- ユーザー行動記録（クリック、閲覧、お気に入り、応募）
- お気に入り管理
- 応募管理
- 行動サマリー取得

**エンドポイント:**
- `POST /api/interactions/track` - 行動記録
- `POST /api/interactions/favorites/add` - お気に入り追加
- `DELETE /api/interactions/favorites/remove` - お気に入り削除
- `GET /api/interactions/favorites/{user_id}` - お気に入り一覧
- `GET /api/interactions/favorites/{user_id}/check/{job_id}` - お気に入り確認
- `POST /api/interactions/apply` - 応募記録
- `GET /api/interactions/apply/{user_id}/check/{job_id}` - 応募確認
- `GET /api/interactions/summary/{user_id}` - 行動サマリー

### 8. 動的質問API (`/api/questions`)

**機能:**
- AI質問生成（求人データから自動生成）
- 質問取得（全質問、次の質問）
- 回答保存・取得
- 質問の有効性評価

**エンドポイント:**
- `GET /api/questions/all` - 全質問取得
- `GET /api/questions/{question_id}` - 質問詳細取得
- `GET /api/questions/key/{question_key}` - 質問取得（キー指定）
- `GET /api/questions/next/{user_id}` - 次の質問取得
- `POST /api/questions/answer` - 回答保存
- `GET /api/questions/responses/{user_id}` - 回答一覧取得
- `POST /api/questions/generate` - 質問生成（管理者用）
- `PUT /api/questions/{question_id}/mark-effective` - 質問を有効としてマーク

## Flask版からFastAPI版への主な変更点

### 1. ルーティング
**Flask:**
```python
@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    ...
```

**FastAPI:**
```python
@router.get("/{user_id}")
async def get_user_info(user_id: int):
    ...
```

### 2. リクエスト検証
**Flask:**
```python
email = request.form["email"]
password = request.form["password"]
```

**FastAPI:**
```python
async def login_user(request: LoginRequest):
    email = request.email
    password = request.password
```

### 3. レスポンス型定義
**Flask:**
```python
return jsonify({"user_id": user_id, "email": email})
```

**FastAPI:**
```python
@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(user_id: int):
    return UserProfileResponse(**profile)
```

### 4. エラーハンドリング
**Flask:**
```python
return "エラーが発生しました", 500
```

**FastAPI:**
```python
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="エラーが発生しました"
)
```

## 起動方法

### 開発環境
```bash
# ホットリロード有効
python main.py

# または
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 本番環境
```bash
# ワーカープロセス4つで起動
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## APIドキュメント

起動後、以下のURLでインタラクティブなAPIドキュメントにアクセス可能：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 利点

1. **自動ドキュメント生成**: Swagger UIとReDocで即座にAPI仕様書が生成される
2. **型安全性**: Pydanticによる入力検証とシリアライゼーション
3. **パフォーマンス**: 非同期処理による高速化
4. **開発効率**: 自動補完とエラーチェックが充実
5. **テスト容易性**: TestClientによる簡単なテスト記述
6. **依存性注入**: クリーンなコード設計
7. **WebSocket対応**: リアルタイム通信が可能

## 次のステップ

- [ ] JWT認証の実装（現在は簡易的なトークン生成）
- [ ] レート制限の追加
- [ ] ミドルウェアの追加（ログ、CORS設定の詳細化）
- [ ] Docker化
- [ ] テストコードの作成
- [ ] CI/CDパイプラインの構築