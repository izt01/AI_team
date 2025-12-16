"""
ハイブリッドレコメンデーションシステム
- 協調フィルタリング: 類似ユーザーの行動から推薦
- コンテンツベース: ユーザーの過去の選好から推薦
- scikit-learnを使った機械学習モデル
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import pickle
import json


def get_db_conn():
    """データベース接続を取得"""
    return psycopg2.connect(
        host="localhost", port=5432, dbname="jobmatch",
        user="devuser", password="devpass"
    )


class CollaborativeFiltering:
    """協調フィルタリングクラス"""

    @staticmethod
    def find_similar_users(user_id: int, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        類似ユーザーを見つける（行動履歴ベース）

        Args:
            user_id: ユーザーID
            top_k: 上位K人を返す

        Returns:
            (user_id, similarity_score) のリスト
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 全ユーザーの行動履歴を取得（ユーザー×求人のマトリックス）
            cur.execute("""
                SELECT user_id, job_id, interaction_type,
                       CASE
                           WHEN interaction_type = 'apply' THEN 5.0
                           WHEN interaction_type = 'favorite' THEN 3.0
                           WHEN interaction_type = 'click' THEN 1.0
                           WHEN interaction_type = 'view' THEN 0.5
                           ELSE 0.0
                       END as score
                FROM user_interactions
                WHERE user_id IN (
                    SELECT DISTINCT user_id FROM user_interactions
                )
            """)

            interactions = cur.fetchall()
            cur.close()
            conn.close()

            if not interactions:
                return []

            # ユーザー×求人のマトリックスを構築
            user_item_matrix = {}
            all_jobs = set()

            for inter in interactions:
                uid = inter['user_id']
                jid = str(inter['job_id'])  # UUIDを文字列に変換
                score = float(inter['score'])  # Decimalをfloatに変換

                if uid not in user_item_matrix:
                    user_item_matrix[uid] = {}

                user_item_matrix[uid][jid] = user_item_matrix[uid].get(jid, 0.0) + score
                all_jobs.add(jid)

            if user_id not in user_item_matrix:
                return []

            # ターゲットユーザーのベクトル
            target_vector = [user_item_matrix[user_id].get(job, 0.0) for job in sorted(all_jobs)]

            # 類似度を計算
            similarities = []
            for uid, items in user_item_matrix.items():
                if uid == user_id:
                    continue

                user_vector = [items.get(job, 0.0) for job in sorted(all_jobs)]

                # コサイン類似度
                similarity = cosine_similarity([target_vector], [user_vector])[0][0]

                if similarity > 0.0:
                    similarities.append((uid, float(similarity)))

            # 類似度の高い順にソート
            similarities.sort(key=lambda x: x[1], reverse=True)

            return similarities[:top_k]

        except Exception as e:
            print(f"Error finding similar users: {e}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def get_recommendations_from_similar_users(user_id: int, top_k: int = 20) -> List[Tuple[str, float]]:
        """
        類似ユーザーの行動から求人を推薦

        Args:
            user_id: ユーザーID
            top_k: 上位K件を返す

        Returns:
            (job_id, score) のリスト
        """
        try:
            # 類似ユーザーを見つける
            similar_users = CollaborativeFiltering.find_similar_users(user_id, top_k=10)

            if not similar_users:
                return []

            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # ターゲットユーザーが既にインタラクションした求人を取得
            cur.execute("""
                SELECT DISTINCT job_id FROM user_interactions
                WHERE user_id = %s
            """, (user_id,))

            interacted_jobs = set([str(row['job_id']) for row in cur.fetchall()])

            # 類似ユーザーがインタラクションした求人を取得
            similar_user_ids = [uid for uid, _ in similar_users]
            similarities_dict = {uid: sim for uid, sim in similar_users}

            if not similar_user_ids:
                cur.close()
                conn.close()
                return []

            cur.execute("""
                SELECT user_id, job_id, interaction_type,
                       CASE
                           WHEN interaction_type = 'apply' THEN 5.0
                           WHEN interaction_type = 'favorite' THEN 3.0
                           WHEN interaction_type = 'click' THEN 1.0
                           WHEN interaction_type = 'view' THEN 0.5
                           ELSE 0.0
                       END as score
                FROM user_interactions
                WHERE user_id = ANY(%s)
            """, (similar_user_ids,))

            recommendations = cur.fetchall()
            cur.close()
            conn.close()

            # スコアを集計（類似度で重み付け）
            job_scores = {}
            for rec in recommendations:
                jid = str(rec['job_id'])
                
                # 既にインタラクション済みの求人はスキップ
                if jid in interacted_jobs:
                    continue
                    
                uid = rec['user_id']
                score = float(rec['score'])
                similarity = similarities_dict.get(uid, 0.0)

                weighted_score = score * similarity
                job_scores[jid] = job_scores.get(jid, 0.0) + weighted_score

            # スコアの高い順にソート
            sorted_jobs = sorted(job_scores.items(), key=lambda x: x[1], reverse=True)

            return sorted_jobs[:top_k]

        except Exception as e:
            print(f"Error getting recommendations from similar users: {e}")
            import traceback
            traceback.print_exc()
            return []


class ContentBasedFiltering:
    """コンテンツベースフィルタリングクラス"""

    @staticmethod
    def get_recommendations_from_user_profile(user_id: int, top_k: int = 20, previous_job_ids: List[str] = None) -> List[Tuple[str, float]]:
        """
        ユーザープロファイルから求人を推薦（累積絞り込み対応版）

        Args:
            user_id: ユーザーID
            top_k: 上位K件を返す
            previous_job_ids: 前回の結果のIDリスト

        Returns:
            (job_id, score) のリスト
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # ユーザープロファイルを取得
            cur.execute("""
                SELECT job_title, location_prefecture, salary_min
                FROM user_profile
                WHERE user_id = %s
            """, (user_id,))

            profile = cur.fetchone()

            if not profile:
                print(f"⚠ No profile found for user_id: {user_id}")
                cur.close()
                conn.close()
                return []

            print(f"User profile: {profile}")

            # ユーザーの質問回答を取得
            cur.execute("""
                SELECT dq.question_key, dq.category, uqr.normalized_response
                FROM user_question_responses uqr
                JOIN dynamic_questions dq ON uqr.question_id = dq.id
                WHERE uqr.user_id = %s
            """, (user_id,))

            responses = cur.fetchall()
            print(f"User responses: {len(responses)} answers")

            # 回答を辞書に整理（改善版）
            user_preferences = {}
            
            # ★★★ question_keyの自動正規化（堅牢版） ★★★
            # 既知のキーワードを抽出
            known_keywords = {
                'remote': ['remote', 'リモート', 'テレワーク', 'wfh', 'work_from_home'],
                'flex_time': ['flex', 'フレックス', 'flexible', '柔軟'],
                'side_job': ['side', '副業', 'サイド', '兼業'],
                'company_size': ['size', '規模', '企業規模', 'company_size'],
                'company_type': ['type', 'タイプ', 'ベンチャー', '大企業', 'startup'],
                'overtime': ['overtime', '残業', '労働時間'],
                'atmosphere': ['atmosphere', '雰囲気', '文化', 'culture'],
                'training': ['training', '研修', '教育', 'education'],
                'growth': ['growth', '成長', 'キャリア', 'career'],
                'promotion': ['promotion', '昇進', '昇格']
            }
            
            def normalize_key(original_key: str) -> str:
                """question_keyを自動的に正規化"""
                key_lower = original_key.lower()
                
                # 既知のキーワードにマッチするか確認
                for standard_key, keywords in known_keywords.items():
                    if any(kw in key_lower for kw in keywords):
                        return standard_key
                
                # マッチしない場合は元のキーを返す
                return original_key
            
            for resp in responses:
                original_key = resp['question_key']
                # 自動正規化
                key = normalize_key(original_key)
                value = resp['normalized_response'].strip().lower()
                
                if original_key != key:
                    print(f"  🔄 Normalized '{original_key}' → '{key}'")
                
                # ★★★ テキスト解釈が必要な項目のリスト ★★★
                text_interpretation_keys = ['company_type', 'company_size', 'overtime', 'atmosphere', 'promotion']
                
                if key in text_interpretation_keys:
                    # テキストのまま保存
                    user_preferences[key] = value
                    print(f"  → Stored text '{value}' for {key}")
                    continue
                
                # ★★★ その他の項目は真偽値判定（強化版） ★★★
                positive_keywords = [
                    'はい', 'yes', 'hai', 'する', '希望する', '希望します', '希望です', 
                    'いいです', 'いい', '良い', 'がいい', 'できる', '可能', 'したい',
                    'ある', 'あり', 'ありがいい', '魅力的', '大切', '優先',
                    '少なめ', '少ない', 'リモート', 'フレックス', '大企業', '大手',
                    '活気', 'チャレンジ', '成長', '研修', '昇進', '多い', '興味'
                ]
                
                negative_keywords = [
                    'いいえ', 'no', 'しない', '希望しない', '不要', 'なくても',
                    '大丈夫', '考えない', '重視しない', 'できなくても', '特に', 'ない', 
                    'ないです', '興味ない', '興味はない'
                ]
                
                # ★★★ 曖昧な回答（どちらでもない）を検出 ★★★
                neutral_keywords = [
                    'オプション', 'どちらでも', 'こだわらない', 'あれば', 'なくても',
                    'まあ', 'できれば', '特に気にしない', '気にしない'
                ]
                
                is_neutral = any(kw in value for kw in neutral_keywords)
                is_positive = any(kw in value for kw in positive_keywords)
                is_negative = any(kw in value for kw in negative_keywords)
                
                if is_neutral:
                    # どちらでもない場合はフィルタリングしない（Noneを保存）
                    user_preferences[key] = None
                    print(f"  ⚪ Interpreted '{value}' as NEUTRAL (no filter) for {key}")
                elif is_positive and not is_negative:
                    user_preferences[key] = True
                    print(f"  ✓ Interpreted '{value}' as TRUE for {key}")
                elif is_negative:
                    user_preferences[key] = False
                    print(f"  ✗ Interpreted '{value}' as FALSE for {key}")
                else:
                    # キーワードマッチしない場合はテキストのまま保存
                    user_preferences[key] = value
                    print(f"  → Stored text '{value}' for {key}")

            print(f"\nFinal user preferences: {user_preferences}")

            # ユーザーが既にインタラクションした求人を除外
            cur.execute("""
                SELECT DISTINCT job_id FROM user_interactions
                WHERE user_id = %s AND interaction_type IN ('apply', 'favorite')
            """, (user_id,))

            interacted_jobs = set([str(row['job_id']) for row in cur.fetchall()])
            print(f"Excluding {len(interacted_jobs)} already interacted jobs")

            # 基本条件に合う求人を検索
            titles = [t.strip() for t in profile['job_title'].split(',') if t.strip()] if profile['job_title'] else []
            locations = [l.strip() for l in profile['location_prefecture'].split(',') if l.strip()] if profile['location_prefecture'] else []
            salary_min = int(profile['salary_min']) if profile['salary_min'] else 0

            print(f"Search criteria - titles: {titles}, locations: {locations}, salary_min: {salary_min}")

            conditions = []
            params = []

            # 職種（部分一致）
            if titles:
                title_conditions = []
                for title in titles:
                    title_conditions.append("cp.job_title ILIKE %s")
                    params.append(f"%{title}%")
                conditions.append(f"({' OR '.join(title_conditions)})")

            # 勤務地（部分一致）
            if locations:
                location_conditions = []
                for loc in locations:
                    location_conditions.append("cp.location_prefecture ILIKE %s")
                    params.append(f"%{loc}%")
                conditions.append(f"({' OR '.join(location_conditions)})")

            # 年収
            if salary_min > 0:
                conditions.append("cp.salary_min >= %s")
                params.append(salary_min)

            # 既にインタラクションした求人を除外
            if interacted_jobs:
                conditions.append("cp.id::text NOT IN %s")
                params.append(tuple(interacted_jobs))

            # ★★★ 前回の結果がある場合、それを条件に追加 ★★★
            if previous_job_ids:
                conditions.append("cp.id::text = ANY(%s)")
                params.append(previous_job_ids)
                print(f"🔍 Filtering from previous {len(previous_job_ids)} jobs")

            print("\n=== Applying Multi-Axis Filters ===")

            # ★★★ 多軸フィルタリング（NULL/unknown除外版） ★★★

            # リモートワーク（True/False両方対応）
            if user_preferences.get('remote') == True:
                conditions.append("ja.work_flexibility->>'remote' = 'true'")
                print("🔍 Filtering: remote = true")
            elif user_preferences.get('remote') == False:
                conditions.append("ja.work_flexibility->>'remote' = 'false'")
                print("🔍 Filtering: remote = false")

            # フレックスタイム（True/False両方対応）
            if user_preferences.get('flex_time') == True:
                conditions.append("ja.work_flexibility->>'flex_time' = 'true'")
                print("🔍 Filtering: flex_time = true")
            elif user_preferences.get('flex_time') == False:
                conditions.append("ja.work_flexibility->>'flex_time' = 'false'")
                print("🔍 Filtering: flex_time = false")

            # 副業（True/False両方対応）
            if user_preferences.get('side_job') == True:
                conditions.append("ja.work_flexibility->>'side_job' = 'true'")
                print("🔍 Filtering: side_job = true")
            elif user_preferences.get('side_job') == False:
                conditions.append("ja.work_flexibility->>'side_job' = 'false'")
                print("🔍 Filtering: side_job = false")

            # ★★★ 企業規模のフィルタリング（追加） ★★★
            if 'company_type' in user_preferences:
                user_size = user_preferences['company_type']

                if isinstance(user_size, str):
                    if any(kw in user_size for kw in ['大きい', '大企業', '大手', '安定', '大規模', '環境']):
                        conditions.append("ja.company_culture->>'size' = 'large'")
                        print("🔍 Filtering: company size = large")
                    elif any(kw in user_size for kw in ['小', 'スタートアップ', 'ベンチャー', '小規模', '中小', '中堅']):
                        conditions.append("ja.company_culture->>'size' IN ('small', 'medium')")
                        conditions.append("ja.company_culture->>'size' != 'unknown'")
                        print("🔍 Filtering: company size = small/medium (excluding unknown)")

            # ★★★ 残業時間のフィルタリング（追加） ★★★
            if 'overtime' in user_preferences:
                user_overtime = user_preferences['overtime']

                if isinstance(user_overtime, str):
                    if any(kw in user_overtime for kw in ['少な', '少ない', '10時間', '短', '無し']):
                        conditions.append("ja.work_flexibility->>'overtime' = 'low'")
                        print("🔍 Filtering: overtime = low")

            # 研修（True/False両方対応）
            if user_preferences.get('training') == True:
                conditions.append("ja.career_path->>'training' = 'true'")
                print("🔍 Filtering: training = true")
            elif user_preferences.get('training') == False:
                conditions.append("ja.career_path->>'training' = 'false'")
                print("🔍 Filtering: training = false")

            # キャリア成長（True/False両方対応）
            if user_preferences.get('growth') == True:
                conditions.append("ja.career_path->>'growth_opportunities' = 'true'")
                print("🔍 Filtering: growth = true")
            elif user_preferences.get('growth') == False:
                conditions.append("ja.career_path->>'growth_opportunities' = 'false'")
                print("🔍 Filtering: growth = false")

            # 雰囲気のフィルタリング
            if 'atmosphere' in user_preferences:
                user_atmos = user_preferences['atmosphere']

                if isinstance(user_atmos, str):
                    if any(kw in user_atmos for kw in ['活気', 'チャレンジ', '挑戦']):
                        conditions.append("ja.company_culture->>'atmosphere' = 'challenging'")
                        conditions.append("ja.company_culture->>'atmosphere' != 'unknown'")
                        print("🔍 Filtering: atmosphere = challenging (excluding unknown)")

            # 昇進スピードのフィルタリング
            if 'promotion' in user_preferences:
                user_promo = user_preferences['promotion']

                if isinstance(user_promo, str):
                    if any(kw in user_promo for kw in ['早い', '速い', '多い', '優先']):
                        conditions.append("ja.career_path->>'promotion_speed' = 'fast'")
                        conditions.append("ja.career_path->>'promotion_speed' != 'unknown'")
                        print("🔍 Filtering: promotion_speed = fast (excluding unknown)")
            
            # ★★★ 全てのフィルタリング条件を追加した後にwhere_clauseを定義 ★★★
            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 求人と属性を取得（INNER JOIN + NULL除外）
            query = f"""
                SELECT cp.id, cp.job_title, cp.location_prefecture,
                       cp.salary_min, cp.salary_max,
                       cd.company_name,
                       ja.company_culture, ja.work_flexibility, ja.career_path
                FROM company_profile cp
                JOIN company_date cd ON cp.company_id = cd.company_id
                INNER JOIN job_attributes ja ON cp.id::text = ja.job_id::text
                WHERE {where_clause}
                  AND ja.work_flexibility IS NOT NULL
                  AND ja.company_culture IS NOT NULL
                  AND ja.career_path IS NOT NULL
            """
            print(f"\nSQL Params: {params}")

            cur.execute(query, params)
            jobs = cur.fetchall()

            print(f"\n✓ Found {len(jobs)} jobs matching ALL filter criteria\n")

            cur.close()
            conn.close()

            if not jobs:
                print("⚠ No jobs found after filtering")
                return []

            # スコアを計算（多軸評価）
            recommendations = []
            for job in jobs:
                score = 1.0  # ベーススコア

                # 基本条件のマッチ
                for title in titles:
                    if title.lower() in job['job_title'].lower():
                        score += 3.0

                for loc in locations:
                    if loc.lower() in job['location_prefecture'].lower():
                        score += 2.0

                if int(job['salary_min']) >= salary_min:
                    score += 2.0

                # 多軸評価でのマッチング
                if job.get('work_flexibility'):
                    work_flex = job['work_flexibility']
                    
                    # リモートワーク
                    if user_preferences.get('remote') == True and work_flex.get('remote') == True:
                        score += 5.0
                    elif user_preferences.get('remote') == False and work_flex.get('remote') == False:
                        score += 2.0
                    
                    # フレックスタイム
                    if user_preferences.get('flex_time') == True and work_flex.get('flex_time') == True:
                        score += 4.0
                    
                    # 副業
                    if user_preferences.get('side_job') == True and work_flex.get('side_job') == True:
                        score += 4.0
                    
                    # 残業
                    if 'overtime' in user_preferences:
                        user_overtime = user_preferences['overtime']
                        job_overtime = work_flex.get('overtime', '')
                        
                        if isinstance(user_overtime, str) and '少な' in user_overtime and job_overtime == 'low':
                            score += 5.0
                        elif isinstance(user_overtime, str) and '普通' in user_overtime and job_overtime == 'medium':
                            score += 3.0

                # 企業文化
                if job.get('company_culture'):
                    culture = job['company_culture']
                    
                    # 企業規模
                    if 'company_type' in user_preferences:
                        user_size = user_preferences['company_type']
                        job_size = culture.get('size', '')
                        
                        if isinstance(user_size, str):
                            if any(kw in user_size for kw in ['大きい', '大企業', '大手', '安定', '大規模', '環境']) and job_size == 'large':
                                score += 6.0
                            elif any(kw in user_size for kw in ['小', 'スタートアップ', 'ベンチャー']) and job_size in ['small', 'medium']:
                                score += 5.0
                    
                    # 雰囲気
                    if 'atmosphere' in user_preferences:
                        user_atmos = user_preferences['atmosphere']
                        job_atmos = culture.get('atmosphere', '')
                        
                        if isinstance(user_atmos, str) and any(kw in user_atmos for kw in ['活気', 'チャレンジ']):
                            if job_atmos == 'challenging':
                                score += 5.0

                # キャリアパス
                if job.get('career_path'):
                    career = job['career_path']
                    
                    # 成長機会
                    if user_preferences.get('growth') == True and career.get('growth_opportunities') == True:
                        score += 5.0
                    
                    # 研修
                    if user_preferences.get('training') == True and career.get('training') == True:
                        score += 5.0
                    
                    # 昇進スピード
                    if 'promotion' in user_preferences:
                        user_promo = user_preferences['promotion']
                        job_promo = career.get('promotion_speed', '')
                        
                        if isinstance(user_promo, str) and '早い' in user_promo and job_promo == 'fast':
                            score += 6.0
                        elif isinstance(user_promo, str) and 'ゆっくり' in user_promo and job_promo == 'slow':
                            score += 4.0

                recommendations.append((str(job['id']), score))

            # スコアの高い順にソート
            recommendations.sort(key=lambda x: x[1], reverse=True)

            print(f"Returning {len(recommendations) if top_k is None else len(recommendations[:top_k])} recommendations")
            return recommendations if top_k is None else recommendations[:top_k]

        except Exception as e:
            print(f"Error getting recommendations from user profile: {e}")
            import traceback
            traceback.print_exc()
            return []


