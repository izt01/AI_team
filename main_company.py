"""
企業向け求人管理システム FastAPI版
- 企業登録
- 求人登録・編集・削除
- 求人一覧・詳細表示
"""

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import os
from dotenv import load_dotenv
from db_config import get_db_conn
from typing import Optional

# 環境変数読み込み
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# FastAPIアプリケーション初期化
company_app = FastAPI(
    title="企業向け求人管理システム",
    description="求人の登録・管理を行うAPIシステム",
    version="2.0.0"
)

# セッション管理のミドルウェアを追加
company_app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("FLASK_SECRET_KEY", "company-secret")
)

# テンプレート設定
templates = Jinja2Templates(directory="templates_fastapi")


# --- エンベディング生成 ---
def get_embedding(text: str) -> list[float]:
    """テキストをエンベディング化"""
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding


def get_company_id(request: Request) -> Optional[str]:
    """セッションから企業IDを取得"""
    return request.session.get("company_id")


def require_company_login(request: Request) -> str:
    """企業ログイン必須の依存性"""
    company_id = get_company_id(request)
    if not company_id:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    return company_id


# --- ルート ---
@company_app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """トップページ - 企業登録画面へリダイレクト"""
    return RedirectResponse(url="/company/register", status_code=302)


@company_app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    """ログイン画面"""
    return templates.TemplateResponse("company_login.html", {"request": request})


@company_app.post("/login")
async def login_post(
    request: Request,
    email_address: str = Form(...),
    password: str = Form(...)
):
    """ログイン処理"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT password, company_id FROM company_date WHERE email=%s",
        (email_address,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row and check_password_hash(row[0], password):
        # ログイン成功
        request.session["company_email"] = email_address
        request.session["company_id"] = row[1]
        return RedirectResponse(url="/jobs", status_code=302)
    else:
        # ログイン失敗
        return templates.TemplateResponse(
            "company_login.html",
            {"request": request, "error": "メールアドレスまたはパスワードが違います"}
        )


@company_app.get("/logout")
async def logout(request: Request):
    """ログアウト"""
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)


@company_app.get("/company/register", response_class=HTMLResponse)
async def company_register_get(request: Request):
    """企業登録画面"""
    return templates.TemplateResponse("company_register.html", {"request": request})


@company_app.post("/company/register")
async def company_register_post(
    request: Request,
    company_name: str = Form(...),
    email_address: str = Form(...),
    password: str = Form(...),
    address: str = Form(""),
    phone_number: str = Form(""),
    website_url: str = Form("")
):
    """企業登録処理"""
    password_hash = generate_password_hash(password)
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO company_date (
                id, company_id, email, password, company_name,
                address, phone_number, website_url, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (email) DO NOTHING
        """, (
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            email_address,
            password_hash,
            company_name,
            address,
            phone_number,
            website_url
        ))
        
        conn.commit()
        
        # セッションに保存
        request.session["company_email"] = email_address
        
        # 登録した企業IDを取得
        cur.execute("SELECT company_id FROM company_date WHERE email = %s", (email_address,))
        result = cur.fetchone()
        if result:
            request.session["company_id"] = result[0]
        
        cur.close()
        conn.close()
        
        return RedirectResponse(url="/job/new", status_code=302)
        
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return templates.TemplateResponse(
            "company_register.html",
            {"request": request, "error": f"登録に失敗しました: {str(e)}"}
        )


@company_app.get("/job/new", response_class=HTMLResponse)
async def job_new_get(request: Request, company_id: str = Depends(require_company_login)):
    """求人登録画面"""
    return templates.TemplateResponse("job_form.html", {"request": request})


