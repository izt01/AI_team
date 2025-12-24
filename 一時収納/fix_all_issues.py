"""
全自動修正スクリプト - すべての問題を一度に解決
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def fix_all():
    print("=" * 80)
    print("🔧 全自動修正スクリプト")
    print("=" * 80)
    
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname=os.getenv("DB_NAME", "jobmatch"),
            user=os.getenv("DB_USER", "devuser"),
            password=os.getenv("DB_PASSWORD", "devpass")
        )
        cur = conn.cursor()
        
        print("\n✅ データベース接続成功")
        
        # 1. user_question_responses に question_key を追加
        print("\n[1] user_question_responses テーブルを修正中...")
        
        # question_key カラムの確認
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_question_responses' 
            AND column_name = 'question_key'
        """)
        
        if not cur.fetchone():
            print("   → question_key カラムを追加中...")
            cur.execute("""
                ALTER TABLE user_question_responses 
                ADD COLUMN question_key VARCHAR(100)
            """)
            conn.commit()
            print("   ✅ question_key カラムを追加しました")
        else:
            print("   ✅ question_key カラムは既に存在します")
        
        # 既存データに question_key を生成
        print("   → 既存データの question_key を生成中...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_question_responses' 
            AND column_name = 'question_id'
        """)
        
        if cur.fetchone():
            cur.execute("""
                UPDATE user_question_responses
                SET question_key = 'question_' || question_id::text
                WHERE question_key IS NULL OR question_key = ''
            """)
            updated = cur.rowcount
            conn.commit()
            print(f"   ✅ {updated} レコードを更新しました")
        
        # 2. dynamic_questions に question_key を追加（必要に応じて）
        print("\n[2] dynamic_questions テーブルを確認中...")
        
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'dynamic_questions' 
            AND column_name = 'question_key'
        """)
        
        if not cur.fetchone():
            print("   → question_key カラムを追加中...")
            cur.execute("""
                ALTER TABLE dynamic_questions 
                ADD COLUMN question_key VARCHAR(100) UNIQUE
            """)
            conn.commit()
            print("   ✅ question_key カラムを追加しました")
            
            # 既存データに question_key を生成
            cur.execute("""
                UPDATE dynamic_questions
                SET question_key = 'question_' || id
                WHERE question_key IS NULL OR question_key = ''
            """)
            updated = cur.rowcount
            conn.commit()
            print(f"   ✅ {updated} レコードを更新しました")
        else:
            print("   ✅ question_key カラムは既に存在します")
        
        # 3. インデックスを追加
        print("\n[3] インデックスを追加中...")
        
        try:
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_question_responses_question_key 
                ON user_question_responses(question_key)
            """)
            conn.commit()
            print("   ✅ user_question_responses のインデックスを追加")
        except Exception as e:
            print(f"   ⚠️  インデックスの追加をスキップ: {e}")
        
        # 4. 最終確認
        print("\n[4] 最終確認...")
        
        # user_question_responses
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'user_question_responses' 
            AND column_name = 'question_key'
        """)
        uqr_ok = cur.fetchone()[0] > 0
        
        # dynamic_questions
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'dynamic_questions' 
            AND column_name = 'question_key'
        """)
        dq_ok = cur.fetchone()[0] > 0
        
        print(f"   user_question_responses.question_key: {'✅' if uqr_ok else '❌'}")
        print(f"   dynamic_questions.question_key: {'✅' if dq_ok else '❌'}")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 80)
        if uqr_ok and dq_ok:
            print("✅ すべての修正が完了しました！")
            print("=" * 80)
            print("\n次のステップ:")
            print("  1. 最新版の dynamic_question_generator_v2.py に置き換え")
            print("  2. 最新版の app.py に置き換え")
            print("  3. アプリを再起動: python app.py")
            print("  4. ブラウザをリロード: http://localhost:5000/chat")
        else:
            print("⚠️  一部の修正が失敗しました")
            print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_all()