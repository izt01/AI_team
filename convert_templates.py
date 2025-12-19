"""
FlaskテンプレートをFastAPI用に自動変換するスクリプト

url_for()を実際のURLパスに置き換えます
"""

import os
import re
from pathlib import Path

# url_for()のマッピング（Flask関数名 → FastAPIパス）
URL_MAPPINGS = {
    # ユーザー向けルート
    'step1': '/step1',
    'step2': '/step2',
    'login': '/login',
    'logout': '/logout',
    'chat_page': '/chat',
    'profile': '/profile',
    'profile_edit': '/profile/edit',
    
    # 企業向けルート
    'company_register': '/company/register',
    'dashboard': '/dashboard',
    'job_list': '/jobs',
    'job_new': '/job/new',
    'job_detail': '/job/',  # 後ろにIDが付く
    'job_edit': '/job/',  # 後ろにID/editが付く
    'scout_history': '/scout/history',
    'scout_search': '/scout/search',
    'scout_ai_search': '/scout/ai-search',
}


def convert_url_for(content: str) -> str:
    """
    url_for()を実際のURLパスに変換
    
    例:
    - {{ url_for('login') }} → /login
    - {{ url_for('job_detail', job_id=job.id) }} → /job/{{ job.id }}
    """
    
    # パターン1: 引数なしのurl_for()
    # {{ url_for('login') }} → /login
    for func_name, url_path in URL_MAPPINGS.items():
        if not url_path.endswith('/'):
            # 引数なしの単純な置換
            pattern = r"{{\s*url_for\(['\"]" + func_name + r"['\"]\)\s*}}"
            content = re.sub(pattern, url_path, content)
    
    # パターン2: job_detail with job_id
    # {{ url_for('job_detail', job_id=job.id) }} → /job/{{ job.id }}
    pattern = r"{{\s*url_for\(['\"]job_detail['\"]\s*,\s*job_id\s*=\s*([^)]+)\)\s*}}"
    content = re.sub(pattern, r'/job/{{ \1 }}', content)
    
    # パターン3: job_edit with job_id
    # {{ url_for('job_edit', job_id=job.id) }} → /job/{{ job.id }}/edit
    pattern = r"{{\s*url_for\(['\"]job_edit['\"]\s*,\s*job_id\s*=\s*([^)]+)\)\s*}}"
    content = re.sub(pattern, r'/job/{{ \1 }}/edit', content)
    
    # パターン4: Pythonコード内のurl_for()
    # href="{{ url_for('chat_page') }}" → href="/chat"
    for func_name, url_path in URL_MAPPINGS.items():
        if not url_path.endswith('/'):
            pattern = r'url_for\(["\']' + func_name + r'["\']\)'
            content = re.sub(pattern, f'"{url_path}"', content)
    
    return content


def convert_template_file(file_path: Path, output_dir: Path):
    """テンプレートファイルを変換"""
    
    print(f"変換中: {file_path.name}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # url_for()を変換
    converted_content = convert_url_for(content)
    
    # 変換結果を保存
    output_path = output_dir / file_path.name
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(converted_content)
    
    # 変更があったかチェック
    if content != converted_content:
        print(f"  ✅ 変換完了: {file_path.name}")
        
        # 変更箇所を表示
        original_urls = re.findall(r'url_for\([^)]+\)', content)
        if original_urls:
            print(f"     変換されたurl_for(): {len(original_urls)}個")
    else:
        print(f"  ⚠️  変更なし: {file_path.name}")


def main():
    """メイン処理"""
    
    print("=" * 70)
    print("FlaskテンプレートをFastAPI用に変換")
    print("=" * 70)
    print()
    
    # 入力ディレクトリ（元のテンプレート）
    input_dir = Path("templates")
    
    # 出力ディレクトリ（変換後のテンプレート）
    output_dir = Path("templates_fastapi")
    output_dir.mkdir(exist_ok=True)
    
    if not input_dir.exists():
        print(f"❌ エラー: {input_dir} が見つかりません")
        print()
        print("このスクリプトは templates/ ディレクトリと同じ場所で実行してください")
        return
    
    # HTMLファイルを取得
    html_files = list(input_dir.glob("*.html"))
    
    if not html_files:
        print(f"❌ {input_dir} にHTMLファイルが見つかりません")
        return
    
    print(f"📁 入力: {input_dir}")
    print(f"📁 出力: {output_dir}")
    print(f"📄 ファイル数: {len(html_files)}")
    print()
    
    # 各ファイルを変換
    for html_file in sorted(html_files):
        convert_template_file(html_file, output_dir)
    
    print()
    print("=" * 70)
    print("✅ 変換完了！")
    print("=" * 70)
    print()
    print("次のステップ:")
    print("  1. templates_fastapi/ の内容を確認")
    print("  2. main.py と main_company.py のテンプレートディレクトリを変更:")
    print('     templates = Jinja2Templates(directory="templates_fastapi")')
    print("  3. アプリを再起動")
    print()


if __name__ == "__main__":
    main()