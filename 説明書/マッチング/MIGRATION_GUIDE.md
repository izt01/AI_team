# Flask vs FastAPI 移行ガイド

## 📊 比較表

| 機能 | Flask | FastAPI |
|------|-------|---------|
| **アプリ初期化** | `Flask(__name__)` | `FastAPI()` |
| **ルート定義** | `@app.route()` | `@app.get()`, `@app.post()` |
| **非同期サポート** | 限定的 | ネイティブサポート |
| **型チェック** | なし | Pydanticによる自動バリデーション |
| **パフォーマンス** | 標準 | 高速（Starlette基盤） |
| **APIドキュメント** | 手動 | 自動生成（Swagger/ReDoc） |
| **依存性注入** | なし | `Depends()` |
| **フォーム処理** | `request.form` | `Form(...)` パラメータ |
| **JSON処理** | `jsonify()` | 自動シリアライズ |
| **テンプレート** | Flask-Jinja2 | Jinja2（直接） |
| **セッション** | ビルトイン | ミドルウェア必要 |
| **エラーハンドリング** | `@app.errorhandler()` | `HTTPException` |

## 🔄 コード変換例

### 1. 基本的なGETエンドポイント

**Flask:**
```python
@app.route("/")
def index():
    return render_template("index.html")
```

**FastAPI:**
```python
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
```

### 2. POSTエンドポイント

**Flask:**
```python
@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]
    # 処理
    return redirect(url_for("dashboard"))
```

**FastAPI:**
```python
@app.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...)
):
    # 処理
    return RedirectResponse(url="/dashboard", status_code=302)
```

### 3. JSONレスポンス

**Flask:**
```python
@app.route("/api/data")
def get_data():
    data = {"message": "Hello"}
    return jsonify(data)
```

**FastAPI:**
```python
@app.get("/api/data")
async def get_data():
    return {"message": "Hello"}
    # または
    # return JSONResponse({"message": "Hello"})
```

### 4. セッション管理

**Flask:**
```python
from flask import session

@app.route("/set_session")
def set_session():
    session["user_id"] = 123
    return "Session set"

@app.route("/get_session")
def get_session():
    user_id = session.get("user_id")
    return f"User ID: {user_id}"
```

**FastAPI:**
```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(SessionMiddleware, secret_key="secret")

@app.get("/set_session")
async def set_session(request: Request):
    request.session["user_id"] = 123
    return {"message": "Session set"}

@app.get("/get_session")
async def get_session(request: Request):
    user_id = request.session.get("user_id")
    return {"user_id": user_id}
```

### 5. 認証チェック（デコレータ vs 依存性注入）

**Flask:**
```python
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")
```

**FastAPI:**
```python
from fastapi import Depends, HTTPException

def require_login(request: Request) -> int:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    return user_id

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user_id: int = Depends(require_login)
):
    return templates.TemplateResponse("dashboard.html", {"request": request})
```

### 6. エラーハンドリング

**Flask:**
```python
@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500
```

**FastAPI:**
```python
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return HTMLResponse(content=str(exc.detail), status_code=exc.status_code)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)
```

### 7. ファイルアップロード

**Flask:**
```python
from werkzeug.utils import secure_filename

@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return "File uploaded"
```

**FastAPI:**
```python
from fastapi import File, UploadFile
import shutil

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    with open(f"uploads/{file.filename}", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename}
```

### 8. データベース接続（依存性注入の活用）

**Flask:**
```python
def get_db():
    conn = psycopg2.connect(...)
    return conn

@app.route("/users")
def get_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(users)
```

**FastAPI:**
```python
from typing import Generator
from fastapi import Depends

def get_db() -> Generator:
    conn = psycopg2.connect(...)
    try:
        yield conn
    finally:
        conn.close()

@app.get("/users")
async def get_users(conn = Depends(get_db)):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    cur.close()
    return users
```

## 📝 移行チェックリスト

- [ ] `requirements.txt` を `requirements_fastapi.txt` に更新
- [ ] `Flask` → `FastAPI` にインポート変更
- [ ] `@app.route()` → `@app.get()`, `@app.post()` に変更
- [ ] `request.form` → `Form(...)` パラメータに変更
- [ ] `session` → `request.session` に変更
- [ ] `url_for()` → 直接URLパスに変更
- [ ] `redirect()` → `RedirectResponse()` に変更
- [ ] `jsonify()` → 辞書を直接returnまたは`JSONResponse()`
- [ ] `render_template()` → `templates.TemplateResponse()` に変更
- [ ] テンプレートに `{"request": request}` を渡す
- [ ] `SessionMiddleware` を追加
- [ ] エラーハンドラを `@app.exception_handler()` に変更
- [ ] 認証デコレータを `Depends()` に変更
- [ ] 関数を `async def` に変更（推奨）

## 🎯 移行のベストプラクティス

### 1. 段階的移行

1. まず小さなエンドポイントから移行
2. テストを書いて動作確認
3. 徐々に大きなエンドポイントを移行

### 2. 型ヒントの活用

FastAPIの強みを活かすため、型ヒントを積極的に使用：

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    age: int

@app.post("/users")
async def create_user(user: User):
    # userは自動的にバリデーションされる
    return {"message": f"User {user.name} created"}
```

### 3. 依存性注入の活用

共通処理は依存性注入で再利用：

```python
async def get_current_user(request: Request) -> User:
    # 認証チェック
    token = request.headers.get("Authorization")
    # ユーザー情報を取得
    return user

@app.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user
```

### 4. 非同期処理の活用

I/O処理（DB、API呼び出し）は非同期で：

```python
import httpx

@app.get("/external_api")
async def call_external_api():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()
```

## 🚨 注意点

### 1. url_for()は使えない

FlaskのようにURLを逆引きする機能はありません。直接URLを指定してください。

### 2. Blueprintの代替

FastAPIでは`APIRouter`を使用：

**Flask:**
```python
from flask import Blueprint

api = Blueprint('api', __name__)

@api.route('/users')
def get_users():
    pass

app.register_blueprint(api, url_prefix='/api')
```

**FastAPI:**
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
async def get_users():
    pass

app.include_router(router, prefix="/api")
```

### 3. before_requestの代替

**Flask:**
```python
@app.before_request
def before_request():
    # リクエスト前の処理
    pass
```

**FastAPI:**
```python
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # リクエスト前の処理
    response = await call_next(request)
    # レスポンス後の処理
    return response
```

## 📚 学習リソース

- [FastAPI公式チュートリアル](https://fastapi.tiangolo.com/tutorial/)
- [FlaskからFastAPIへの移行ガイド](https://fastapi.tiangolo.com/alternatives/)
- [Pydantic入門](https://docs.pydantic.dev/latest/)
