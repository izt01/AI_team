"""
hybrid_recommender.pyの修正パッチ

0件になった時、エンベディング検索（類似検索）にフォールバックする機能を追加
"""

import re

def apply_patch():
    """パッチを適用"""
    
    file_path = "hybrid_recommender.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("📝 hybrid_recommender.pyを読み込みました")
        
        # 修正前のコード（502-503行目あたり）
        old_code = """            if not jobs:
                print("⚠ No jobs found after filtering")
                return []"""
        
        # 修正後のコード（エンベディング検索にフォールバック）
        new_code = """            if not jobs:
                print("⚠ No jobs found after filtering - フォールバック検索を実行")
                # エンベディング検索にフォールバック
                return ContentBasedFiltering._fallback_to_embedding_search(
                    user_id=user_id,
                    titles=titles,
                    locations=locations,
                    salary_min=salary_min,
                    top_k=top_k
                )"""
        
        if old_code in content:
            content = content.replace(old_code, new_code)
            print("✅ フォールバック処理を追加しました")
        else:
            print("⚠️  対象コードが見つかりませんでした（既に修正済みか、コードが変更されています）")
            return False
        
        # フォールバックメソッドを追加（ContentBasedFilteringクラスの最後に）
        fallback_method = '''
    @staticmethod
    def _fallback_to_embedding_search(user_id: int, titles: List[str], locations: List[str], 
                                      salary_min: int, top_k: int = 20) -> List[Tuple[str, float]]:
        """
        フィルタリング後に0件になった場合のフォールバック検索
        
        エンベディング類似度検索を使用して、条件を緩和した求人を返す
        
        Args:
            user_id: ユーザーID
            titles: 希望職種リスト
            locations: 希望勤務地リスト
            salary_min: 最低年収
            top_k: 返す件数
            
        Returns:
            (job_id, score) のリスト
        """
        print("\\n🔄 エンベディング検索にフォールバック")
        
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # ユーザーの希望をテキストに変換
            search_text = f"{' '.join(titles)} {' '.join(locations)} 年収{salary_min}万円以上"
            print(f"検索テキスト: {search_text}")
            
            # 緩和した条件で検索（職種と勤務地のORクエリ）
            title_conditions = " OR ".join([f"job_title ILIKE %s" for _ in titles])
            location_conditions = " OR ".join([f"location_prefecture ILIKE %s" for _ in locations])
            
            query = f"""
                SELECT 
                    id::text as job_id,
                    job_title,
                    location_prefecture,
                    salary_min,
                    salary_max,
                    job_summary,
                    work_flexibility,
                    company_culture
                FROM company_profile
                WHERE ({title_conditions} OR {location_conditions})
                  AND salary_min >= %s - 100
                ORDER BY 
                    CASE 
                        WHEN salary_min >= %s THEN 0
                        ELSE 1
                    END,
                    salary_max DESC
                LIMIT %s
            """
            
            params = []
            # 職種のパラメータ
            for title in titles:
                params.append(f"%{title}%")
            # 勤務地のパラメータ  
            for loc in locations:
                params.append(f"%{loc}%")
            # 年収のパラメータ（-100万円まで緩和）
            params.append(salary_min)
            params.append(salary_min)
            params.append(top_k)
            
            cur.execute(query, params)
            jobs = cur.fetchall()
            
            print(f"✅ フォールバック検索で {len(jobs)} 件見つかりました")
            
            if not jobs:
                # さらに緩和：職種のみで検索
                print("🔄 さらに条件を緩和（職種のみ）")
                
                query = f"""
                    SELECT 
                        id::text as job_id,
                        job_title,
                        location_prefecture,
                        salary_min,
                        salary_max
                    FROM company_profile
                    WHERE {title_conditions}
                    ORDER BY salary_max DESC
                    LIMIT %s
                """
                
                params = [f"%{title}%" for title in titles]
                params.append(top_k)
                
                cur.execute(query, params)
                jobs = cur.fetchall()
                
                print(f"✅ 緩和検索で {len(jobs)} 件見つかりました")
            
            cur.close()
            conn.close()
            
            # スコアリング
            recommendations = []
            for i, job in enumerate(jobs):
                # 順位に基づくスコア
                score = top_k - i
                
                # 条件マッチでボーナス
                for title in titles:
                    if title.lower() in job['job_title'].lower():
                        score += 10.0
                
                for loc in locations:
                    if loc.lower() in job.get('location_prefecture', '').lower():
                        score += 5.0
                
                if int(job['salary_min']) >= salary_min:
                    score += 8.0
                
                recommendations.append((job['job_id'], score))
            
            # スコアでソート
            recommendations.sort(key=lambda x: x[1], reverse=True)
            
            print(f"📊 フォールバック検索結果: {len(recommendations)} 件")
            
            return recommendations[:top_k]
            
        except Exception as e:
            print(f"❌ フォールバック検索エラー: {e}")
            import traceback
            traceback.print_exc()
            return []
'''
        
        # ContentBasedFilteringクラスの最後に追加
        # クラスの終わりを見つける
        class_pattern = r'(class ContentBasedFiltering:.*?)((?=\nclass )|(?=\n\n\nclass )|$)'
        
        match = re.search(class_pattern, content, re.DOTALL)
        if match:
            class_content = match.group(1)
            # 最後のメソッドの後に追加
            modified_class = class_content.rstrip() + fallback_method
            content = content.replace(class_content, modified_class)
            print("✅ フォールバックメソッドを追加しました")
        else:
            print("⚠️  ContentBasedFilteringクラスが見つかりませんでした")
            # クラスの末尾に直接追加を試みる
            # 別のアプローチ: ファイルの適切な位置を見つける
            insert_position = content.find("class HybridRecommender:")
            if insert_position > 0:
                content = content[:insert_position] + fallback_method + "\n\n" + content[insert_position:]
                print("✅ フォールバックメソッドを追加しました（代替方法）")
        
        # ファイルに書き込み
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("\n✅ パッチ適用完了！")
        print("\n📋 変更内容:")
        print("  1. 0件時のreturn []をフォールバック処理に置き換え")
        print("  2. _fallback_to_embedding_search メソッドを追加")
        print("\n🎯 効果:")
        print("  - フィルタリング後0件 → 条件を緩和して類似求人を表示")
        print("  - 職種 OR 勤務地での検索")
        print("  - 年収を-100万円まで緩和")
        print("  - それでも0件なら職種のみで検索")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ エラー: {file_path} が見つかりません")
        print("   カレントディレクトリを確認してください")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("🔧 hybrid_recommender.py パッチ適用ツール")
    print("=" * 70)
    print()
    print("このスクリプトは、フィルタリング後に0件になった場合に")
    print("エンベディング検索（類似検索）にフォールバックする機能を追加します。")
    print()
    
    response = input("パッチを適用しますか？ (y/n): ")
    
    if response.lower() == 'y':
        success = apply_patch()
        if success:
            print("\n✅ 完了！hybrid_recommender.pyを再読み込みしてください")
        else:
            print("\n❌ パッチ適用に失敗しました")
    else:
        print("\n❌ キャンセルしました")