@company_app.post("/job/new")
async def job_new_post(
    request: Request,
    company_id: str = Depends(require_company_login),
    job_title: str = Form(...),
    salary_min: int = Form(...),
    salary_max: int = Form(...),
    bonus: str = Form(""),
    overtime: str = Form(""),
    workplace_atmosphere: str = Form("")
):
    """求人登録処理"""
    # 任意項目を intent_labels にまとめる
    labels = []
    if bonus:
        labels.append(bonus)
    if overtime:
        labels.append(overtime)
    if workplace_atmosphere:
        labels.append(workplace_atmosphere)
    intent_labels = ",".join(labels) if labels else None
    
    # エンベディング生成
    profile_text = " ".join([job_title, str(salary_min), str(salary_max), intent_labels or ""])
    embedding = get_embedding(profile_text)
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO company_profile (
                id, company_id, job_title, salary_min, salary_max,
                intent_labels, embedding, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            str(uuid.uuid4()),
            company_id,
            job_title,
            salary_min,
            salary_max,
            intent_labels,
            embedding
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return RedirectResponse(url="/jobs", status_code=302)
        
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return templates.TemplateResponse(
            "job_form.html",
            {"request": request, "error": f"登録に失敗しました: {str(e)}"}
        )


@company_app.get("/jobs", response_class=HTMLResponse)
async def job_list(request: Request, company_id: str = Depends(require_company_login)):
    """求人一覧"""
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT id, job_title, salary_min, salary_max, intent_labels, created_at
        FROM company_profile
        WHERE company_id = %s
        ORDER BY created_at DESC
    """, (company_id,))
    
    jobs = cur.fetchall()
    cur.close()
    conn.close()
    
    return templates.TemplateResponse(
        "job_list.html",
        {"request": request, "jobs": jobs}
    )


@company_app.get("/job/{job_id}", response_class=HTMLResponse)
async def job_detail(
    request: Request,
    job_id: str,
    company_id: str = Depends(require_company_login)
):
    """求人詳細"""
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT cp.*, cd.company_name
        FROM company_profile cp
        JOIN company_date cd ON cp.company_id = cd.company_id
        WHERE cp.id = %s AND cp.company_id = %s
    """, (job_id, company_id))
    
    job = cur.fetchone()
    cur.close()
    conn.close()
    
    if not job:
        raise HTTPException(status_code=404, detail="求人が見つかりません")
    
    return templates.TemplateResponse(
        "job_detail.html",
        {"request": request, "job": job}
    )


@company_app.get("/job/{job_id}/edit", response_class=HTMLResponse)
async def job_edit_get(
    request: Request,
    job_id: str,
    company_id: str = Depends(require_company_login)
):
    """求人編集画面"""
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT * FROM company_profile
        WHERE id = %s AND company_id = %s
    """, (job_id, company_id))
    
    job = cur.fetchone()
    cur.close()
    conn.close()
    
    if not job:
        raise HTTPException(status_code=404, detail="求人が見つかりません")
    
    return templates.TemplateResponse(
        "job_edit.html",
        {"request": request, "job": job}
    )


@company_app.post("/job/{job_id}/edit")
async def job_edit_post(
    request: Request,
    job_id: str,
    company_id: str = Depends(require_company_login),
    job_title: str = Form(...),
    salary_min: int = Form(...),
    salary_max: int = Form(...),
    bonus: str = Form(""),
    overtime: str = Form(""),
    workplace_atmosphere: str = Form("")
):
    """求人編集処理"""
    # 任意項目を intent_labels にまとめる
    labels = []
    if bonus:
        labels.append(bonus)
    if overtime:
        labels.append(overtime)
    if workplace_atmosphere:
        labels.append(workplace_atmosphere)
    intent_labels = ",".join(labels) if labels else None
    
    # エンベディング再生成
    profile_text = " ".join([job_title, str(salary_min), str(salary_max), intent_labels or ""])
    embedding = get_embedding(profile_text)
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE company_profile
            SET job_title = %s,
                salary_min = %s,
                salary_max = %s,
                intent_labels = %s,
                embedding = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND company_id = %s
        """, (
            job_title,
            salary_min,
            salary_max,
            intent_labels,
            embedding,
            job_id,
            company_id
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return RedirectResponse(url="/jobs", status_code=302)
        
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        raise HTTPException(status_code=500, detail=f"更新に失敗しました: {str(e)}")


@company_app.post("/job/{job_id}/delete")
async def job_delete(
    request: Request,
    job_id: str,
    company_id: str = Depends(require_company_login)
):
    """求人削除"""
    conn = get_db_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            DELETE FROM company_profile
            WHERE id = %s AND company_id = %s
        """, (job_id, company_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return RedirectResponse(url="/jobs", status_code=302)
        
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        raise HTTPException(status_code=500, detail=f"削除に失敗しました: {str(e)}")


# --- 起動 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(company_app, host="0.0.0.0", port=5001)