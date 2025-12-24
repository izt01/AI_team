# FastAPI求人マッチングシステム - 完全なフォルダ構成

## 📁 プロジェクト全体構成

```
jobmatch-fastapi/
│
├── 📄 main.py                              # FastAPIメインアプリ（ユーザー向け）
├── 📄 main_company.py                      # FastAPI企業向けアプリ
├── 📄 db_config.py                         # データベース接続設定
│
├── 📋 requirements_fastapi.txt             # FastAPI用パッケージリスト
├── 📋 requirements.txt                     # Flask用パッケージリスト（参考用）
│
├── 🔧 .env                                 # 環境変数（要作成）
├── 🔧 .gitignore                           # Git除外設定（推奨）
│
├── 🚀 setup.sh                             # Linux/Mac セットアップスクリプト
├── 🚀 setup.bat                            # Windows セットアップスクリプト
├── 🔄 convert_templates.py                 # テンプレート変換スクリプト
│
├── 📚 README_FASTAPI.md                    # FastAPI版セットアップガイド
├── 📚 MIGRATION_GUIDE.md                   # Flask→FastAPI移行ガイド
├── 📚 TEMPLATE_CONVERSION_GUIDE.md         # テンプレート変換ガイド
│
├── 🧠 AI/MLモジュール/
│   ├── 📄 tracking.py                      # ユーザー行動追跡
│   ├── 📄 hybrid_recommender.py            # ハイブリッドレコメンダー
│   ├── 📄 multi_axis_evaluator.py          # 多軸評価システム
│   ├── 📄 dynamic_questions.py             # 動的質問生成（旧版）
│   ├── 📄 dynamic_question_generator_v2.py # 動的質問生成（最新版）
│   └── 📄 company_scout_system.py          # 企業スカウトシステム
│
├── 🛠️ ユーティリティスクリプト/
│   ├── 📄 check_scout_search.py            # スカウト検索確認
│   ├── 📄 complete_diagnostic.py           # 完全診断スクリプト
│   ├── 📄 diagnose_env.py                  # 環境変数診断
│   ├── 📄 fix_all_issues.py                # 問題自動修正
│   ├── 📄 fix_embedding_dimensions.py      # エンベディング次元修正
│   ├── 📄 fix_job_detail.py                # 求人詳細修正
│   ├── 📄 ratch_fallback_search.py         # フォールバック検索パッチ
│   └── 📄 generate_10k_history_date.py     # 履歴データ生成
│
├── 🎨 templates_fastapi/                   # FastAPI用テンプレート（変換済み）
│   │
│   ├── 👤 ユーザー向けテンプレート/
│   │   ├── 📄 login.html                   # ログイン画面
│   │   ├── 📄 form_step1.html              # 登録ステップ1（基本情報）
│   │   ├── 📄 form_step2.html              # 登録ステップ2（希望条件）
│   │   ├── 📄 chat.html                    # チャット画面
│   │   ├── 📄 profile.html                 # プロフィール画面
│   │   └── 📄 [その他ユーザー向けページ]
│   │
│   └── 🏢 企業向けテンプレート/
│       ├── 📄 company_login.html           # 企業ログイン画面
│       ├── 📄 company_register.html        # 企業登録画面
│       ├── 📄 company_dashboard.html       # 企業ダッシュボード
│       ├── 📄 job_list.html                # 求人一覧
│       ├── 📄 job_form.html                # 求人登録フォーム
│       ├── 📄 job_detail.html              # 求人詳細
│       ├── 📄 job_edit.html                # 求人編集
│       ├── 📄 scout_search.html            # スカウト検索
│       ├── 📄 scout_ai_search.html         # AIスカウト検索
│       ├── 📄 scout_history.html           # スカウト履歴
│       └── 📄 candidate_detail.html        # 候補者詳細
│
├── 🎨 templates/                           # Flask用テンプレート（元ファイル・参考用）
│   └── [同じ構成]
│
├── 🎭 static/                              # 静的ファイル（オプション）
│   ├── css/
│   │   └── style.css                       # カスタムCSS
│   ├── js/
│   │   └── app.js                          # カスタムJavaScript
│   └── images/
│       └── logo.png                        # ロゴ画像
│
├── 🗄️ データベース関連/
│   ├── 📄 schema.sql                       # DBスキーマ定義（要作成）
│   ├── 📄 seed_data.sql                    # 初期データ（要作成）
│   └── 📁 migrations/                      # マイグレーション（オプション）
│
├── 🧪 tests/                               # テストファイル（オプション）
│   ├── 📄 test_main.py                     # メインアプリテスト
│   ├── 📄 test_company.py                  # 企業アプリテスト
│   └── 📄 test_recommender.py              # レコメンダーテスト
│
└── 📦 アーカイブ/
    ├── 📄 app.py                           # Flask版メインアプリ（参考用）
    ├── 📄 company_app.py                   # Flask版企業アプリ（参考用）
    ├── 📄 comapny_app_enhanced.py          # Flask版企業アプリ拡張版（参考用）
    └── 📦 templates_fastapi.tar.gz         # 変換済みテンプレートアーカイブ
```

