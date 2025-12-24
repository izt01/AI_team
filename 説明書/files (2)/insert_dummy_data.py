"""
JobMatch AI - ダミーデータ挿入スクリプト

このスクリプトは、開発・テスト用のダミーデータをデータベースに挿入します。

【挿入データ】
1. 企業情報 (company_date): 10社
2. 求人情報 (company_profile): 50件
3. ユーザー情報 (personal_date): 5名
4. ユーザープロフィール (user_profile): 5名分

【実行方法】
python insert_dummy_data.py
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash
import random
from datetime import datetime, timedelta
from db_config import get_db_conn


def clear_all_tables():
    """全テーブルのデータをクリア（危険！本番環境では実行しないこと）"""
    print("🗑️  既存データをクリア中...")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    tables = [
        'chat_history',
        'user_interactions',
        'score_history',
        'conversation_sessions',
        'user_insights',
        'conversation_turns',
        'user_sessions',
        'company_profile',
        'company_date',
        'user_profile',
        'personal_date'
    ]
    
    for table in tables:
        try:
            cur.execute(f"TRUNCATE TABLE {table} CASCADE")
            print(f"  ✅ {table} をクリア")
        except Exception as e:
            print(f"  ⚠️  {table} のクリアをスキップ: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    print()


def insert_companies():
    """企業情報をダミーデータで挿入"""
    print("🏢 企業情報を挿入中...")
    
    companies = [
        {
            'company_id': 1,
            'company_name': '株式会社テックイノベーション',
            'industry': 'IT・インターネット',
            'employee_count': 500,
            'founded_year': 2015,
            'headquarters': '東京都渋谷区',
            'website': 'https://tech-innovation.example.com'
        },
        {
            'company_id': 2,
            'company_name': 'デジタルソリューションズ株式会社',
            'industry': 'ソフトウェア開発',
            'employee_count': 200,
            'founded_year': 2018,
            'headquarters': '東京都港区',
            'website': 'https://digital-solutions.example.com'
        },
        {
            'company_id': 3,
            'company_name': 'グローバルデザイン株式会社',
            'industry': 'Webデザイン',
            'employee_count': 150,
            'founded_year': 2017,
            'headquarters': '東京都千代田区',
            'website': 'https://global-design.example.com'
        },
        {
            'company_id': 4,
            'company_name': '株式会社AIテクノロジーズ',
            'industry': 'AI・機械学習',
            'employee_count': 300,
            'founded_year': 2019,
            'headquarters': '神奈川県横浜市',
            'website': 'https://ai-tech.example.com'
        },
        {
            'company_id': 5,
            'company_name': 'クラウドシステムズ株式会社',
            'industry': 'クラウドサービス',
            'employee_count': 400,
            'founded_year': 2016,
            'headquarters': '大阪府大阪市',
            'website': 'https://cloud-systems.example.com'
        },
        {
            'company_id': 6,
            'company_name': '株式会社フィンテックソリューション',
            'industry': '金融・Fintech',
            'employee_count': 250,
            'founded_year': 2020,
            'headquarters': '東京都新宿区',
            'website': 'https://fintech-sol.example.com'
        },
        {
            'company_id': 7,
            'company_name': 'モバイルアプリケーションズ株式会社',
            'industry': 'モバイルアプリ開発',
            'employee_count': 180,
            'founded_year': 2018,
            'headquarters': '東京都品川区',
            'website': 'https://mobile-apps.example.com'
        },
        {
            'company_id': 8,
            'company_name': '株式会社データアナリティクス',
            'industry': 'データ分析',
            'employee_count': 220,
            'founded_year': 2019,
            'headquarters': '福岡県福岡市',
            'website': 'https://data-analytics.example.com'
        },
        {
            'company_id': 9,
            'company_name': 'セキュリティソリューション株式会社',
            'industry': 'セキュリティ',
            'employee_count': 350,
            'founded_year': 2017,
            'headquarters': '愛知県名古屋市',
            'website': 'https://security-sol.example.com'
        },
        {
            'company_id': 10,
            'company_name': '株式会社ゲームスタジオ',
            'industry': 'ゲーム開発',
            'employee_count': 280,
            'founded_year': 2016,
            'headquarters': '東京都目黒区',
            'website': 'https://game-studio.example.com'
        }
    ]
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    for company in companies:
        cur.execute("""
            INSERT INTO company_date (
                company_id, company_name, industry, employee_count, 
                founded_year, headquarters, website,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            company['company_id'],
            company['company_name'],
            company['industry'],
            company['employee_count'],
            company['founded_year'],
            company['headquarters'],
            company['website']
        ))
        print(f"  ✅ {company['company_name']}")
    
    conn.commit()
    cur.close()
    conn.close()
    print()


