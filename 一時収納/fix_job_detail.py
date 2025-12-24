"""
company_app_enhanced.py の job_detail 関数修正

company変数を追加して、テンプレートエラーを解消
"""

# ============================================
# company_app_enhanced.py の修正箇所
# ============================================

# 修正前のコード（271行目あたり）
"""
@app.route('/job/<job_id>')
def job_detail(job_id):
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute(\"\"\"
        SELECT * FROM company_profile WHERE id = %s
    \"\"\", (job_id,))
    
    job = cur.fetchone()
    
    if not job:
        cur.close()
        conn.close()
        return "求人が見つかりません", 404
    
    cur.close()
    conn.close()
    
    return render_template("job_detail.html", job=job)  # ← ここがエラー
"""

# ============================================
# 修正後のコード
# ============================================

@app.route('/job/<job_id>')
def job_detail(job_id):
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 求人情報を取得
    cur.execute("""
        SELECT * FROM company_profile WHERE id = %s
    """, (job_id,))
    
    job = cur.fetchone()
    
    if not job:
        cur.close()
        conn.close()
        return "求人が見つかりません", 404
    
    # company情報を作成（company_profileから）
    company = {
        'company_name': job.get('company_name', '企業名非公開'),
        'company_id': job.get('company_id'),
        'industry': job.get('industry'),
        'company_size': job.get('company_size'),
        'website': job.get('website')
    }
    
    cur.close()
    conn.close()
    
    # jobとcompanyの両方を渡す
    return render_template("job_detail.html", job=job, company=company)


# ============================================
# 使い方
# ============================================

"""
1. company_app_enhanced.py を開く
2. job_detail 関数を見つける（271行目あたり）
3. 上記の「修正後のコード」に置き換える
4. ファイルを保存
5. アプリを再起動: python company_app_enhanced.py
"""

# ============================================
# または、このスクリプトで自動修正
# ============================================

def apply_fix():
    """自動修正を適用"""
    import re
    
    file_path = "company_app_enhanced.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修正前のパターンを検索
        old_pattern = r'(def job_detail\(job_id\):.*?return render_template\("job_detail\.html", job=job\))'
        
        # 修正後のコード
        new_code = '''def job_detail(job_id):
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 求人情報を取得
    cur.execute("""
        SELECT * FROM company_profile WHERE id = %s
    """, (job_id,))
    
    job = cur.fetchone()
    
    if not job:
        cur.close()
        conn.close()
        return "求人が見つかりません", 404
    
    # company情報を作成
    company = {
        'company_name': job.get('company_name', '企業名非公開'),
        'company_id': job.get('company_id'),
        'industry': job.get('industry'),
        'company_size': job.get('company_size'),
        'website': job.get('website')
    }
    
    cur.close()
    conn.close()
    
    # jobとcompanyの両方を渡す
    return render_template("job_detail.html", job=job, company=company)'''
        
        # 正規表現で置換
        if re.search(old_pattern, content, re.DOTALL):
            content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)
            
            # ファイルに書き込み
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 修正完了！")
            print("   company_app_enhanced.pyを再起動してください")
            return True
        else:
            print("⚠️  パターンが見つかりませんでした")
            print("   手動で修正してください")
            return False
            
    except FileNotFoundError:
        print(f"❌ {file_path} が見つかりません")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("🔧 job_detail 関数修正ツール")
    print("=" * 70)
    print()
    print("このスクリプトは、company変数が渡されないエラーを修正します")
    print()
    
    response = input("自動修正を実行しますか？ (y/n): ")
    
    if response.lower() == 'y':
        apply_fix()
    else:
        print("\n手動修正方法:")
        print("1. company_app_enhanced.py を開く")
        print("2. job_detail 関数（271行目あたり）を見つける")
        print("3. 以下のように修正:")
        print()
        print("   # 修正前")
        print('   return render_template("job_detail.html", job=job)')
        print()
        print("   # 修正後")
        print("   company = {'company_name': job.get('company_name', '企業名非公開')}")
        print('   return render_template("job_detail.html", job=job, company=company)')