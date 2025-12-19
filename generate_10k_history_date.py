"""
検索履歴とチャット履歴の大量ダミーデータ生成スクリプト

- search_history: 10,000件
- chat_history: 10,000件
"""

import random
from datetime import datetime, timedelta
from db_config import get_db_conn
from psycopg2.extras import execute_batch

# ダミーデータの定義
SEARCH_KEYWORDS = [
    # プログラミング言語
    "Python", "JavaScript", "Java", "C++", "Ruby", "Go", "TypeScript", "PHP", "Swift", "Kotlin",
    # 職種
    "エンジニア", "デザイナー", "プロジェクトマネージャー", "データサイエンティスト", "DevOpsエンジニア",
    "フロントエンドエンジニア", "バックエンドエンジニア", "フルスタックエンジニア", "機械学習エンジニア",
    # 技術・フレームワーク
    "React", "Vue", "Angular", "Django", "Flask", "Spring", "Node.js", "Docker", "Kubernetes",
    "AWS", "GCP", "Azure", "機械学習", "AI", "深層学習", "自然言語処理", "画像認識",
    # 勤務形態
    "リモートワーク", "フルリモート", "在宅勤務", "ハイブリッド", "フレックスタイム", "時短勤務",
    # 地域
    "東京", "大阪", "名古屋", "福岡", "札幌", "仙台", "横浜", "神戸", "京都", "広島",
    # 企業タイプ
    "スタートアップ", "ベンチャー", "大手企業", "外資系", "上場企業", "メガベンチャー",
    # その他
    "新卒", "中途", "未経験歓迎", "第二新卒", "副業OK", "英語力不要", "高年収", "成長企業"
]

USER_MESSAGES = [
    "Pythonを使った仕事を探しています",
    "リモートワークができる求人はありますか？",
    "未経験でもエンジニアになれますか？",
    "年収600万円以上の求人を教えてください",
    "東京で働ける職場を探しています",
    "フルスタックエンジニアの求人はありますか？",
    "スタートアップで働きたいです",
    "英語を使う仕事に興味があります",
    "データサイエンティストになりたいです",
    "副業OKの求人を探しています",
    "フレックスタイム制の会社を希望します",
    "在宅勤務可能な求人はありますか？",
    "大手企業で安定した環境で働きたいです",
    "成長できる環境を探しています",
    "チーム開発の経験を積みたいです",
    "機械学習のプロジェクトに携わりたいです",
    "UI/UXデザインの仕事を探しています",
    "バックエンド開発に興味があります",
    "AWSの経験を活かせる職場を探しています",
    "Dockerを使った開発がしたいです",
    "ReactやVueを使ったフロントエンド開発がしたい",
    "週3日勤務の求人はありますか？",
    "外資系企業に興味があります",
    "転職したいけど何から始めればいいですか？",
    "面接対策を教えてください",
    "履歴書の書き方を教えてください",
    "キャリアチェンジを考えています",
    "今の年収が適正か知りたいです",
    "スキルアップできる環境を探しています",
    "ワークライフバランスを重視したいです"
]