## 📝 各ファイルの詳細説明

### 🎯 メインアプリケーションファイル

| ファイル名 | 説明 | 行数 | 重要度 |
|-----------|------|------|--------|
| **main.py** | ユーザー向けFastAPIアプリ<br>・登録/ログイン<br>・チャット機能<br>・求人推薦 | ~700行 | ⭐⭐⭐⭐⭐ |
| **main_company.py** | 企業向けFastAPIアプリ<br>・求人管理<br>・スカウト機能<br>・候補者検索 | ~500行 | ⭐⭐⭐⭐⭐ |
| **db_config.py** | DB接続一元管理<br>・接続プール<br>・環境変数読込 | ~80行 | ⭐⭐⭐⭐⭐ |

### 🧠 AI/MLコアモジュール

| ファイル名 | 説明 | 行数 | 重要度 |
|-----------|------|------|--------|
| **tracking.py** | ユーザー行動追跡<br>・クリック/お気に入り<br>・応募記録<br>・チャット履歴 | ~300行 | ⭐⭐⭐⭐ |
| **hybrid_recommender.py** | ハイブリッド推薦<br>・協調フィルタリング<br>・コンテンツベース<br>・MLスコアリング | ~900行 | ⭐⭐⭐⭐⭐ |
| **multi_axis_evaluator.py** | 多軸評価<br>・企業文化マッチ<br>・働き方評価<br>・キャリアパス分析 | ~500行 | ⭐⭐⭐⭐ |
| **dynamic_question_generator_v2.py** | 動的質問生成<br>・GPT-4活用<br>・文脈理解<br>・絞り込み最適化 | ~600行 | ⭐⭐⭐⭐⭐ |
| **company_scout_system.py** | スカウトシステム<br>・性格分析<br>・AIマッチング<br>・メッセージ生成 | ~700行 | ⭐⭐⭐⭐ |

### 🛠️ ユーティリティ

| ファイル名 | 説明 | 用途 |
|-----------|------|------|
| **convert_templates.py** | テンプレート自動変換 | 初回セットアップ時 |
| **setup.sh / .bat** | 自動セットアップ | 初回セットアップ時 |
| **check_scout_search.py** | スカウト機能確認 | デバッグ・動作確認 |
| **complete_diagnostic.py** | 全体診断 | トラブルシューティング |
| **fix_*.py** | 各種修正スクリプト | 問題発生時 |

### 🎨 テンプレート（16ファイル）

#### 👤 ユーザー向け（6ファイル）

1. **login.html** - ログイン画面
2. **form_step1.html** - 登録ステップ1（個人情報）
3. **form_step2.html** - 登録ステップ2（希望条件）
4. **chat.html** - AI対話による求人検索
5. **profile.html** - ユーザープロフィール
6. **[その他]** - お気に入り、応募履歴など

#### 🏢 企業向け（10ファイル）

1. **company_login.html** - 企業ログイン
2. **company_register.html** - 企業登録
3. **company_dashboard.html** - ダッシュボード
4. **job_list.html** - 求人一覧
5. **job_form.html** - 求人登録
6. **job_detail.html** - 求人詳細
7. **job_edit.html** - 求人編集
8. **scout_search.html** - 候補者検索
9. **scout_ai_search.html** - AIスカウト検索
10. **scout_history.html** - スカウト履歴
11. **candidate_detail.html** - 候補者詳細

### 📋 設定ファイル

| ファイル名 | 説明 | 形式 |
|-----------|------|------|
| **.env** | 環境変数<br>・APIキー<br>・DB接続情報 | `KEY=value` |
| **requirements_fastapi.txt** | FastAPI依存パッケージ | pip形式 |
| **.gitignore** | Git除外設定 | パターンマッチ |

### 📚 ドキュメント

