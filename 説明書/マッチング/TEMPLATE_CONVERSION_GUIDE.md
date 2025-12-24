# テンプレート変換ガイド - Flask → FastAPI

## 📋 概要

FlaskからFastAPIへの移行で最も重要なのが、テンプレート内の`url_for()`の置き換えです。
FastAPIにはFlaskのような`url_for()`関数がないため、直接URLパスを指定する必要があります。

## 🔄 主な変更点

### 1. url_for()の置き換え

**Flask:**
```html
<a href="{{ url_for('login') }}">ログイン</a>
<a href="{{ url_for('job_detail', job_id=job.id) }}">詳細</a>
```

**FastAPI:**
```html
<a href="/login">ログイン</a>
<a href="/job/{{ job.id }}">詳細</a>
```

### 2. フォームのaction属性

**Flask:**
```html
<form method="POST" action="{{ url_for('step1') }}">
```

**FastAPI:**
```html
<form method="POST" action="/step1">
```

## 📝 URL変換マッピング

### ユーザー向けルート

| Flask関数名 | FastAPI URL | 例 |
|------------|-------------|-----|
| `step1` | `/step1` | `<a href="/step1">` |
| `step2` | `/step2` | `<a href="/step2">` |
| `login` | `/login` | `<a href="/login">` |
| `logout` | `/logout` | `<a href="/logout">` |
| `chat_page` | `/chat` | `<a href="/chat">` |
| `profile` | `/profile` | `<a href="/profile">` |
| `profile_edit` | `/profile/edit` | `<a href="/profile/edit">` |

### 企業向けルート

| Flask関数名 | FastAPI URL | 例 |
|------------|-------------|-----|
| `company_register` | `/company/register` | `<a href="/company/register">` |
| `dashboard` | `/dashboard` | `<a href="/dashboard">` |
| `job_list` | `/jobs` | `<a href="/jobs">` |
| `job_new` | `/job/new` | `<a href="/job/new">` |
| `job_detail` | `/job/{job_id}` | `<a href="/job/{{ job.id }}">` |
| `job_edit` | `/job/{job_id}/edit` | `<a href="/job/{{ job.id }}/edit">` |
| `scout_history` | `/scout/history` | `<a href="/scout/history">` |
| `scout_search` | `/scout/search` | `<a href="/scout/search">` |
| `scout_ai_search` | `/scout/ai-search` | `<a href="/scout/ai-search">` |

## 🔧 自動変換ツール

`convert_templates.py`を実行すると、自動的にurl_for()を変換します：

```bash
python convert_templates.py
```

### 変換される例

**変換前（Flask）:**
```html
<a href="{{ url_for('login') }}">ログイン</a>
<a href="{{ url_for('job_detail', job_id=job.id) }}">詳細</a>
<form method="POST" action="{{ url_for('step1') }}">
```

**変換後（FastAPI）:**
```html
<a href="/login">ログイン</a>
<a href="/job/{{ job.id }}">詳細</a>
<form method="POST" action="/step1">
```

## 📂 ディレクトリ構成

```
project/
├── templates/              # 元のFlaskテンプレート
│   ├── login.html
│   ├── chat.html
│   └── ...
├── templates_fastapi/      # 変換後のFastAPIテンプレート
│   ├── login.html
│   ├── chat.html
│   └── ...
├── main.py                 # FastAPIユーザーアプリ
├── main_company.py         # FastAPI企業アプリ
└── convert_templates.py    # 変換スクリプト
```

## ✅ 手動変換チェックリスト

自動変換後、以下を手動で確認してください：

- [ ] すべての`{{ url_for(...) }}`が置き換えられている
- [ ] フォームの`action`属性が正しい
- [ ] JavaScriptコード内のURL参照が修正されている
- [ ] リダイレクト先のURLが正しい

## 🎯 変換後の確認方法

### 1. テンプレートディレクトリの変更

**main.py と main_company.py:**
```python
# 変更前
templates = Jinja2Templates(directory="templates")

# 変更後
templates = Jinja2Templates(directory="templates_fastapi")
```

### 2. アプリの起動

```bash
# ユーザー向けアプリ
uvicorn main:app --reload --port 5000

# 企業向けアプリ
uvicorn main_company:company_app --reload --port 5001
```

### 3. 動作確認

各ページにアクセスして、リンクやフォームが正しく動作するか確認：

- ✅ ログインページ: http://localhost:5000/login
- ✅ 登録ページ: http://localhost:5000/step1
- ✅ チャットページ: http://localhost:5000/chat
- ✅ 企業ログイン: http://localhost:5001/login
- ✅ 求人一覧: http://localhost:5001/jobs

## 🐛 トラブルシューティング

### エラー: `url_for is not defined`

**原因:** テンプレート内にまだ`url_for()`が残っている

**解決策:**
1. エラーメッセージからファイル名を確認
2. 該当ファイルを開いて`url_for()`を検索
3. 上記のマッピング表を使って手動で置き換え

### エラー: 404 Not Found

**原因:** URLパスが間違っている

**解決策:**
1. ブラウザのアドレスバーでURLを確認
2. `main.py`または`main_company.py`のルート定義と一致するか確認
3. 必要に応じてテンプレートのURLを修正

### リンクが動かない

**原因:** 相対パスと絶対パスの混在

**解決策:**
すべてのURLを絶対パス（`/`始まり）に統一：
```html
<!-- ❌ 相対パス -->
<a href="login">

<!-- ✅ 絶対パス -->
<a href="/login">
```

## 📚 追加の変更が必要なファイル

### chat.html

チャット機能のJavaScriptコード内のURL:

```javascript
// 変更前
fetch('{{ url_for("chat_api") }}', {

// 変更後
fetch('/api/chat', {
```

### company_dashboard.html

ダッシュボードの統計表示やリンク：

```html
<!-- 変更前 -->
<a href="{{ url_for('job_new') }}">新しい求人を登録</a>

<!-- 変更後 -->
<a href="/job/new">新しい求人を登録</a>
```

## 🎨 スタイルやJavaScriptは変更不要

CSS や JavaScript のコードは基本的に変更不要です。
ただし、URL を動的に生成している場合は修正が必要です。

## 💡 ベストプラクティス

1. **URLは常に絶対パスで記述**
   ```html
   <a href="/login">  ✅
   <a href="login">   ❌
   ```

2. **動的なIDはJinja2変数で**
   ```html
   <a href="/job/{{ job.id }}">  ✅
   <a href="/job/123">           ❌（ハードコード）
   ```

3. **フォームのactionも絶対パス**
   ```html
   <form action="/step1" method="POST">  ✅
   <form action="step1" method="POST">   ❌
   ```

## 🔍 検証コマンド

変換後、残っている`url_for()`を検索：

```bash
# Linux/Mac
grep -r "url_for" templates_fastapi/

# Windows (PowerShell)
Get-ChildItem -Path templates_fastapi -Recurse | Select-String "url_for"
```

何も出力されなければ、すべて置き換え完了です！

## 📖 参考リンク

- [FastAPI Templates](https://fastapi.tiangolo.com/advanced/templates/)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Starlette Routing](https://www.starlette.io/routing/)
