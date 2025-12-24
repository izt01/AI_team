"""
AIスカウト検索の動作確認スクリプト

このスクリプトで以下を確認：
1. ダミーユーザーデータの存在
2. 性格分析データの存在
3. 検索が正しく動作するか
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from db_config import get_db_conn

def check_data():
    """データの存在を確認"""
    
    print("\n" + "="*60)
    print("📊 AIスカウト検索 - データ確認")
    print("="*60)
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. ユーザー数の確認
    print("\n1️⃣ ユーザーデータの確認")
    print("-" * 60)
    
    cur.execute("SELECT COUNT(*) as count FROM personal_date")
    user_count = cur.fetchone()['count']
    print(f"✅ personal_date: {user_count:,}件")
    
    cur.execute("SELECT COUNT(*) as count FROM user_profile WHERE job_title IS NOT NULL")
    profile_count = cur.fetchone()['count']
    print(f"✅ user_profile (職種あり): {profile_count:,}件")
    
    # 2. 性格分析データの確認
    print("\n2️⃣ 性格分析データの確認")
    print("-" * 60)
    
    cur.execute("SELECT COUNT(*) as count FROM user_personality_analysis")
    analysis_count = cur.fetchone()['count']
    print(f"{'✅' if analysis_count > 0 else '❌'} user_personality_analysis: {analysis_count:,}件")
    
    if analysis_count == 0:
        print("\n⚠️  警告: 性格分析データがありません！")
        print("   AIスカウト検索を使うには、まず性格分析データを生成してください。")
        print("   実行: python generate_scout_dummy_data.py")
        return False
    
    # 3. サンプルデータの表示
    print("\n3️⃣ サンプルユーザーデータ")
    print("-" * 60)
    
    cur.execute("""
        SELECT 
            pd.user_id,
            pd.user_name,
            up.job_title,
            up.location_prefecture,
            up.salary_min,
            upa.analysis_data->>'career_orientation' as career_orientation,
            upa.analysis_data->'personality_traits' as personality_traits
        FROM personal_date pd
        LEFT JOIN user_profile up ON pd.user_id = up.user_id
        LEFT JOIN user_personality_analysis upa ON pd.user_id = upa.user_id
        WHERE upa.analysis_data IS NOT NULL
        LIMIT 5
    """)
    
    samples = cur.fetchall()
    
    if not samples:
        print("❌ 検索可能なユーザーが見つかりません")
        return False
    
    for i, user in enumerate(samples, 1):
        print(f"\n【ユーザー {i}】")
        print(f"  ID: {user['user_id']}")
        print(f"  名前: {user['user_name'] or '未設定'}")
        print(f"  職種: {user['job_title'] or '未設定'}")
        print(f"  勤務地: {user['location_prefecture'] or '未設定'}")
        print(f"  希望年収: {user['salary_min'] or '未設定'}万円")
        print(f"  キャリア志向: {user['career_orientation'] or '未設定'}")
        
        import json
        # PostgreSQLのJSONBは既にリスト型で返されることがある
        if user['personality_traits']:
            if isinstance(user['personality_traits'], str):
                traits = json.loads(user['personality_traits'])
            else:
                traits = user['personality_traits']
        else:
            traits = []
        print(f"  性格特性: {', '.join(traits[:3]) if traits else '未設定'}")
    
    # 4. 職種別の分布
    print("\n4️⃣ 職種別のユーザー分布")
    print("-" * 60)
    
    cur.execute("""
        SELECT 
            up.job_title,
            COUNT(*) as count
        FROM user_profile up
        JOIN user_personality_analysis upa ON up.user_id = upa.user_id
        WHERE up.job_title IS NOT NULL
        GROUP BY up.job_title
        ORDER BY count DESC
        LIMIT 10
    """)
    
    job_stats = cur.fetchall()
    
    if job_stats:
        for job in job_stats:
            print(f"  {job['job_title']}: {job['count']:,}名")
    else:
        print("  データなし")
    
    # 5. 勤務地別の分布
    print("\n5️⃣ 勤務地別のユーザー分布")
    print("-" * 60)
    
    cur.execute("""
        SELECT 
            up.location_prefecture,
            COUNT(*) as count
        FROM user_profile up
        JOIN user_personality_analysis upa ON up.user_id = upa.user_id
        WHERE up.location_prefecture IS NOT NULL
        GROUP BY up.location_prefecture
        ORDER BY count DESC
        LIMIT 10
    """)
    
    location_stats = cur.fetchall()
    
    if location_stats:
        for loc in location_stats:
            print(f"  {loc['location_prefecture']}: {loc['count']:,}名")
    else:
        print("  データなし")
    
    # 6. キャリア志向別の分布
    print("\n6️⃣ キャリア志向別のユーザー分布")
    print("-" * 60)
    
    cur.execute("""
        SELECT 
            analysis_data->>'career_orientation' as career_orientation,
            COUNT(*) as count
        FROM user_personality_analysis
        WHERE analysis_data->>'career_orientation' IS NOT NULL
        GROUP BY analysis_data->>'career_orientation'
        ORDER BY count DESC
    """)
    
    career_stats = cur.fetchall()
    
    if career_stats:
        for career in career_stats:
            print(f"  {career['career_orientation']}: {career['count']:,}名")
    else:
        print("  データなし")
    
    cur.close()
    conn.close()
    
    # 7. 検索テスト
    print("\n7️⃣ 検索テスト")
    print("-" * 60)
    
    if samples:
        print("\n✅ データは正常です！")
        print("\nAIスカウト検索で以下のような条件で検索できます:")
        print("  • 「エンジニアを探しています」")
        print("  • 「東京で働ける人」")
        print("  • 「挑戦志向の人材」")
        print("  • 「協調性が高い人」")
        return True
    else:
        print("\n❌ 検索可能なデータがありません")
        return False


def test_search_query():
    """実際の検索クエリをテスト"""
    
    print("\n" + "="*60)
    print("🔍 検索クエリのテスト")
    print("="*60)
    
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # テストケース1: エンジニア検索
    print("\n【テストケース1: エンジニア検索】")
    print("-" * 60)
    
    cur.execute("""
        SELECT 
            pd.user_id,
            pd.user_name,
            up.job_title,
            up.location_prefecture,
            upa.analysis_data->>'summary' as summary
        FROM personal_date pd
        JOIN user_profile up ON pd.user_id = up.user_id
        JOIN user_personality_analysis upa ON pd.user_id = upa.user_id
        WHERE up.job_title ILIKE %s
          AND upa.analysis_data IS NOT NULL
        LIMIT 3
    """, ('%エンジニア%',))
    
    results = cur.fetchall()
    
    if results:
        print(f"✅ 検索結果: {len(results)}件")
        for user in results:
            print(f"\n  • {user['user_name']} ({user['job_title']})")
            print(f"    {user['location_prefecture']}")
    else:
        print("❌ 該当者なし")
    
    # テストケース2: 東京で検索
    print("\n【テストケース2: 東京勤務希望者検索】")
    print("-" * 60)
    
    cur.execute("""
        SELECT 
            pd.user_id,
            pd.user_name,
            up.job_title,
            up.location_prefecture
        FROM personal_date pd
        JOIN user_profile up ON pd.user_id = up.user_id
        JOIN user_personality_analysis upa ON pd.user_id = upa.user_id
        WHERE up.location_prefecture ILIKE %s
          AND upa.analysis_data IS NOT NULL
        LIMIT 3
    """, ('%東京%',))
    
    results = cur.fetchall()
    
    if results:
        print(f"✅ 検索結果: {len(results)}件")
        for user in results:
            print(f"  • {user['user_name']} ({user['job_title']})")
    else:
        print("❌ 該当者なし")
    
    # テストケース3: 性格特性で検索
    print("\n【テストケース3: 性格特性で検索】")
    print("-" * 60)
    print("検索条件: 協調性が高い")
    
    cur.execute("""
        SELECT 
            pd.user_id,
            pd.user_name,
            up.job_title,
            upa.analysis_data->'personality_traits' as traits
        FROM personal_date pd
        JOIN user_profile up ON pd.user_id = up.user_id
        JOIN user_personality_analysis upa ON pd.user_id = upa.user_id
        WHERE upa.analysis_data->'personality_traits' @> '["協調性が高い"]'::jsonb
        LIMIT 3
    """)
    
    results = cur.fetchall()
    
    if results:
        print(f"✅ 検索結果: {len(results)}件")
        import json
        for user in results:
            # PostgreSQLのJSONBは既にリスト型で返されることがある
            if user['traits']:
                if isinstance(user['traits'], str):
                    traits = json.loads(user['traits'])
                else:
                    traits = user['traits']
            else:
                traits = []
            print(f"  • {user['user_name']} - {', '.join(traits)}")
    else:
        print("❌ 該当者なし")
    
    cur.close()
    conn.close()


def main():
    """メイン実行"""
    
    try:
        # データ確認
        data_ok = check_data()
        
        if data_ok:
            # 検索テスト
            test_search_query()
            
            print("\n" + "="*60)
            print("✅ すべての確認が完了しました！")
            print("="*60)
            print("\nAIスカウト検索を使用できます:")
            print("  1. ブラウザで http://localhost:5001/scout/ai-search にアクセス")
            print("  2. AIと会話して候補者を検索")
            print("  3. マッチした候補者が表示されます")
            
        else:
            print("\n" + "="*60)
            print("❌ データが不足しています")
            print("="*60)
            print("\n修正方法:")
            print("  1. ダミーデータを生成:")
            print("     python generate_scout_dummy_data.py")
            print("\n  2. 再度このスクリプトを実行:")
            print("     python check_scout_search.py")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()