AI_RESPONSES = [
    "Pythonを使用した開発職をお探しですね。データサイエンスや機械学習、Web開発など、様々な分野でPythonの求人があります。",
    "はい、多くの企業がリモートワークに対応しています。完全リモートやハイブリッド型の求人をご紹介できます。",
    "未経験からエンジニアを目指すことは可能です。研修制度が充実した企業や、未経験歓迎の求人をご紹介します。",
    "年収600万円以上の求人は多数あります。ご経験やスキルに応じて、最適な求人をご提案させていただきます。",
    "東京都内には多くの求人があります。具体的にどのエリアをご希望でしょうか？",
    "フルスタックエンジニアの求人は需要が高いです。フロントエンドとバックエンド両方の経験がある方は特に歓迎されます。",
    "スタートアップ企業での勤務は成長機会が多いです。いくつか魅力的な企業をご紹介できます。",
    "英語を使う業務がある求人もございます。どの程度の英語力をお持ちでしょうか？",
    "データサイエンティストは注目の職種です。統計学や機械学習の知識があると有利です。",
    "副業を許可している企業も増えています。副業OKの求人をお探ししますね。",
    "フレックスタイム制を導入している企業は多いです。ワークライフバランスを重視されているのですね。",
    "在宅勤務可能な求人は増加傾向にあります。完全在宅か、週何日程度を希望されますか？",
    "大手企業は福利厚生や研修制度が充実しています。安定志向の方にはおすすめです。",
    "成長できる環境をお探しですね。新しい技術に挑戦できる企業をご紹介します。",
    "チーム開発の経験は非常に重要です。アジャイル開発を採用している企業が多いです。",
    "機械学習プロジェクトに携わりたいのですね。AIスタートアップや研究開発部門のある企業をご紹介します。",
    "UI/UXデザインの需要は高まっています。ユーザー中心設計の経験はお持ちですか？",
    "バックエンド開発では、API設計やデータベース設計のスキルが重視されます。",
    "AWS経験者は市場価値が高いです。どのサービスをメインに使われていますか？",
    "Dockerを使った開発環境構築ができると、多くの企業で評価されます。",
    "React、Vue共に人気のフレームワークです。モダンな開発環境で働ける企業をご紹介します。",
    "週3日勤務の求人もございます。業務委託や契約社員の形態が多いです。",
    "外資系企業は給与水準が高い傾向にあります。英語力が求められることが多いです。",
    "転職活動では、まずご自身のキャリアの棚卸しから始めましょう。サポートさせていただきます。",
    "面接では、これまでの経験と今後のキャリアビジョンを明確に伝えることが重要です。",
    "履歴書は簡潔に、具体的な実績を数字で示すと効果的です。",
    "キャリアチェンジは勇気がいる決断ですが、新しい分野への挑戦は可能です。",
    "年収の適正は、経験年数やスキル、市場動向によって変わります。診断サービスもご利用いただけます。",
    "スキルアップには、実務経験と継続的な学習が大切です。勉強会やセミナーに参加される企業も多いです。",
    "ワークライフバランスを重視する企業は増えています。残業時間や休暇制度を確認しましょう。"
]