1. **README_FASTAPI.md** - FastAPI版のセットアップ手順
2. **MIGRATION_GUIDE.md** - Flask→FastAPI移行ガイド
3. **TEMPLATE_CONVERSION_GUIDE.md** - テンプレート変換詳細

## 🗄️ データベース構造

### 必要なテーブル

```sql
-- ユーザー関連
personal_date                    -- 個人情報
user_profile                     -- ユーザープロフィール
user_question_responses          -- 質問への回答
user_personality_analysis        -- 性格分析結果
user_filtering_history           -- フィルタリング履歴

-- 企業・求人関連
company_date                     -- 企業情報
company_profile                  -- 求人情報
job_attributes                   -- 求人属性

-- 行動追跡
user_interactions                -- ユーザー行動（クリック、お気に入り等）
chat_history                     -- チャット履歴
user_interaction_summary         -- 行動サマリー（VIEW）

-- 質問管理
dynamic_questions                -- 動的質問データ

-- スカウト
scout_messages                   -- スカウトメッセージ（要作成）
scout_history                    -- スカウト履歴（要作成）
```

## 📦 依存パッケージ

### FastAPI関連
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
jinja2==3.1.3
starlette==0.35.1
```

### データベース
```
psycopg2-binary==2.9.9
pgvector==0.2.0
```

### AI/ML
```
openai==1.12.0
scikit-learn==1.3.2
numpy==1.26.2
pandas==2.1.4
```

### その他
```
python-dotenv==1.0.0
Werkzeug==3.0.1  # パスワードハッシュ化
```

## 🚀 起動順序

### 1. セットアップ（初回のみ）

```bash
# 依存パッケージインストール
pip install -r requirements_fastapi.txt

# テンプレート変換
python convert_templates.py

# または自動セットアップ
./setup.sh  # Linux/Mac
setup.bat   # Windows
```

### 2. 環境変数設定

`.env`ファイルを作成：

```env
OPENAI_API_KEY=sk-proj-...
DB_HOST=localhost
DB_PORT=5432
DB_NAME=jobmatch
DB_USER=devuser
DB_PASSWORD=devpass
FLASK_SECRET_KEY=your-secret-key
```

### 3. データベース準備

```bash
# PostgreSQL起動確認
psql -U devuser -d jobmatch

# 必要に応じてスキーマ作成
psql -U devuser -d jobmatch < schema.sql
```

### 4. アプリケーション起動

```bash
# ユーザー向けアプリ（ポート5000）
uvicorn main:app --reload --port 5000

# 企業向けアプリ（ポート5001）
uvicorn main_company:company_app --reload --port 5001
```

### 5. アクセス

- ユーザーアプリ: http://localhost:5000
- 企業アプリ: http://localhost:5001
- API Docs: http://localhost:5000/docs
- 企業API Docs: http://localhost:5001/docs

## 📊 推奨ファイルサイズ

```
プロジェクト全体:        ~50MB
├── Pythonコード:       ~5MB
├── テンプレート:       ~500KB
├── ドキュメント:       ~200KB
└── 依存パッケージ:     ~45MB
```

## 🔐 セキュリティチェックリスト

- [ ] `.env`ファイルを`.gitignore`に追加
- [ ] APIキーを環境変数で管理
- [ ] パスワードはハッシュ化して保存
- [ ] SQLインジェクション対策（パラメータ化クエリ）
- [ ] CORS設定（本番環境）
- [ ] HTTPS化（本番環境）

## 🎯 次のステップ

1. ✅ この構成図に従ってファイルを配置
2. ✅ `.env`ファイルを作成
3. ✅ `setup.sh`または`setup.bat`を実行
4. ✅ データベースに接続できるか確認
5. ✅ アプリを起動して動作確認
6. ✅ `/docs`でAPIドキュメントを確認

## 💡 開発のヒント

### 新機能追加時

1. `main.py`または`main_company.py`にルートを追加
2. 必要に応じて新しいテンプレートを作成
3. `/docs`で自動生成されたAPIドキュメントを確認

### デバッグ時

1. `complete_diagnostic.py`で全体診断
2. ログを確認（ターミナル出力）
3. `/docs`のTry it outで手動テスト

### 本番デプロイ時

1. `DEBUG=False`に設定
2. Gunicornまたは同等のWSGIサーバーを使用
3. Nginx等のリバースプロキシを設定
4. HTTPS証明書を設定

このフォルダ構成に従えば、FastAPI版の求人マッチングシステムが完全に動作します！
