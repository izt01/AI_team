"""
データベースマイグレーションスクリプト
既存のデータベースを新しいスキーマに移行
"""

import psycopg2
import sys
import os


def get_db_conn():
    """データベース接続を取得"""
    return psycopg2.connect(
        host="localhost", port=5432, dbname="jobmatch",
        user="devuser", password="devpass"
    )


def execute_sql_file(filepath: str):
    """SQLファイルを実行"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        conn = get_db_conn()
        cur = conn.cursor()

        # 複数のSQL文を実行
        cur.execute(sql_content)

        conn.commit()
        cur.close()
        conn.close()

        print(f"✓ Successfully executed: {filepath}")
        return True

    except Exception as e:
        print(f"✗ Error executing {filepath}: {e}")
        return False


def check_pgvector_extension():
    """pgvector拡張が利用可能かチェック"""
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM pg_available_extensions WHERE name = 'vector';")
        result = cur.fetchone()

        cur.close()
        conn.close()

        if result:
            print("✓ pgvector extension is available")
            return True
        else:
            print("⚠ pgvector extension is NOT available")
            print("  Please install pgvector first:")
            print("  https://github.com/pgvector/pgvector")
            return False

    except Exception as e:
        print(f"✗ Error checking pgvector: {e}")
        return False


def backup_database():
    """データベースをバックアップ（推奨）"""
    print("\n=== Database Backup ===")
    print("Before migration, it's recommended to backup your database:")
    print("  pg_dump -U devuser -h localhost jobmatch > jobmatch_backup.sql")
    print()

    response = input("Have you backed up your database? (y/n): ")

    if response.lower() != 'y':
        print("Please backup your database first, then run this script again.")
        sys.exit(0)


def migrate():
    """マイグレーションを実行"""
    print("\n=== AI Job Matching System - Database Migration ===\n")

    # Step 1: バックアップの確認
    backup_database()

    # Step 2: pgvectorのチェック
    print("\n=== Checking pgvector extension ===")
    has_pgvector = check_pgvector_extension()

    if not has_pgvector:
        print("\nContinuing without pgvector...")
        response = input("Do you want to continue without vector search? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    # Step 3: スキーマ拡張を実行
    print("\n=== Executing schema extension ===")
    schema_file = "schema_extension.sql"

    if not os.path.exists(schema_file):
        print(f"✗ Schema file not found: {schema_file}")
        sys.exit(1)

    success = execute_sql_file(schema_file)

    if not success:
        print("\n✗ Migration failed!")
        sys.exit(1)

    # Step 4: 既存データの移行
    print("\n=== Migrating existing data ===")

    try:
        conn = get_db_conn()
        cur = conn.cursor()

        # 既存のembedding（TEXT）をvector型に変換
        print("  Converting existing embeddings to vector type...")

        cur.execute("""
            SELECT id, embedding
            FROM company_profile
            WHERE embedding IS NOT NULL AND embedding != ''
        """)

        jobs_with_embedding = cur.fetchall()

        converted_count = 0
        for job_id, embedding_text in jobs_with_embedding:
            try:
                # TEXT形式のembeddingをパース（JSON配列として）
                import json
                embedding_array = json.loads(embedding_text)

                # vector型に変換して保存
                cur.execute("""
                    UPDATE company_profile
                    SET embedding_vector = %s::vector
                    WHERE id = %s
                """, (str(embedding_array), job_id))

                converted_count += 1

            except Exception as e:
                print(f"    ⚠ Failed to convert embedding for job_id {job_id}: {e}")

        conn.commit()

        print(f"  ✓ Converted {converted_count} embeddings")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"  ✗ Error migrating data: {e}")

    # Step 5: 初期データの投入
    print("\n=== Setting up initial data ===")

    try:
        conn = get_db_conn()
        cur = conn.cursor()

        # 初期質問が既に存在するかチェック
        cur.execute("SELECT COUNT(*) FROM dynamic_questions")
        question_count = cur.fetchone()[0]

        if question_count == 0:
            print("  Initial questions already set up")
        else:
            print(f"  ✓ {question_count} questions found")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"  ⚠ Error checking initial data: {e}")

    # 完了
    print("\n=== Migration completed successfully! ===")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Extract job attributes: POST /admin/extract_job_attributes")
    print("3. Generate dynamic questions: POST /admin/generate_questions")
    print("4. Run the new application: python app_v2.py")
    print()


if __name__ == "__main__":
    migrate()
