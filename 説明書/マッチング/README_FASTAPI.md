# FastAPI版 AI求人マッチングシステム

FlaskからFastAPIへ移行したバージョンです。

## 🚀 セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements_fastapi.txt
```

### 2. 環境変数の設定

`.env` ファイルを作成し、以下を設定してください：

```env
OPENAI_API_KEY=your_openai_api_key_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=jobmatch
DB_USER=devuser
DB_PASSWORD=devpass
FLASK_SECRET_KEY=your_secret_key_here
```

### 3. データベースの準備

PostgreSQLデータベースが既に設定されていることを確認してください。

## 📦 起動方法

### ユーザー向けアプリ（ポート5000）

```bash
python main.py
```

または

```bash
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

アクセス: http://localhost:5000

### 企業向けアプリ（ポート5001）

```bash
python main_company.py
```

または

```bash
uvicorn main_company:company_app --host 0.0.0.0 --port 5001 --reload
```

アクセス: http://localhost:5001

## 🔄 FlaskからFastAPIへの主な変更点

### 1. アプリケーション初期化

**Flask:**
```python
app = Flask(__name__)
app.secret_key = "supersecretkey"
```

**FastAPI:**
```python
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")
```

### 2. ルート定義

**Flask:**
```python
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # POST処理
    return render_template("login.html")
```

**FastAPI:**
```python
@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    # POST処理
```

### 3. フォームデータの取得

**Flask:**
```python
email = request.form["email"]
password = request.form["password"]
```

**FastAPI:**
```python
async def login_post(
    email: str = Form(...),
    password: str = Form(...)
):
    # emailとpasswordが自動的に注入される
```

### 4. セッション管理

**Flask:**
```python
session["user_id"] = user_id
user_id = session.get("user_id")
```

**FastAPI:**
```python
request.session["user_id"] = user_id
user_id = request.session.get("user_id")
```

### 5. リダイレクト

**Flask:**
```python
return redirect(url_for("chat_page"))
```

**FastAPI:**
```python
return RedirectResponse(url="/chat", status_code=302)
```

### 6. JSONレスポンス

**Flask:**
```python
return jsonify({"response": message})
```

**FastAPI:**
```python
return JSONResponse({"response": message})
# または
return {"response": message}  # FastAPIが自動的にJSONに変換
```

### 7. テンプレートレンダリング

**Flask:**
```python
return render_template("chat.html", message=message)
```

**FastAPI:**
```python
return templates.TemplateResponse(
    "chat.html",
    {"request": request, "message": message}
)
```

## 📝 APIドキュメント

FastAPIは自動的にAPIドキュメントを生成します：

- **Swagger UI**: http://localhost:5000/docs
- **ReDoc**: http://localhost:5000/redoc

## 🔧 開発モード

`--reload` オプションを使うと、コード変更時に自動的に再起動されます：

```bash
uvicorn main:app --reload
```

## 🎯 FastAPIの利点

1. **高速**: FlaskやDjangoより高速（Starlette + Pydanticベース）
2. **型ヒント**: Pythonの型ヒントを活用した自動バリデーション
3. **自動ドキュメント**: Swagger/ReDocが自動生成
4. **非同期サポート**: async/awaitネイティブサポート
5. **依存性注入**: Dependsによる強力な依存性注入システム
6. **モダンなPython**: Python 3.7+の機能を活用

## 📚 参考リンク

- [FastAPI公式ドキュメント](https://fastapi.tiangolo.com/)
- [Uvicornドキュメント](https://www.uvicorn.org/)
- [Pydanticドキュメント](https://docs.pydantic.dev/)

## ⚠️ 注意事項

### セッション管理

FastAPIではFlaskのようなビルトインセッションがないため、`SessionMiddleware`を使用しています。
本番環境では以下を検討してください：

1. Redis + `fastapi-sessions`
2. JWT認証
3. OAuth2 / OpenID Connect

### テンプレート

Jinja2テンプレートはFlaskと同じものを使用できますが、以下の点に注意：

- `url_for()`は使えないため、直接URLを指定
- `{{ request }}` をテンプレートコンテキストに渡す必要がある

### CORS設定（API利用時）

フロントエンドと分離する場合は、CORSを設定してください：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🐛 トラブルシューティング

### ポートが既に使用中

```bash
# ポート使用状況を確認
lsof -i :5000

# プロセスを停止
kill -9 <PID>
```

### テンプレートが見つからない

テンプレートディレクトリが正しく設定されているか確認：

```python
templates = Jinja2Templates(directory="templates")
```

### セッションが保存されない

`SessionMiddleware`が正しく追加されているか確認してください。