def get_existing_user_ids():
    """既存のユーザーIDを取得"""
    conn = get_db_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT user_id FROM personal_date ORDER BY user_id")
    user_ids = [row[0] for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return user_ids

def check_table_columns():
    """テーブルの列名を確認"""
    conn = get_db_conn()
    cur = conn.cursor()
    
    # search_historyの列を確認
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'search_history'
        ORDER BY ordinal_position
    """)
    search_columns = [row[0] for row in cur.fetchall()]
    
    # chat_historyの列を確認
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'chat_history'
        ORDER BY ordinal_position
    """)
    chat_columns = [row[0] for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return search_columns, chat_columns

def generate_search_history_data(user_ids, count=10000):
    """検索履歴のダミーデータを生成"""
    
    data = []
    start_date = datetime.now() - timedelta(days=365)  # 1年前から
    
    print(f"🔄 {count}件の検索履歴データを生成中...")
    
    for i in range(count):
        user_id = random.choice(user_ids)
        
        # ランダムに1-5個のキーワードを選択
        num_keywords = random.randint(1, 5)
        keywords = random.sample(SEARCH_KEYWORDS, num_keywords)
        search_keywords = ",".join(keywords)
        
        # 求人IDはランダム（1-1000）
        job_id = random.randint(1, 1000) if random.random() > 0.3 else None
        
        # 日時は過去1年間のランダムな日時
        days_ago = random.randint(0, 365)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        searched_at = start_date + timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        
        data.append((user_id, search_keywords, job_id, searched_at))
        
        if (i + 1) % 1000 == 0:
            print(f"   生成済み: {i + 1}/{count}")
    
    return data

def generate_chat_history_data(user_ids, chat_columns, count=10000):
    """チャット履歴のダミーデータを生成"""
    
    data = []
    start_date = datetime.now() - timedelta(days=365)
    
    print(f"🔄 {count}件のチャット履歴データを生成中...")
    
    # 列名を確認
    has_user_message = 'user_message' in chat_columns
    has_message_text = 'message_text' in chat_columns
    has_ai_response = 'ai_response' in chat_columns
    has_bot_response = 'bot_response' in chat_columns
    
    print(f"   検出された列: {chat_columns}")
    
    for i in range(count):
        user_id = random.choice(user_ids)
        
        # ランダムにメッセージを選択
        user_msg = random.choice(USER_MESSAGES)
        ai_msg = random.choice(AI_RESPONSES)
        
        # 日時は過去1年間のランダムな日時
        days_ago = random.randint(0, 365)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        created_at = start_date + timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        
        # 列名に応じてデータを構築
        if has_user_message and has_ai_response:
            data.append((user_id, user_msg, ai_msg, created_at))
        elif has_message_text:
            # message_text列しかない場合
            data.append((user_id, user_msg, 'user', created_at))
        else:
            # その他の構造の場合
            data.append((user_id, user_msg, created_at))
        
        if (i + 1) % 1000 == 0:
            print(f"   生成済み: {i + 1}/{count}")
    
    return data

def insert_search_history(data):
    """検索履歴を一括挿入"""
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    print(f"💾 検索履歴を挿入中...")
    
    try:
        execute_batch(cur, """
            INSERT INTO search_history (user_id, search_keywords, job_id, searched_at)
            VALUES (%s, %s, %s, %s)
        """, data, page_size=1000)
        
        conn.commit()
        
        # 挿入件数を確認
        cur.execute("SELECT COUNT(*) FROM search_history")
        count = cur.fetchone()[0]
        
        print(f"✅ 検索履歴を挿入しました: {count}件")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    
    finally:
        cur.close()
        conn.close()

def insert_chat_history(data, chat_columns):
    """チャット履歴を一括挿入"""
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    print(f"💾 チャット履歴を挿入中...")
    
    try:
        # 列名に応じてSQL文を構築
        if 'user_message' in chat_columns and 'ai_response' in chat_columns:
            sql = """
                INSERT INTO chat_history (user_id, user_message, ai_response, created_at)
                VALUES (%s, %s, %s, %s)
            """
        elif 'message_text' in chat_columns and 'message_type' in chat_columns:
            sql = """
                INSERT INTO chat_history (user_id, message_text, message_type, created_at)
                VALUES (%s, %s, %s, %s)
            """
        else:
            # デフォルト
            sql = """
                INSERT INTO chat_history (user_id, user_message, created_at)
                VALUES (%s, %s, %s)
            """
        
        execute_batch(cur, sql, data, page_size=1000)
        
        conn.commit()
        
        # 挿入件数を確認
        cur.execute("SELECT COUNT(*) FROM chat_history")
        count = cur.fetchone()[0]
        
        print(f"✅ チャット履歴を挿入しました: {count}件")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    
    finally:
        cur.close()
        conn.close()

def main():
    print("=" * 70)
    print("🎲 大量ダミーデータ生成スクリプト")
    print("=" * 70)
    
    # ユーザーIDを取得
    print("\n📋 既存のユーザーIDを取得中...")
    user_ids = get_existing_user_ids()
    
    if not user_ids:
        print("❌ ユーザーが見つかりません。先にユーザーデータを作成してください。")
        return
    
    print(f"✅ {len(user_ids)}人のユーザーが見つかりました")
    
    # テーブルの列を確認
    print("\n🔍 テーブル構造を確認中...")
    search_columns, chat_columns = check_table_columns()
    
    print(f"   search_history: {search_columns}")
    print(f"   chat_history: {chat_columns}")
    
    # 件数を指定
    print("\n" + "=" * 70)
    search_count = int(input("検索履歴を何件生成しますか？ [10000]: ") or "10000")
    chat_count = int(input("チャット履歴を何件生成しますか？ [10000]: ") or "10000")
    
    # 検索履歴を生成・挿入
    print("\n" + "=" * 70)
    print("📊 検索履歴の生成")
    print("=" * 70)
    
    search_data = generate_search_history_data(user_ids, search_count)
    insert_search_history(search_data)
    
    # チャット履歴を生成・挿入
    print("\n" + "=" * 70)
    print("💬 チャット履歴の生成")
    print("=" * 70)
    
    chat_data = generate_chat_history_data(user_ids, chat_columns, chat_count)
    insert_chat_history(chat_data, chat_columns)
    
    # 統計を表示
    print("\n" + "=" * 70)
    print("📊 最終統計")
    print("=" * 70)
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM search_history")
    search_total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM chat_history")
    chat_total = cur.fetchone()[0]
    
    print(f"   検索履歴: {search_total:,}件")
    print(f"   チャット履歴: {chat_total:,}件")
    
    # サンプルデータを表示
    print("\n📋 サンプルデータ（検索履歴）:")
    cur.execute("SELECT * FROM search_history ORDER BY searched_at DESC LIMIT 3")
    for row in cur.fetchall():
        print(f"   {row}")
    
    print("\n💬 サンプルデータ（チャット履歴）:")
    cur.execute("SELECT * FROM chat_history ORDER BY created_at DESC LIMIT 3")
    for row in cur.fetchall():
        print(f"   {row[:4]}...")  # 最初の4列だけ表示
    
    cur.close()
    conn.close()
    
    print("\n✅ 完了しました！")

if __name__ == "__main__":
    main()