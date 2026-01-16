#!/bin/bash

# FastAPI Job Matching System - Development Startup Script

echo "=================================="
echo "🚀 Starting Development Server"
echo "=================================="

# 環境変数チェック
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your settings."
    exit 1
fi

# 依存パッケージのインストール確認
echo "📦 Checking dependencies..."
pip install -r requirements.txt

# データベース接続テスト
echo "🔍 Testing database connection..."
python -c "from config.database import test_connection; test_connection()"

if [ $? -ne 0 ]; then
    echo "❌ Database connection failed!"
    echo "Please check your .env file and database settings."
    exit 1
fi

# サーバー起動
echo ""
echo "=================================="
echo "✅ Starting FastAPI server..."
echo "=================================="
echo "📚 API Docs: http://localhost:8000/docs"
echo "📖 ReDoc: http://localhost:8000/redoc"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
