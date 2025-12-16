"""
認証関連APIルーター
- ユーザー登録・ログイン
- 企業登録・ログイン
"""

from fastapi import APIRouter, HTTPException, status, Depends
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from typing import Optional

from models.auth_models import (
    UserRegisterRequest,
    CompanyRegisterRequest,
    LoginRequest,
    LoginResponse,
    RegisterResponse,
)
from db_config import get_db_conn

router = APIRouter()


# ============================================
# ユーザー認証
# ============================================

@router.post("/register/user", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_user(request: UserRegisterRequest):
    """
    ユーザー登録
    
    新規ユーザーを登録し、user_profileも同時に作成します。
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        
        # メールアドレスの重複チェック
        cur.execute("SELECT user_id FROM personal_date WHERE email = %s", (request.email,))
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このメールアドレスは既に登録されています"
            )
        
        # 新しいuser_idを生成（MAX+1）
        cur.execute("SELECT COALESCE(MAX(user_id), 0) + 1 FROM personal_date")
        new_user_id = cur.fetchone()[0]
        
        # パスワードをハッシュ化
        password_hash = generate_password_hash(request.password)
        
        # personal_dateテーブルに挿入
        cur.execute("""
            INSERT INTO personal_date (
                user_id, email, password_hash, user_name, 
                birth_day, phone_number, address, 
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            new_user_id,
            request.email,
            password_hash,
            request.name,
            request.birth_day,
            request.phone_number,
            request.address,
        ))
        
        # user_profileテーブルに空レコードを作成
        cur.execute("""
            INSERT INTO user_profile (
                user_id, job_title, location_prefecture, salary_min,
                created_at, updated_at
            )
            VALUES (%s, '', '', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (new_user_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return RegisterResponse(
            message="ユーザー登録が完了しました",
            user_id=new_user_id,
            email=request.email,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登録エラー: {str(e)}"
        )


@router.post("/login/user", response_model=LoginResponse)
async def login_user(request: LoginRequest):
    """
    ユーザーログイン
    
    メールアドレスとパスワードで認証を行います。
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        
        # ユーザー情報を取得
        cur.execute(
            "SELECT user_id, email, password_hash FROM personal_date WHERE email = %s",
            (request.email,)
        )
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="メールアドレスまたはパスワードが正しくありません"
            )
        
        user_id, email, password_hash = user
        
        # パスワード検証
        if not check_password_hash(password_hash, request.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="メールアドレスまたはパスワードが正しくありません"
            )
        
        # 簡易的なトークン生成（本番環境ではJWTを使用）
        access_token = f"user_{user_id}_{uuid.uuid4()}"
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user_id,
            email=email,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ログインエラー: {str(e)}"
        )


# ============================================
# 企業認証
# ============================================

@router.post("/register/company", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_company(request: CompanyRegisterRequest):
    """
    企業登録
    
    新規企業を登録します。
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        
        # メールアドレスの重複チェック
        cur.execute("SELECT email FROM company_date WHERE email = %s", (request.email,))
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このメールアドレスは既に登録されています"
            )
        
        # UUIDを生成
        record_id = str(uuid.uuid4())
        company_id = str(uuid.uuid4())
        
        # パスワードをハッシュ化
        password_hash = generate_password_hash(request.password)
        
        # company_dateテーブルに挿入
        cur.execute("""
            INSERT INTO company_date (
                id, company_id, email, password, company_name,
                address, phone_number, website_url,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            record_id,
            company_id,
            request.email,
            password_hash,
            request.company_name,
            request.address,
            request.phone_number,
            request.website_url,
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return RegisterResponse(
            message="企業登録が完了しました",
            company_id=company_id,
            email=request.email,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登録エラー: {str(e)}"
        )


@router.post("/login/company", response_model=LoginResponse)
async def login_company(request: LoginRequest):
    """
    企業ログイン
    
    メールアドレスとパスワードで認証を行います。
    """
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        
        # 企業情報を取得
        cur.execute(
            "SELECT password, company_id, email FROM company_date WHERE email = %s",
            (request.email,)
        )
        company = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="メールアドレスまたはパスワードが正しくありません"
            )
        
        password_hash, company_id, email = company
        
        # パスワード検証
        if not check_password_hash(password_hash, request.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="メールアドレスまたはパスワードが正しくありません"
            )
        
        # 簡易的なトークン生成（本番環境ではJWTを使用）
        access_token = f"company_{company_id}_{uuid.uuid4()}"
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            company_id=company_id,
            email=email,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ログインエラー: {str(e)}"
        )