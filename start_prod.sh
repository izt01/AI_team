#!/bin/bash

# FastAPI Job Matching System - Production Startup Script

echo "=================================="
echo "🚀 Starting Production Server"
echo "=================================="

# 環境変数チェック
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

# 依存パッケージのインストール
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# ワーカー数（CPUコア数 x 2 + 1）
WORKERS=${WORKERS:-4}

# サーバー起動
echo ""
echo "=================================="
echo "✅ Starting Gunicorn with $WORKERS workers..."
echo "=================================="

gunicorn main:app \
    -w $WORKERS \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