def insert_jobs():
    """求人情報をダミーデータで挿入"""
    print("💼 求人情報を挿入中...")
    
    # 職種テンプレート
    job_templates = [
        {
            'job_title': 'Webエンジニア',
            'job_summary': 'Webアプリケーションの設計・開発を担当していただきます。',
            'required_skills': 'JavaScript, React, Node.js',
            'preferred_skills': 'TypeScript, AWS, Docker'
        },
        {
            'job_title': 'バックエンドエンジニア',
            'job_summary': 'サーバーサイドの開発・運用を担当していただきます。',
            'required_skills': 'Python, Django, PostgreSQL',
            'preferred_skills': 'FastAPI, Redis, Kubernetes'
        },
        {
            'job_title': 'フロントエンドエンジニア',
            'job_summary': 'ユーザーインターフェースの設計・実装を担当していただきます。',
            'required_skills': 'HTML, CSS, JavaScript, React',
            'preferred_skills': 'Vue.js, Sass, Figma'
        },
        {
            'job_title': 'データサイエンティスト',
            'job_summary': 'データ分析・機械学習モデルの構築を担当していただきます。',
            'required_skills': 'Python, pandas, scikit-learn',
            'preferred_skills': 'TensorFlow, PyTorch, SQL'
        },
        {
            'job_title': 'UIUXデザイナー',
            'job_summary': 'アプリケーションのデザイン・ユーザー体験の改善を担当していただきます。',
            'required_skills': 'Figma, Adobe XD, Photoshop',
            'preferred_skills': 'Illustrator, Sketch, プロトタイピング'
        },
        {
            'job_title': 'プロジェクトマネージャー',
            'job_summary': 'プロジェクトの計画・進行管理を担当していただきます。',
            'required_skills': 'プロジェクト管理経験, コミュニケーション能力',
            'preferred_skills': 'アジャイル開発, Jira, Confluence'
        },
        {
            'job_title': 'インフラエンジニア',
            'job_summary': 'システムインフラの構築・運用を担当していただきます。',
            'required_skills': 'Linux, AWS, ネットワーク知識',
            'preferred_skills': 'Terraform, Ansible, セキュリティ'
        },
        {
            'job_title': 'QAエンジニア',
            'job_summary': '品質保証・テスト自動化を担当していただきます。',
            'required_skills': 'テスト設計, Selenium, テストケース作成',
            'preferred_skills': 'Jest, Cypress, CI/CD'
        },
        {
            'job_title': 'セキュリティエンジニア',
            'job_summary': 'セキュリティ対策・脆弱性診断を担当していただきます。',
            'required_skills': 'セキュリティ知識, ペネトレーションテスト',
            'preferred_skills': 'CISSP, CEH, 脅威分析'
        },
        {
            'job_title': 'モバイルエンジニア',
            'job_summary': 'iOS/Androidアプリの開発を担当していただきます。',
            'required_skills': 'Swift/Kotlin, モバイルアプリ開発',
            'preferred_skills': 'React Native, Flutter, Firebase'
        }
    ]
    
    # 勤務地
    locations = [
        '東京都', '神奈川県', '大阪府', '愛知県', '福岡県',
        '北海道', '宮城県', '静岡県', '広島県', '沖縄県'
    ]
    
    # リモートオプション
    remote_options = [
        '完全リモート可', 'ハイブリッド（週2-3出社）', 
        'ハイブリッド（週1-2出社）', 'なし', 'なし'
    ]
    
    # 企業文化
    cultures = [
        'フラットな組織文化。意見を自由に言える環境です。',
        'チャレンジを歓迎する文化。失敗を恐れず挑戦できます。',
        'ワークライフバランス重視。残業は月平均20時間以内。',
        '技術力向上を支援。書籍購入・勉強会参加を全額補助。',
        'グローバルな環境。多国籍メンバーと働けます。'
    ]
    
    # 柔軟性
    flexibilities = [
        'フレックスタイム制', 'コアタイムなし', 
        '時短勤務可', '副業OK', '服装自由'
    ]
    
    # 福利厚生
    benefits_list = [
        '社会保険完備、交通費全額支給、リモートワーク手当',
        '社会保険完備、住宅手当、資格取得支援',
        '社会保険完備、フィットネス補助、書籍購入制度',
        '社会保険完備、育児支援、研修制度充実',
        '社会保険完備、ストックオプション、社員食堂'
    ]
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    job_count = 0
    
    # 各企業に5件ずつ求人を作成
    for company_id in range(1, 11):
        for i in range(5):
            template = random.choice(job_templates)
            
            # 年収範囲を設定
            base_salary = random.randint(400, 800)
            salary_min = base_salary
            salary_max = base_salary + random.randint(100, 300)
            
            cur.execute("""
                INSERT INTO company_profile (
                    company_id, job_title, location_prefecture, location_city,
                    salary_min, salary_max, employment_type,
                    job_summary, required_skills, preferred_skills,
                    remote_option, remote_work, company_culture, work_flexibility,
                    benefits, work_hours, holidays,
                    created_at, updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, %s, %s, %s, 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """, (
                company_id,
                template['job_title'],
                random.choice(locations),
                '中央区' if random.random() > 0.5 else '北区',
                salary_min,
                salary_max,
                random.choice(['正社員', '契約社員', '業務委託']),
                template['job_summary'],
                template['required_skills'],
                template['preferred_skills'],
                random.choice(remote_options),
                random.choice(remote_options),
                random.choice(cultures),
                random.choice(flexibilities),
                random.choice(benefits_list),
                '9:00-18:00（フレックス）',
                '週休2日制（土日祝）、年間休日120日以上'
            ))
            
            job_count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"  ✅ {job_count}件の求人を作成")
    print()


