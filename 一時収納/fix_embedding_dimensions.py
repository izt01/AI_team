"""
エンベディングベクトルの次元数を修正（既存データ対応版）

company_profileテーブルのembedding列を768次元から1536次元に変更
既存の768次元データをクリアしてから変更
"""

import psycopg2

def fix_embedding_dimensions():
    """embedding列の次元数を1536に変更（既存データクリア版）"""
    
    try:
        # データベース接続
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="jobmatch",
            user="devuser",
            password="devpass"
        )
        
        cur = conn.cursor()
        
        print("🔄 embedding列の次元数を確認中...")
        
        # 現在の型を確認
        cur.execute("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'company_profile' 
            AND column_name = 'embedding';
        """)
        
        result = cur.fetchone()
        if result:
            print(f"現在の設定: {result}")
        
        # embeddingデータがあるか確認
        cur.execute("""
            SELECT COUNT(*) FROM company_profile WHERE embedding IS NOT NULL;
        """)
        
        count = cur.fetchone()[0]
        print(f"\n📊 既存embeddingデータ: {count}件")
        
        if count > 0:
            print("\n⚠️  既存の768次元embeddingデータが存在します")
            print("   次元数を変更するには、既存データをクリアする必要があります")
            
            response = input("\n既存embeddingデータをクリアしますか？ (y/n): ")
            
            if response.lower() != 'y':
                print("\n❌ キャンセルしました")
                return False
            
            print("\n🗑️  既存embeddingデータをクリア中...")
            
            # embeddingをNULLに設定
            cur.execute("""
                UPDATE company_profile SET embedding = NULL;
            """)
            
            conn.commit()
            
            print(f"✅ {count}件のembeddingをクリアしました")
        
        print("\n🔧 embedding列を1536次元に変更中...")
        
        # 次元数を変更
        cur.execute("""
            ALTER TABLE company_profile 
            ALTER COLUMN embedding TYPE vector(1536);
        """)
        
        conn.commit()
        
        print("✅ 変更完了！")
        
        # 変更後を確認
        cur.execute("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'company_profile' 
            AND column_name = 'embedding';
        """)
        
        result = cur.fetchone()
        print(f"変更後: {result}")
        
        cur.close()
        conn.close()
        
        print("\n📊 注意事項:")
        print("  - 既存のembeddingデータはクリアされました")
        print("  - 求人を再登録するとembeddingが再生成されます")
        print("  - または既存データのembeddingを再計算できます（次のステップ）")
        
        return True
        
    except psycopg2.errors.UndefinedObject as e:
        print(f"❌ エラー: vector型が見つかりません")
        print("   pgvector拡張がインストールされているか確認してください")
        print(f"   詳細: {e}")
        return False
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        return False


def regenerate_embeddings():
    """既存求人のembeddingを再生成"""
    
    try:
        import openai
        import os
        
        # OpenAI APIキーの確認
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  OPENAI_API_KEYが設定されていません")
            print("   環境変数を設定するか、.envファイルを作成してください")
            return False
        
        openai.api_key = api_key
        
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="jobmatch",
            user="devuser",
            password="devpass"
        )
        
        cur = conn.cursor()
        
        print("\n🔄 既存求人のembeddingを再生成中...")
        
        # embeddingがNULLの求人を取得
        cur.execute("""
            SELECT id, job_title, job_summary
            FROM company_profile
            WHERE embedding IS NULL
            ORDER BY created_at DESC
            LIMIT 100;
        """)
        
        jobs = cur.fetchall()
        
        if not jobs:
            print("✅ 再生成が必要な求人はありません")
            return True
        
        print(f"📝 {len(jobs)}件の求人のembeddingを再生成します...")
        
        success_count = 0
        error_count = 0
        
        for i, job in enumerate(jobs, 1):
            job_id, title, summary = job
            
            try:
                # テキストを結合
                text = f"{title} {summary or ''}"
                
                # embeddingを生成
                response = openai.Embedding.create(
                    model="text-embedding-3-small",
                    input=text
                )
                
                embedding = response['data'][0]['embedding']
                
                # 更新
                cur.execute("""
                    UPDATE company_profile
                    SET embedding = %s
                    WHERE id = %s
                """, (embedding, job_id))
                
                conn.commit()
                
                print(f"  [{i}/{len(jobs)}] ✓ {title}")
                success_count += 1
                
            except Exception as e:
                print(f"  [{i}/{len(jobs)}] ✗ {title}: {e}")
                error_count += 1
                continue
        
        print(f"\n✅ 完了: 成功 {success_count}件, 失敗 {error_count}件")
        
        cur.close()
        conn.close()
        
        return True
        
    except ImportError:
        print("⚠️  openaiライブラリがインストールされていません")
        print("   pip install openai でインストールしてください")
        return False
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_current_status():
    """現在の状態を確認"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="jobmatch",
            user="devuser",
            password="devpass"
        )
        
        cur = conn.cursor()
        
        print("\n📊 現在の状態:")
        print("-" * 50)
        
        # テーブルの統計
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(embedding) as with_embedding,
                COUNT(*) - COUNT(embedding) as without_embedding
            FROM company_profile;
        """)
        
        stats = cur.fetchone()
        print(f"  総求人数: {stats[0]}件")
        print(f"  embedding有: {stats[1]}件")
        print(f"  embedding無: {stats[2]}件")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"⚠️  状態確認エラー: {e}")


if __name__ == "__main__":
    print("=" * 70)
    print("🔧 エンベディング次元修正ツール (改良版)")
    print("=" * 70)
    print()
    
    # 現在の状態を確認
    check_current_status()
    
    print("\nこのスクリプトは以下を実行します:")
    print("  1. 既存の768次元embeddingデータをクリア")
    print("  2. company_profileテーブルのembedding列を1536次元に変更")
    print("  3. (オプション) 既存求人のembeddingを再生成")
    print()
    
    response = input("実行しますか？ (y/n): ")
    
    if response.lower() == 'y':
        # ステップ1: 次元数を変更
        success = fix_embedding_dimensions()
        
        if success:
            print("\n" + "=" * 70)
            
            response2 = input("\n既存求人のembeddingを再生成しますか？ (y/n): ")
            
            if response2.lower() == 'y':
                # ステップ2: embeddingを再生成
                regenerate_embeddings()
            else:
                print("\n📝 メモ:")
                print("   - 求人を手動で編集・保存するとembeddingが自動生成されます")
                print("   - または後でこのスクリプトを再実行できます")
        
        # 最終状態を確認
        check_current_status()
        
        print("\n✅ 完了！")
        print("   company_app_enhanced.pyを再起動してください")
        
    else:
        print("\n❌ キャンセルしました")