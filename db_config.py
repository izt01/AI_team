"""
データベース接続設定モジュール
環境変数から接続情報を読み込んで一元管理
"""

import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# 環境変数を読み込み
load_dotenv()


def get_db_conn():
    """
    データベース接続を取得
    
    Returns:
        psycopg2.connection: データベース接続オブジェクト
    
    使用例:
        conn = get_db_conn()
        cur = conn.cursor()
        # または
        cur = conn.cursor(cursor_factory=RealDictCursor)
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname=os.getenv("DB_NAME", "jobmatch"),
            user=os.getenv("DB_USER", "devuser"),
            password=os.getenv("DB_PASSWORD", "devpass")
        )
        return conn
    except Exception as e:
        print(f"❌ データベース接続エラー: {e}")
        raise


def get_db_cursor(conn, use_dict_cursor=False):
    """
    データベースカーソルを取得
    
    Args:
        conn: データベース接続オブジェクト
        use_dict_cursor: True の場合、RealDictCursor を使用
    
    Returns:
        カーソルオブジェクト
    
    使用例:
        conn = get_db_conn()
        cur = get_db_cursor(conn, use_dict_cursor=True)
    """
    if use_dict_cursor:
        return conn.cursor(cursor_factory=RealDictCursor)
    return conn.cursor()


# 接続テスト用の関数
def test_connection():
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
    # このファイルを直接実行した場合は接続テスト
    test_connection()