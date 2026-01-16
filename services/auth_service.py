"""
認証サービス
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from dotenv import load_dotenv

load_dotenv()

# セキュリティ設定
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/user/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    パスワード検証
    
    Args:
        plain_password: 平文パスワード
        hashed_password: ハッシュ化パスワード
        
    Returns:
        一致すればTrue
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        print(f"❌ パスワード検証エラー: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    パスワードをハッシュ化
    
    Args:
        password: 平文パスワード
        
    Returns:
        ハッシュ化パスワード
    """
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        print(f"❌ パスワードハッシュ化エラー: {e}")
        raise



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWTアクセストークンを生成
    
    Args:
        data: トークンに含めるデータ
        expires_delta: 有効期限
        
    Returns:
        JWTトークン
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    JWTトークンをデコード
    
    Args:
        token: JWTトークン
        
    Returns:
        デコードされたデータ
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    現在のユーザーIDを取得（依存性注入用）
    
    Args:
        token: JWTトークン
        
    Returns:
        ユーザーID
        
    Raises:
        HTTPException: 認証失敗時
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証に失敗しました",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    
    if user_id is None:
        raise credentials_exception
    
    return user_id


async def get_current_user_from_cookie(request) -> str:
    """
    CookieからユーザーIDを取得（依存性注入用）
    
    Args:
        request: FastAPI Request object
        
    Returns:
        ユーザーID
        
    Raises:
        HTTPException: 認証失敗時
    """
    from fastapi import Request
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証に失敗しました",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Cookieからトークンを取得
    token = request.cookies.get("access_token")
    
    if not token:
        print("❌ /api/user/chat: Cookieにaccess_tokenがありません")
        raise credentials_exception
    
    # "Bearer "プレフィックスを除去
    if token.startswith("Bearer "):
        token = token[7:]
    
    print(f"🍪 /api/user/chat: トークン取得成功: {token[:20]}...")
    
    payload = decode_access_token(token)
    
    if payload is None:
        print("❌ /api/user/chat: トークンのデコードに失敗")
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    
    if user_id is None:
        print("❌ /api/user/chat: トークンにuser_idがありません")
        raise credentials_exception
    
    print(f"✅ /api/user/chat: 認証成功 user_id={user_id}")
    return user_id


async def get_current_company(token: str = Depends(oauth2_scheme)) -> str:
    """
    現在の企業IDを取得（依存性注入用）
    
    Args:
        token: JWTトークン
        
    Returns:
        企業ID
        
    Raises:
        HTTPException: 認証失敗時
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証に失敗しました",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    company_id: str = payload.get("sub")
    entity_type: str = payload.get("type")
    
    if company_id is None or entity_type != "company":
        raise credentials_exception
    
    return company_id