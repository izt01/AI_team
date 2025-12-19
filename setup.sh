#!/bin/bash

echo "=================================="
echo "FastAPI求人マッチングシステム"
echo "セットアップスクリプト"
echo "=================================="
echo ""

# 1. 依存パッケージのインストール
echo "📦 1. 依存パッケージをインストール中..."
pip install -r requirements_fastapi.txt

echo ""
echo "✅ パッケージのインストール完了"
echo ""

# 2. .envファイルの確認
if [ ! -f .env ]; then
    echo "⚠️  .envファイルが見つかりません"
    echo ""
    echo "以下の内容で .env ファイルを作成してください:"
    echo ""
    echo "OPENAI_API_KEY=your_openai_api_key_here"
    echo "DB_HOST=localhost"
    echo "DB_PORT=5432"
    echo "DB_NAME=jobmatch"
    echo "DB_USER=devuser"
    echo "DB_PASSWORD=devpass"
    echo "FLASK_SECRET_KEY=your_secret_key_here"
    echo ""
else
    echo "✅ .envファイルを確認しました"
    echo ""
fi

# 3. テンプレートの変換
if [ -d templates ] && [ ! -d templates_fastapi ]; then
    echo "🔄 3. テンプレートを変換中..."
    python convert_templates.py
    echo ""
else
    echo "✅ テンプレートは既に変換済みです"
    echo ""
fi

# 4. データベース接続確認
echo "🔍 4. データベース接続を確認中..."
python -c "from db_config import test_connection; test_connection()"
echo ""

# 完了メッセージ
echo "=================================="
echo "✅ セットアップ完了！"
echo "=================================="
echo ""
echo "次のステップ:"
echo ""
echo "【ユーザー向けアプリを起動】"
echo "  python main.py"
echo "  または"
echo "  uvicorn main:app --reload --port 5000"
echo ""
echo "【企業向けアプリを起動】"
echo "  python main_company.py"
echo "  または"
echo "  uvicorn main_company:company_app --reload --port 5001"
echo ""
echo "【APIドキュメント】"
echo "  http://localhost:5000/docs"
echo "  http://localhost:5001/docs"
echo ""