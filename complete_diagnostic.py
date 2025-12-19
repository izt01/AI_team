"""
完全診断スクリプト - すべての問題を一度にチェック
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

print("=" * 80)
print("🔍 完全診断スクリプト")
print("=" * 80)

# 1. 現在のディレクトリ確認
print("\n[1] 現在のディレクトリ:")
current_dir = os.getcwd()
print(f"   {current_dir}")

# 2. 必要なファイルの存在確認
print("\n[2] 必要なファイルの確認:")
required_files = [
    'app.py',
    'dynamic_question_generator_v2.py',
    'db_config.py',
    '.env',
    'tracking.py'
]

all_files_exist = True
for file in required_files:
    exists = Path(file).exists()
    status = "✅" if exists else "❌"
    print(f"   {status} {file}")
    if not exists:
        all_files_exist = False

# 3. .env ファイルの内容確認
print("\n[3] .env ファイルの確認:")
env_path = Path('.env')
if env_path.exists():
    print(f"   ✅ .env ファイルが存在します")
    print(f"   サイズ: {env_path.stat().st_size} bytes")
    
    # APIキーの確認
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(f"   ✅ OPENAI_API_KEY: {api_key[:20]}...")
    else:
        print(f"   ❌ OPENAI_API_KEY が設定されていません")
else:
    print(f"   ❌ .env ファイルが存在しません")

# 4. データベース接続確認
print("\n[4] データベース接続の確認:")
try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "jobmatch"),
        user=os.getenv("DB_USER", "devuser"),
        password=os.getenv("DB_PASSWORD", "devpass")
    )
    print("   ✅ データベース接続成功")
    
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 5. user_question_responses テーブルのスキーマ確認
    print("\n[5] user_question_responses テーブルの確認:")
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'user_question_responses'
        ORDER BY ordinal_position
    """)
    columns = cur.fetchall()
    
    column_names = [col['column_name'] for col in columns]
    
    print(f"   カラム数: {len(columns)}")
    for col in columns:
        print(f"   - {col['column_name']:30s} ({col['data_type']})")
    
    # question_key の確認
    if 'question_key' in column_names:
        print("\n   ✅ question_key カラムが存在します")
    else:
        print("\n   ❌ question_key カラムが存在しません")
        print("   対処法: python fix_user_question_responses_schema.py を実行")
    
    # 6. dynamic_questions テーブルの確認
    print("\n[6] dynamic_questions テーブルの確認:")
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'dynamic_questions'
        ORDER BY ordinal_position
    """)
    dq_columns = cur.fetchall()
    dq_column_names = [col['column_name'] for col in dq_columns]
    
    print(f"   カラム数: {len(dq_columns)}")
    for col in dq_columns[:5]:  # 最初の5つだけ表示
        print(f"   - {col['column_name']:30s} ({col['data_type']})")
    
    if 'question_key' in dq_column_names:
        print("   ✅ question_key カラムが存在します")
        
        # データ確認
        cur.execute("SELECT COUNT(*) as count FROM dynamic_questions")
        count = cur.fetchone()['count']
        print(f"   データ件数: {count}")
    else:
        print("   ❌ question_key カラムが存在しません")
    
    # 7. job_attributes テーブルの確認
    print("\n[7] job_attributes テーブルの確認:")
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'job_attributes'
        AND column_name = 'job_id'
    """)
    ja_col = cur.fetchone()
    
    if ja_col:
        print(f"   job_id カラムの型: {ja_col['data_type']}")
        if ja_col['data_type'] == 'uuid':
            print("   ✅ UUID型です（正しい）")
        else:
            print(f"   ⚠️  {ja_col['data_type']}型です")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"   ❌ データベースエラー: {e}")

# 8. dynamic_question_generator_v2.py のバージョン確認
print("\n[8] dynamic_question_generator_v2.py のバージョン確認:")
dqg_path = Path('dynamic_question_generator_v2.py')
if dqg_path.exists():
    with open(dqg_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # db_config インポートの確認
    if 'from db_config import get_db_conn' in content:
        print("   ✅ db_config をインポートしています")
    else:
        print("   ❌ db_config をインポートしていません（古いバージョン）")
    
    # UUID キャストの確認
    if '::uuid[]' in content:
        print("   ✅ UUID型キャストが含まれています")
    else:
        print("   ❌ UUID型キャストがありません（古いバージョン）")
    
    # question_key の確認
    if 'SELECT question_key' in content:
        print("   ⚠️  question_key を直接SELECTしています")
        if 'LEFT JOIN dynamic_questions' in content:
            print("   ✅ JOINで対応しています")
        else:
            print("   ❌ JOINで対応していません（要修正）")
else:
    print("   ❌ ファイルが見つかりません")

# 9. app.py のバージョン確認
print("\n[9] app.py のバージョン確認:")
app_path = Path('app.py')
if app_path.exists():
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'from db_config import get_db_conn' in content:
        print("   ✅ db_config をインポートしています")
    else:
        print("   ❌ db_config をインポートしていません（古いバージョン）")
else:
    print("   ❌ ファイルが見つかりません")

# 最終判定
print("\n" + "=" * 80)
print("📊 診断結果")
print("=" * 80)

issues = []

if not all_files_exist:
    issues.append("必要なファイルが不足しています")

if not os.getenv('OPENAI_API_KEY'):
    issues.append("OPENAI_API_KEY が設定されていません")

# question_key の確認（変数が定義されている場合のみ）
try:
    if 'question_key' not in column_names:
        issues.append("user_question_responses テーブルに question_key カラムがありません")
except:
    pass

if issues:
    print("\n❌ 以下の問題が見つかりました:\n")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    
    print("\n🔧 推奨対応:")
    print("   1. python fix_user_question_responses_schema.py を実行")
    print("   2. 最新版の dynamic_question_generator_v2.py に置き換え")
    print("   3. 最新版の app.py に置き換え")
    print("   4. アプリを再起動")
else:
    print("\n✅ すべての確認項目が正常です！")
    print("\n次のステップ:")
    print("   python app.py でアプリを起動")

print("=" * 80)