class HybridRecommender:
    """ハイブリッドレコメンダークラス（協調 + コンテンツベース + 多軸評価）"""

    @staticmethod
    def get_hybrid_recommendations(user_id: int, top_k: int = 20, previous_job_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        ハイブリッドレコメンデーション（累積絞り込み対応）

        Args:
            user_id: ユーザーID
            top_k: 上位K件を返す（Noneの場合は全件返す）
            previous_job_ids: 前回の結果のIDリスト（Noneの場合は全体から検索）

        Returns:
            推薦求人のリスト
        """
        try:
            print(f"\n=== Hybrid Recommendation for user_id: {user_id} ===")
        
            if previous_job_ids:
                print(f"Filtering from previous {len(previous_job_ids)} jobs")
        
            # 協調フィルタリングの推薦
            cf_recs = CollaborativeFiltering.get_recommendations_from_similar_users(user_id, top_k=top_k)
            print(f"CF recommendations: {len(cf_recs)} jobs")

            # コンテンツベースの推薦
            cb_recs = ContentBasedFiltering.get_recommendations_from_user_profile(
                user_id, 
                top_k=top_k,
                previous_job_ids=previous_job_ids
            )
            print(f"CB recommendations: {len(cb_recs)} jobs")

            # スコアをマージ（重み付け）
            cf_weight = 0.4
            cb_weight = 0.6

            combined_scores = {}

            for job_id, score in cf_recs:
                combined_scores[job_id] = combined_scores.get(job_id, 0.0) + score * cf_weight

            for job_id, score in cb_recs:
                combined_scores[job_id] = combined_scores.get(job_id, 0.0) + score * cb_weight

            print(f"Combined scores: {len(combined_scores)} unique jobs")

            # スコアの高い順にソート
            sorted_jobs = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

            # 求人情報を取得
            if not sorted_jobs:
                print("⚠ No jobs after combining scores")
                return []

            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            job_ids = [jid for jid, _ in (sorted_jobs if top_k is None else sorted_jobs[:top_k])]
            print(f"Fetching details for {len(job_ids)} jobs")

            cur.execute("""
                SELECT cp.id, cp.job_title, cp.location_prefecture,
                       cp.salary_min, cp.salary_max,
                       cd.company_name
                FROM company_profile cp
                JOIN company_date cd ON cp.company_id = cd.company_id
                WHERE cp.id::text = ANY(%s)
            """, (job_ids,))

            jobs = cur.fetchall()
            print(f"Found {len(jobs)} job details")
        
            cur.close()
            conn.close()

            # スコアを付与
            jobs_dict = {str(job['id']): dict(job) for job in jobs}
            results = []

            for job_id, score in (sorted_jobs if top_k is None else sorted_jobs[:top_k]):
                if job_id in jobs_dict:
                    job = jobs_dict[job_id]
                    job['recommendation_score'] = score
                    results.append(job)

            print(f"Final results: {len(results)} jobs\n")
            return results

        except Exception as e:
            print(f"Error getting hybrid recommendations: {e}")
            import traceback
            traceback.print_exc()
            return []


class MLModelScorer:
    """機械学習モデルによるスコアリングクラス"""

    def __init__(self, model_version: str = "v1.0"):
        self.model_version = model_version
        self.model = None
        self.scaler = None

    def extract_features(self, user_id: int, job_id: str) -> Optional[np.ndarray]:
        """
        ユーザーと求人から特徴量を抽出

        Args:
            user_id: ユーザーID
            job_id: 求人ID (UUID文字列)

        Returns:
            特徴量ベクトル
        """
        try:
            conn = get_db_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # ユーザープロファイル
            cur.execute("""
                SELECT job_title, location_prefecture, salary_min
                FROM user_profile
                WHERE user_id = %s
            """, (user_id,))
            user_profile = cur.fetchone()

            # 求人情報
            cur.execute("""
                SELECT cp.job_title, cp.location_prefecture, cp.salary_min, cp.salary_max,
                       cp.click_count, cp.favorite_count, cp.apply_count
                FROM company_profile cp
                WHERE cp.id::text = %s
            """, (job_id,))
            job = cur.fetchone()

            # ユーザーの行動サマリー
            cur.execute("""
                SELECT * FROM user_interaction_summary
                WHERE user_id = %s
            """, (user_id,))
            user_summary = cur.fetchone()

            cur.close()
            conn.close()

            if not user_profile or not job:
                return None

            # 特徴量を構築
            features = []

            # 1. 年収のマッチ度
            salary_match = 1.0 if int(job['salary_min']) >= int(user_profile['salary_min']) else 0.0
            features.append(salary_match)

            # 2. 年収の差（正規化）
            salary_diff = (int(job['salary_min']) - int(user_profile['salary_min'])) / 1000.0
            features.append(salary_diff)

            # 3. 職種のマッチ（簡易的に文字列一致）
            title_match = 1.0 if user_profile['job_title'].lower() in job['job_title'].lower() else 0.0
            features.append(title_match)

            # 4. 勤務地のマッチ
            location_match = 1.0 if user_profile['location_prefecture'].lower() in job['location_prefecture'].lower() else 0.0
            features.append(location_match)

            # 5. 求人の人気度（クリック数、お気に入り数、応募数）
            features.append(int(job.get('click_count', 0)))
            features.append(int(job.get('favorite_count', 0)))
            features.append(int(job.get('apply_count', 0)))

            # 6. ユーザーのアクティビティ
            if user_summary:
                features.append(int(user_summary.get('total_clicks', 0)))
                features.append(int(user_summary.get('total_favorites', 0)))
                features.append(int(user_summary.get('total_applies', 0)))
            else:
                features.extend([0, 0, 0])

            return np.array(features).reshape(1, -1)

        except Exception as e:
            print(f"Error extracting features: {e}")
            return None

    def train_model(self, training_data: List[Tuple[int, str, int]]) -> bool:
        """
        Args:
            training_data: (user_id, job_id, label) のリスト
                        label: 1=応募/お気に入り, 0=クリックのみ/閲覧のみ

        Returns:
                成功したかどうか
        """
        try:
            X = []
            y = []

            for user_id, job_id, label in training_data:
                features = self.extract_features(user_id, job_id)
                if features is not None:
                    X.append(features.flatten())
                    y.append(label)

            if not X:
                return False

            X = np.array(X)
            y = np.array(y)

            # 特徴量のスケーリング
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)

            # ロジスティック回帰モデル
            self.model = LogisticRegression(max_iter=1000, random_state=42)
            self.model.fit(X_scaled, y)

            return True

        except Exception as e:
            print(f"Error training model: {e}")
            return False

    def predict_score(self, user_id: int, job_id: str) -> float:
        """
        モデルを使ってスコアを予測

        Args:
            user_id: ユーザーID
            job_id: 求人ID (UUID文字列)

        Returns:
            予測スコア（0.0〜1.0）
        """
        if self.model is None or self.scaler is None:
            return 0.5  # デフォルト

        try:
            features = self.extract_features(user_id, job_id)
            if features is None:
                return 0.5

            features_scaled = self.scaler.transform(features)
            score = self.model.predict_proba(features_scaled)[0][1]  # クラス1の確率

            return float(score)

        except Exception as e:
            print(f"Error predicting score: {e}")
            return 0.5

    def save_model(self, filepath: str) -> bool:
        """モデルを保存"""
        try:
            with open(filepath, 'wb') as f:
                pickle.dump({'model': self.model, 'scaler': self.scaler, 'version': self.model_version}, f)
            return True
        except Exception as e:
            print(f"Error saving model: {e}")
            return False

    def load_model(self, filepath: str) -> bool:
        """モデルを読み込み"""
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.scaler = data['scaler']
                self.model_version = data.get('version', 'unknown')
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False