def insert_users():
    """ユーザー情報をダミーデータで挿入"""
    print("👤 ユーザー情報を挿入中...")
    
    users = [
        {
            'user_id': 1,
            'name': '山田太郎',
            'email': 'yamada@example.com',
            'password': 'password123',
            'birth_day': '1995-04-15',
            'phone_number': '090-1234-5678',
            'address': '東京都渋谷区道玄坂1-2-3'
        },
        {
            'user_id': 2,
            'name': '佐藤花子',
            'email': 'sato@example.com',
            'password': 'password123',
            'birth_day': '1992-08-22',
            'phone_number': '080-2345-6789',
            'address': '神奈川県横浜市中区本町1-1'
        },
        {
            'user_id': 3,
            'name': '鈴木一郎',
            'email': 'suzuki@example.com',
            'password': 'password123',
            'birth_day': '1988-12-10',
            'phone_number': '070-3456-7890',
            'address': '大阪府大阪市北区梅田2-2-2'
        },
        {
            'user_id': 4,
            'name': '田中美咲',
            'email': 'tanaka@example.com',
            'password': 'password123',
            'birth_day': '1997-03-05',
            'phone_number': '090-4567-8901',
            'address': '福岡県福岡市中央区天神3-3-3'
        },
        {
            'user_id': 5,
            'name': '高橋健太',
            'email': 'takahashi@example.com',
            'password': 'password123',
            'birth_day': '1990-07-18',
            'phone_number': '080-5678-9012',
            'address': '愛知県名古屋市中区栄4-4-4'
        }
    ]
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    for user in users:
        password_hash = generate_password_hash(user['password'])
        
        # personal_date に挿入
        cur.execute("""
            INSERT INTO personal_date (
                id, user_id, email, password_hash, user_name,
                birth_day, phone_number, address,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            user['user_id'],
            user['user_id'],
            user['email'],
            password_hash,
            user['name'],
            user['birth_day'],
            user['phone_number'],
            user['address']
        ))
        
        print(f"  ✅ {user['name']} ({user['email']})")
    
    conn.commit()
    cur.close()
    conn.close()
    print()


def insert_user_profiles():
    """ユーザープロフィールをダミーデータで挿入"""
    print("📋 ユーザープロフィールを挿入中...")
    
    profiles = [
        {
            'user_id': 1,
            'job_title': 'Webエンジニア',
            'location_prefecture': '東京都',
            'salary_min': 500,
            'employment_type': '正社員',
            'remote': '完全リモート可',
            'skills': 'JavaScript, React, Node.js, TypeScript',
            'certifications': '基本情報技術者試験'
        },
        {
            'user_id': 2,
            'job_title': 'データサイエンティスト',
            'location_prefecture': '東京都',
            'salary_min': 600,
            'employment_type': '正社員',
            'remote': 'ハイブリッド',
            'skills': 'Python, Machine Learning, SQL, pandas',
            'certifications': 'G検定, 統計検定2級'
        },
        {
            'user_id': 3,
            'job_title': 'UIUXデザイナー',
            'location_prefecture': '大阪府',
            'salary_min': 450,
            'employment_type': '正社員',
            'remote': 'なし',
            'skills': 'Figma, Adobe XD, Photoshop, UI設計',
            'certifications': 'ウェブデザイン技能検定2級'
        },
        {
            'user_id': 4,
            'job_title': 'バックエンドエンジニア',
            'location_prefecture': '福岡県',
            'salary_min': 550,
            'employment_type': '正社員',
            'remote': 'ハイブリッド',
            'skills': 'Python, Django, PostgreSQL, AWS',
            'certifications': 'AWS認定ソリューションアーキテクト'
        },
        {
            'user_id': 5,
            'job_title': 'プロジェクトマネージャー',
            'location_prefecture': '愛知県',
            'salary_min': 700,
            'employment_type': '正社員',
            'remote': 'なし',
            'skills': 'アジャイル開発, Jira, プロジェクト管理',
            'certifications': 'PMP, 情報処理安全確保支援士'
        }
    ]
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    for profile in profiles:
        cur.execute("""
            INSERT INTO user_profile (
                user_id, job_title, location_prefecture, salary_min,
                employment_type, remote, skills, certifications,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            profile['user_id'],
            profile['job_title'],
            profile['location_prefecture'],
            profile['salary_min'],
            profile['employment_type'],
            profile['remote'],
            profile['skills'],
            profile['certifications']
        ))
        
        print(f"  ✅ ユーザーID {profile['user_id']}: {profile['job_title']}")
    
    conn.commit()
    cur.close()
    conn.close()
    print()


