# insert_dummy_attributes.py
import psycopg2
import json
import random

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="jobmatch",
    user="devuser", password="devpass"
)
cur = conn.cursor()

# 全ての求人IDを取得
cur.execute("SELECT id FROM company_profile")
job_ids = [row[0] for row in cur.fetchall()]

print(f"Updating attributes for {len(job_ids)} jobs...")

for i, job_id in enumerate(job_ids, 1):
    # ランダムに属性を生成（リアルな分布）
    work_flexibility = {
        "remote": random.choice([True, True, False, False, False]),  # 40%がリモート可
        "flex_time": random.choice([True, True, False, False]),  # 50%がフレックス可
        "side_job": random.choice([True, False, False, False]),  # 25%が副業可
        "overtime": random.choice(["low", "medium", "medium", "high"])  # 低:中:高 = 1:2:1
    }
    
    company_culture = {
        "type": random.choice(["startup", "venture", "mid-size", "large-enterprise"]),
        "atmosphere": random.choice(["flat", "hierarchical", "challenging", "stable"]),
        "size": random.choice(["small", "medium", "medium", "large", "large"])  # 大企業が多め
    }
    
    career_path = {
        "growth_opportunities": random.choice([True, True, False]),  # 67%が成長機会あり
        "training": random.choice([True, True, False]),  # 67%が研修あり
        "promotion_speed": random.choice(["fast", "normal", "normal", "slow"]),
        "skill_support": random.choice([True, True, False])  # 67%がスキル支援あり
    }
    
    try:
        cur.execute("""
            UPDATE job_attributes
            SET work_flexibility = %s,
                company_culture = %s,
                career_path = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = %s
        """, (
            json.dumps(work_flexibility),
            json.dumps(company_culture),
            json.dumps(career_path),
            str(job_id)
        ))
        
        if (i % 100) == 0:
            print(f"  [{i}/{len(job_ids)}] Updated")
            
    except Exception as e:
        print(f"  [{i}/{len(job_ids)}] Failed: {e}")

conn.commit()
cur.close()
conn.close()

print("\n✓ All attributes updated!")

# 確認
cur = conn.cursor()
cur.execute("""
    SELECT 
        SUM(CASE WHEN work_flexibility->>'remote' = 'true' THEN 1 ELSE 0 END) as remote_count,
        SUM(CASE WHEN work_flexibility->>'flex_time' = 'true' THEN 1 ELSE 0 END) as flex_count,
        SUM(CASE WHEN company_culture->>'size' = 'large' THEN 1 ELSE 0 END) as large_count,
        COUNT(*) as total
    FROM job_attributes
""")
stats = cur.fetchone()
print(f"\n統計:")
print(f"  リモート可: {stats[0]}/{stats[3]} ({stats[0]*100//stats[3]}%)")
print(f"  フレックス可: {stats[1]}/{stats[3]} ({stats[1]*100//stats[3]}%)")
print(f"  大企業: {stats[2]}/{stats[3]} ({stats[2]*100//stats[3]}%)")
cur.close()
conn.close()