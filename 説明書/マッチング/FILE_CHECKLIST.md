# ファイルチェックリスト - FastAPI求人マッチングシステム

## ✅ アップロード済みファイル（確認済み）

### メインアプリケーション
- [x] main.py（修正済み - テンプレートパス変更）
- [x] main_company.py（修正済み - テンプレートパス変更）
- [x] requirements_fastapi.txt
- [x] setup.sh

### AI/MLモジュール
- [x] tracking.py
- [x] hybrid_recommender.py
- [x] multi_axis_evaluator.py

### ユーティリティ
- [x] generate_10k_history_date.py
- [x] ratch_fallback_search.py

## ❌ 不足ファイル（要アップロード）

### 必須ファイル（⭐⭐⭐⭐⭐）
- [ ] **db_config.py** - データベース接続設定
- [ ] **dynamic_question_generator_v2.py** - 動的質問生成（最新版）
- [ ] **dynamic_questions.py** - 動的質問管理

### 重要ファイル（⭐⭐⭐⭐）
- [ ] **company_scout_system.py** - スカウトシステム

### テンプレート（⭐⭐⭐⭐⭐）
- [x] templates_fastapi.tar.gz（すでに提供済み）
  - 解凍すると16個のHTMLファイルが生成されます

### 設定ファイル（⭐⭐⭐⭐⭐）
- [ ] **.env** - 環境変数（ユーザーが作成）

### ドキュメント（すでに提供済み）
- [x] README_FASTAPI.md
- [x] MIGRATION_GUIDE.md
- [x] TEMPLATE_CONVERSION_GUIDE.md
- [x] PROJECT_STRUCTURE.md
- [x] DIRECTORY_TREE.txt

### ユーティリティツール（すでに提供済み）
- [x] convert_templates.py
- [x] setup.bat

## 🔧 修正が必要だった箇所

### main.py
```python
# 修正前
templates = Jinja2Templates(directory="templates")

# 修正後
templates = Jinja2Templates(directory="templates_fastapi")
```

### main_company.py
```python
# 修正前
templates = Jinja2Templates(directory="templates")

# 修正後
templates = Jinja2Templates(directory="templates_fastapi")
```

## 📋 不足ファイルの対処方法

### 1. db_config.py
このファイルは以前アップロードされていました。以下の内容で作成してください：

```python
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


def get_db_conn(use_dict_cursor=False):
    """
    データベース接続を取得
    
    Args:
        use_dict_cursor: True の場合、RealDictCursor を使用（辞書形式で結果取得）
    
    Returns:
        psycopg2.connection: データベース接続オブジェクト
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
```

### 2. dynamic_question_generator_v2.py
これは以前アップロードされたファイルです。元のファイルを使用してください。

### 3. dynamic_questions.py
これも以前アップロードされたファイルです。元のファイルを使用してください。

### 4. company_scout_system.py
これも以前アップロードされたファイルです。元のファイルを使用してください。

## ✅ 次のステップ

### すぐにできること（不足ファイルなしで動作確認）

1. **テンプレートを解凍**
   ```bash
   tar xzf templates_fastapi.tar.gz
   ```

2. **.envファイルを作成**
   ```bash
   cat > .env << EOF
   OPENAI_API_KEY=your_api_key_here
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=jobmatch
   DB_USER=devuser
   DB_PASSWORD=devpass
   FLASK_SECRET_KEY=your_secret_key
   EOF
   ```

3. **依存パッケージをインストール**
   ```bash
   pip install -r requirements_fastapi.txt
   ```

### 不足ファイルを追加後

4. **不足ファイルを配置**
   - db_config.py
   - dynamic_question_generator_v2.py
   - dynamic_questions.py
   - company_scout_system.py

5. **アプリを起動**
   ```bash
   uvicorn main:app --reload --port 5000
   uvicorn main_company:company_app --reload --port 5001
   ```

## 🎯 最小構成で動作させる方法

もし不足ファイルがすぐに用意できない場合、以下の対処で最小限の動作確認が可能です：

### main.pyから依存を削除（一時的）

```python
# コメントアウト（一時的）
# from dynamic_questions import QuestionGenerator, QuestionSelector
# from dynamic_question_generator_v2 import DynamicQuestionGenerator

# 動的質問生成器の初期化もコメントアウト
# dynamic_question_gen = DynamicQuestionGenerator(client)
```

ただし、この場合はチャット機能が制限されます。

## 📞 サポート

不足ファイルの内容が必要な場合は、元のアップロードファイルを確認するか、
私に以下のファイルを再度アップロードしていただければ、完全版を作成できます：

- db_config.py
- dynamic_question_generator_v2.py
- dynamic_questions.py
- company_scout_system.py