def verify_data():
    """挿入されたデータを確認"""
    print("🔍 データ確認中...")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    # 企業数
    cur.execute("SELECT COUNT(*) FROM company_date")
    company_count = cur.fetchone()[0]
    print(f"  📊 企業数: {company_count}")
    
    # 求人数
    cur.execute("SELECT COUNT(*) FROM company_profile")
    job_count = cur.fetchone()[0]
    print(f"  📊 求人数: {job_count}")
    
    # ユーザー数
    cur.execute("SELECT COUNT(*) FROM personal_date")
    user_count = cur.fetchone()[0]
    print(f"  📊 ユーザー数: {user_count}")
    
    # プロフィール数
    cur.execute("SELECT COUNT(*) FROM user_profile")
    profile_count = cur.fetchone()[0]
    print(f"  📊 プロフィール数: {profile_count}")
    
    cur.close()
    conn.close()
    print()


def main():
    """メイン処理"""
    print("=" * 70)
    print("🚀 JobMatch AI - ダミーデータ挿入スクリプト")
    print("=" * 70)
    print()
    
    # 確認メッセージ
    print("⚠️  このスクリプトは全テーブルのデータをクリアして、")
    print("   ダミーデータを挿入します。")
    print()
    response = input("続行しますか？ (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ キャンセルしました")
        return
    
    print()
    
    try:
        # 既存データをクリア
        clear_all_tables()
        
        # データ挿入
        insert_companies()
        insert_jobs()
        insert_users()
        insert_user_profiles()
        
        # データ確認
        verify_data()
        
        print("=" * 70)
        print("✅ ダミーデータの挿入が完了しました！")
        print("=" * 70)
        print()
        print("📝 挿入されたデータ:")
        print("  - 企業: 10社")
        print("  - 求人: 50件")
        print("  - ユーザー: 5名")
        print("  - プロフィール: 5件")
        print()
        print("🔐 テストユーザー:")
        print("  Email: yamada@example.com")
        print("  Password: password123")
        print()
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
