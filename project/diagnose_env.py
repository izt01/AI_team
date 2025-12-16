"""
.envファイルの読み込み診断スクリプト
"""

import os
from pathlib import Path
from dotenv import load_dotenv

print("=" * 70)
print(".env ファイル読み込み診断")
print("=" * 70)

# 1. 現在のディレクトリ確認
current_dir = os.getcwd()
print(f"\n📍 現在のディレクトリ: {current_dir}")

# 2. .envファイルの存在確認
env_path = Path(current_dir) / '.env'
print(f"\n📄 .env ファイルのパス: {env_path}")
print(f"   存在確認: {'✅ 存在する' if env_path.exists() else '❌ 存在しない'}")

if not env_path.exists():
    print("\n❌ エラー: .envファイルが見つかりません")
    print("\n対処法:")
    print(f"1. {current_dir} に .env ファイルを配置してください")
    print("2. ファイル名が正確に '.env' であることを確認（スペースなし）")
    exit(1)

# 3. ファイルサイズ確認
file_size = env_path.stat().st_size
print(f"   サイズ: {file_size} bytes")

if file_size == 0:
    print("\n❌ エラー: .envファイルが空です")
    exit(1)

# 4. ファイル内容の確認（生データ）
print("\n📝 .env ファイルの内容（最初の5行）:")
try:
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    if not lines:
        print("   ❌ ファイルが空です")
    else:
        for i, line in enumerate(lines[:5], 1):
            # APIキーは部分的に伏せる
            display_line = line.rstrip()
            if 'API_KEY' in display_line and '=' in display_line:
                key, value = display_line.split('=', 1)
                masked_value = value[:20] + '...' if len(value) > 20 else value
                print(f"   {i}: {key}={masked_value}")
            else:
                print(f"   {i}: {display_line}")
                
except UnicodeDecodeError as e:
    print(f"   ❌ エンコーディングエラー: {e}")
    print("   対処法: fix_env_encoding.py を実行")
    exit(1)

# 5. python-dotenv で読み込み
print("\n🔄 python-dotenv で読み込み中...")
load_result = load_dotenv(env_path, override=True)
print(f"   読み込み結果: {'✅ 成功' if load_result else '❌ 失敗'}")

# 6. 環境変数の確認
print("\n🔍 環境変数の確認:")

variables_to_check = [
    'OPENAI_API_KEY',
    'DB_HOST',
    'DB_PORT',
    'DB_NAME',
    'DB_USER',
    'DB_PASSWORD',
    'FLASK_SECRET_KEY'
]

missing_vars = []
found_vars = []

for var in variables_to_check:
    value = os.getenv(var)
    if value:
        # APIキーやパスワードは部分的に表示
        if 'KEY' in var or 'PASSWORD' in var:
            display_value = value[:20] + '...' if len(value) > 20 else value
        else:
            display_value = value
        print(f"   ✅ {var:20s} = {display_value}")
        found_vars.append(var)
    else:
        print(f"   ❌ {var:20s} = (未設定)")
        missing_vars.append(var)

# 7. .envファイルの各行を解析
print("\n🔬 .envファイルの詳細解析:")
with open(env_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            if not value:
                print(f"   ⚠️  行 {i}: {key} = (空)")
            elif key == 'OPENAI_API_KEY':
                print(f"   🔑 行 {i}: {key} = {value[:20]}... (長さ: {len(value)})")
        else:
            print(f"   ⚠️  行 {i}: 不正な形式 '{line[:50]}'")

# 8. 最終判定
print("\n" + "=" * 70)
print("診断結果")
print("=" * 70)

if 'OPENAI_API_KEY' not in missing_vars:
    print("✅ OPENAI_API_KEY は正しく設定されています")
    print(f"   値: {os.getenv('OPENAI_API_KEY')[:30]}...")
else:
    print("❌ OPENAI_API_KEY が設定されていません")
    print("\n考えられる原因:")
    print("1. .envファイルに OPENAI_API_KEY= の行がない")
    print("2. OPENAI_API_KEY= の後に値がない（空行）")
    print("3. 行の形式が間違っている（スペースや特殊文字）")
    print("4. .envファイルのエンコーディングが正しくない")
    print("\n対処法:")
    print("1. .envファイルを開いて、以下の行があるか確認:")
    print("   OPENAI_API_KEY=sk-proj-...")
    print("2. '=' の前後にスペースがないことを確認")
    print("3. 行末に不要なスペースがないことを確認")

if missing_vars:
    print(f"\n⚠️  その他の未設定変数: {', '.join(missing_vars)}")

print("=" * 70)