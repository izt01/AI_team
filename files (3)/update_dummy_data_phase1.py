"""
JobMatch AI - Phase 1: ダミーデータ更新スクリプト

既存の求人データに、Phase 1で追加した新規カラムのデータを追加します。

実行方法:
python update_dummy_data_phase1.py
"""

import random
from db_config import get_db_conn


def update_existing_jobs_phase1():
    """既存求人データにPhase 1の新規カラムデータを追加"""
    
    print("=" * 70)
    print("🚀 Phase 1: ダミーデータ更新開始")
    print("=" * 70)
    print()
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    # 既存の全求人を取得
    cur.execute("SELECT id FROM company_profile")
    job_ids = [row[0] for row in cur.fetchall()]
    
    print(f"📊 更新対象: {len(job_ids)}件の求人")
    print()
    
    # データパターンを定義
    tech_stacks = [
        {
            "languages": ["Python", "JavaScript", "TypeScript"],
            "frameworks": ["Django", "React", "Next.js"],
            "databases": ["PostgreSQL", "Redis"],
            "infrastructure": ["AWS", "Docker", "Kubernetes"],
            "tools": ["GitHub", "Jira", "Slack"],
            "version_control": "Git",
            "ci_cd": ["GitHub Actions", "CircleCI"]
        },
        {
            "languages": ["Java", "Kotlin", "TypeScript"],
            "frameworks": ["Spring Boot", "Vue.js", "Nuxt.js"],
            "databases": ["MySQL", "MongoDB"],
            "infrastructure": ["GCP", "Docker"],
            "tools": ["GitLab", "Confluence", "Teams"],
            "version_control": "Git",
            "ci_cd": ["GitLab CI"]
        },
        {
            "languages": ["Ruby", "JavaScript"],
            "frameworks": ["Ruby on Rails", "React"],
            "databases": ["PostgreSQL"],
            "infrastructure": ["Heroku", "AWS"],
            "tools": ["GitHub", "Slack", "Notion"],
            "version_control": "Git",
            "ci_cd": ["GitHub Actions"]
        },
        {
            "languages": ["Go", "TypeScript"],
            "frameworks": ["Echo", "Next.js"],
            "databases": ["PostgreSQL", "Redis"],
            "infrastructure": ["AWS", "Kubernetes"],
            "tools": ["GitHub", "Slack"],
            "version_control": "Git",
            "ci_cd": ["CircleCI"]
        },
        {
            "languages": ["PHP", "JavaScript"],
            "frameworks": ["Laravel", "Vue.js"],
            "databases": ["MySQL"],
            "infrastructure": ["AWS"],
            "tools": ["GitHub", "Backlog"],
            "version_control": "Git",
            "ci_cd": ["Jenkins"]
        }
    ]
    
    dress_codes = ['自由', 'オフィスカジュアル', 'ビジネスカジュアル']
    team_sizes = ['3-5名', '5-10名', '10-15名', '15-20名', '20名以上']
    development_methods = ['アジャイル', 'スクラム', 'カンバン', 'ウォーターフォール', 'ハイブリッド']
    study_frequencies = ['週1回', '月2回', '月1回', '隔週', '不定期']
    project_scales = ['小規模', '中規模', '大規模', '複数プロジェクト']
    
    training_programs = [
        '入社時3ヶ月の新人研修プログラム、OJTによるスキルアップ支援',
        'メンター制度による1on1サポート、定期的な技術勉強会',
        'オンライン研修サービス（Udemy等）の受講支援',
        '社内勉強会と外部セミナー参加の推奨',
        'エンジニア向けキャリアパス研修'
    ]
    
    evaluation_systems = [
        '半期ごとの目標設定と評価、360度フィードバック',
        '四半期ごとのOKR評価、1on1での定期フィードバック',
        '年2回の評価面談、スキルマトリクスによる評価',
        '実績ベースの評価制度、ピアレビューの導入',
        '定量・定性評価の組み合わせ、成長支援型評価'
    ]
    
    career_paths = [
        'エンジニア→シニアエンジニア→テックリード→アーキテクト',
        'エンジニア→チームリーダー→エンジニアリングマネージャー',
        'スペシャリストとマネージャーの両方のキャリアパスを選択可能',
        '技術力を極めるスペシャリスト路線も用意',
        'ジョブローテーションによる多様なキャリア形成支援'
    ]
    
    pc_specs = [
        'MacBook Pro (M3, 16GB RAM) または Windows (同等スペック) 選択可',
        'MacBook Pro (M2, 32GB RAM) 支給',
        'Windows PC (Core i7, 16GB RAM) 支給',
        'MacBook Air (M2) または ThinkPad 選択可',
        'ハイスペックデスクトップ PC 支給'
    ]
    
    office_facilities_list = [
        'フリードリンク、休憩スペース、マッサージチェア完備',
        'カフェスペース、仮眠室、シャワールーム',
        'フリーアドレス、集中ブース、会議室多数',
        '最新オフィス家具、緑豊かな環境、屋上テラス',
        '開放的なオープンスペース、電動昇降デスク'
    ]
    
    team_structures = [
        'フロントエンド2名、バックエンド3名、デザイナー1名、PO1名の構成',
        '少数精鋭のスクラムチーム（5-7名）',
        'クロスファンクショナルチーム（エンジニア、デザイナー、PO混在）',
        'フルスタックエンジニア中心のチーム',
        '機能別チーム構成、専門性の高いメンバー'
    ]
    
    development_processes = [
        '2週間スプリント、デイリースタンドアップ、スプリントレビュー実施',
        'カンバン方式、WIPリミット設定、定期的なふりかえり',
        'アジャイル開発、CI/CD自動化、コードレビュー必須',
        'スクラム開発、ペアプログラミング・モブプログラミング実施',
        'ウォーターフォール基本だが、一部アジャイル要素を取り入れ'
    ]
    
    updated_count = 0
    
    for job_id in job_ids:
        # ランダムにデータを選択
        flex_time = random.choice([True, True, False])  # 66%がフレックス
        core_time = random.choice(['10:00-15:00', '11:00-15:00', '11:00-16:00', None])
        earliest_start = random.choice(['07:00', '08:00', '09:00'])
        latest_start = random.choice(['10:00', '10:30', '11:00'])
        part_time = random.choice([True, False, False])  # 33%が時短可
        side_job = random.choice([True, True, False])  # 66%が副業可
        dress_code = random.choice(dress_codes)
        
        team_size = random.choice(team_sizes)
        average_age = random.randint(28, 38)
        foreign_ratio = random.randint(0, 30)
        female_ratio = random.randint(10, 50)
        dev_method = random.choice(development_methods)
        
        training = random.choice(training_programs)
        study_freq = random.choice(study_frequencies)
        conference = random.choice([True, True, False])
        book_budget = random.choice([5000, 10000, 15000, 0])
        mentor = random.choice([True, True, False])
        
        evaluation = random.choice(evaluation_systems)
        salary_review = random.choice(['年1回', '年2回', '半期ごと'])
        career = random.choice(career_paths)
        promotion = '実績とスキル評価に基づく公平な昇進基準'
        
        remote_allowance = random.choice([5000, 10000, 15000, 0])
        housing = random.choice([0, 20000, 30000, 50000])
        commute_limit = random.choice([30000, 50000, 100000])
        retirement = random.choice([True, False])
        
        pc = random.choice(pc_specs)
        monitors = random.choice([1, 2, 2, 3])
        facilities = random.choice(office_facilities_list)
        quiet = random.choice([True, False])
        
        tech_stack = random.choice(tech_stacks)
        project = random.choice(project_scales)
        team_struct = random.choice(team_structures)
        dev_process = random.choice(development_processes)
        
        # データ更新
        cur.execute("""
            UPDATE company_profile
            SET 
                flex_time = %s,
                core_time = %s,
                earliest_start_time = %s,
                latest_start_time = %s,
                part_time_available = %s,
                side_job_allowed = %s,
                dress_code = %s,
                
                team_size = %s,
                average_age = %s,
                foreign_ratio = %s,
                female_ratio = %s,
                development_method = %s,
                
                training_program = %s,
                study_session_frequency = %s,
                conference_support = %s,
                book_purchase_budget = %s,
                mentor_system = %s,
                
                evaluation_system = %s,
                salary_review_frequency = %s,
                career_path = %s,
                promotion_criteria = %s,
                
                remote_work_allowance = %s,
                housing_allowance = %s,
                commute_allowance_limit = %s,
                retirement_plan = %s,
                
                pc_spec = %s,
                monitor_count = %s,
                office_facilities = %s,
                quiet_workspace = %s,
                
                tech_stack = %s,
                project_scale = %s,
                team_structure = %s,
                development_process = %s,
                
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (
            flex_time, core_time, earliest_start, latest_start,
            part_time, side_job, dress_code,
            team_size, average_age, foreign_ratio, female_ratio, dev_method,
            training, study_freq, conference, book_budget, mentor,
            evaluation, salary_review, career, promotion,
            remote_allowance, housing, commute_limit, retirement,
            pc, monitors, facilities, quiet,
            str(tech_stack).replace("'", '"'),  # JSONBフォーマット
            project, team_struct, dev_process,
            job_id
        ))
        
        updated_count += 1
        
        if updated_count % 10 == 0:
            print(f"  ✅ {updated_count}/{len(job_ids)} 件更新...")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print()
    print(f"✅ 合計 {updated_count} 件の求人データを更新しました")
    print()
    
    # 確認
    verify_phase1_data()
    
    print("=" * 70)
    print("✅ Phase 1: ダミーデータ更新完了！")
    print("=" * 70)


def verify_phase1_data():
    """Phase 1データの確認"""
    print("🔍 データ確認中...")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    # フレックスタイム率
    cur.execute("SELECT COUNT(*) FROM company_profile WHERE flex_time = TRUE")
    flex_count = cur.fetchone()[0]
    
    # 副業可率
    cur.execute("SELECT COUNT(*) FROM company_profile WHERE side_job_allowed = TRUE")
    side_job_count = cur.fetchone()[0]
    
    # 総求人数
    cur.execute("SELECT COUNT(*) FROM company_profile")
    total_count = cur.fetchone()[0]
    
    print(f"  📊 フレックスタイム制: {flex_count}/{total_count}件 ({flex_count/total_count*100:.1f}%)")
    print(f"  📊 副業可: {side_job_count}/{total_count}件 ({side_job_count/total_count*100:.1f}%)")
    
    # サンプルデータ表示
    cur.execute("""
        SELECT 
            id,
            job_title,
            flex_time,
            latest_start_time,
            side_job_allowed,
            team_size,
            development_method
        FROM company_profile
        LIMIT 3
    """)
    
    print()
    print("  🔍 サンプルデータ（3件）:")
    for row in cur.fetchall():
        print(f"    - ID:{row[0]} {row[1]}")
        print(f"      フレックス:{row[2]}, 最遅出社:{row[3]}, 副業:{row[4]}")
        print(f"      チーム:{row[5]}, 開発手法:{row[6]}")
    
    cur.close()
    conn.close()
    print()


if __name__ == "__main__":
    try:
        update_existing_jobs_phase1()
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
