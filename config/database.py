"""
データベース接続設定
完全なDBスキーマ(db_schema_complete.sql)に対応
"""

import os
from typing import Generator
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()


class DatabaseConfig:
    """データベース設定クラス"""
    
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.dbname = os.getenv("DB_NAME", "jobmatch")
        self.user = os.getenv("DB_USER", "devuser")
        self.password = os.getenv("DB_PASSWORD", "devpass")
    
    def get_connection_params(self) -> dict:
        """接続パラメータを辞書で返す"""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password
        }


db_config = DatabaseConfig()


def get_db_conn():
    """
    データベース接続を取得
    
    Returns:
        psycopg2.connection: データベース接続オブジェクト
    """
    try:
        conn = psycopg2.connect(**db_config.get_connection_params())
        return conn
    except Exception as e:
        print(f"❌ データベース接続エラー: {e}")
        raise


def get_db_cursor(conn, use_dict_cursor: bool = False):
    """
    データベースカーソルを取得
    
    Args:
        conn: データベース接続オブジェクト
        use_dict_cursor: True の場合、RealDictCursor を使用
    
    Returns:
        カーソルオブジェクト
    """
    if use_dict_cursor:
        return conn.cursor(cursor_factory=RealDictCursor)
    return conn.cursor()


def get_db() -> Generator:
    """
    FastAPI依存性注入用のデータベース接続
    
    Yields:
        データベース接続
    """
    conn = get_db_conn()
    try:
        yield conn
    finally:
        conn.close()


def test_connection() -> bool:
    """データベース接続をテスト"""
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        cur.close()
        conn.close()
        print(f"✅ データベース接続成功: PostgreSQL {version[0]}")
        return True
    except Exception as e:
        print(f"❌ データベース接続失敗: {e}")
        return False


if __name__ == "__main__":
    test_connection()
