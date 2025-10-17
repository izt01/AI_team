import chainlit as cl
import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from categories import CATEGORY_MAP, CATEGORY_LABELS

VALID_JOB_TITLES = list(CATEGORY_MAP.keys())


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

system_prompt = """
あなたは求職支援AIです。
求人情報や職業内容については敬語で丁寧に答えてください。
職種の紹介や提案は、jobs.jsonに登録されている職種のみを対象としてください。
それ以外の職種は紹介しないでください。
職種（職業）の内容について説明を求められた場合は、職種の一覧と仕事内容を紹介してください。
ユーザーの希望条件（勤務地、給与、勤務時間、職場環境など）に応じて、適した職種を選び、理由を添えて説明してください。
"""

# ログ保存パス生成
LOG_DIR = r"C:\Users\hp\OneDrive\Desktop\job-support-ai\logs"

def get_log_path(user_id: str) -> str:
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    return os.path.join(LOG_DIR, f"{user_id}_log.json")

def load_user_log(user_id: str) -> list:
    filepath = get_log_path(user_id)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f).get("history", [])
    except:
        return []

def save_user_log(user_id: str, message: str, scores: dict, coords: tuple = None, preferences: dict = None):
    try:
        filepath = get_log_path(user_id)
        log = {"user_id": user_id, "history": load_user_log(user_id)}
        entry = {"message": message, "scores": scores}
        if coords:
            entry["coords"] = coords
        if preferences:
            entry["preferences"] = preferences
        log["history"].append(entry)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"ログ保存失敗: {e}")

def merge_scores(history: list) -> dict:
    merged = {}
    for entry in history:
        for key, value in entry["scores"].items():
            merged[key] = max(merged.get(key, 0), value)
    return merged

def load_job_database(filepath="jobs.json") -> dict:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}
    
def get_valid_job_titles(job_db: dict) -> list:
    return [job["職種名"] for job in job_db.values()]

def get_job_titles_by_tags(job_db: dict, tags: list) -> list:
    return [
        job["職種名"]
        for job in job_db.values()
        if any(tag in job.get("タグ", []) for tag in tags)
    ]

def suggest_job_type_from_message(message: str, valid_titles: list) -> dict:
    title_list = "\n".join([f"- {title}" for title in valid_titles])
    prompt = f"""
ユーザーの希望: 「{message}」

以下の職種リストの中から、最も希望に近い職種を1つだけ選び、その職種名と簡単な説明を出力してください。
※職種リストに含まれていない職種は絶対に出力しないでください。
※ユーザーは「人と話すのが苦手」と述べており、コミュニケーション頻度が低い職種を希望しています。

職種リスト:
{title_list}

出力形式（以下の形式で必ず出力してください）:
職種名: ○○○
説明: ○○○
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    content = response.choices[0].message.content.strip()
    try:
        lines = content.splitlines()
        title = lines[0].replace("職種名:", "").strip()
        description = lines[1].replace("説明:", "").strip()

        ALIAS_MAP = {
            "プログラマー": "ITエンジニア",
            "データアナリスト": "AIエンジニア",
            "研究者": "研究職",
            "ライブラリアン": None,
            "ラボテクニシャン": "研究職"
        }
        title = ALIAS_MAP.get(title, title)

        if title in valid_titles:
            return {"職種名": title, "説明": description}
    except:
        pass
    return {"職種名": "営業職", "説明": "幅広い業界で活躍できる職種です。"}

def extract_tags_from_message(message: str) -> list:
    tag_map = {
        "静か": ["静か", "集中型"],
        "人と話す": ["コミュニケーション", "営業", "接客"],
        "話すのが好き": ["コミュニケーション"],
        "在宅": ["在宅可", "リモート可"],
        "安定": ["安定", "事務"],
        "子ども": ["子ども", "保育"],
        "技術": ["技術職"],
        "クリエイティブ": ["クリエイティブ"]
    }

    NEGATIVE_HINTS = {
        "人と話すのが苦手": ["静か", "集中型", "個人作業"],
        "コミュニケーションが苦手": ["静か", "技術職"],
        "接客を避けたい": ["静か", "事務", "研究"]
    }

    matched_tags = []

    # 否定的な希望からポジティブなタグを追加
    for phrase, tags in NEGATIVE_HINTS.items():
        if phrase in message:
            matched_tags.extend(tags)

    # 通常のキーワード抽出（否定文は除外）
    for keyword, tags in tag_map.items():
        if keyword in message:
            if re.search(rf"(苦手|避けたい|嫌い).*{keyword}|{keyword}.*(苦手|避けたい|嫌い)", message):
                continue
            matched_tags.extend(tags)

    return list(set(matched_tags))

def format_job_info(job: dict) -> str:
    return f"""【求人情報：{job.get('職種名', '不明')}】
会社名：{job.get('会社名')}
勤務地：{job.get('勤務地')}
給与：{job.get('給与')}
勤務時間：{job.get('勤務時間')}
仕事内容：{job.get('仕事内容')}
福利厚生：{job.get('福利厚生')}
"""

def analyze_interests(message: str) -> dict:
    prompt = f"""
以下の転職相談メッセージに含まれる関心要素（勤務地、給与、業務内容、職場環境、福利厚生、勤務時間）について、それぞれ1〜5のスコアで評価してください。
メッセージ: {message}
出力形式: JSON（例：{{"勤務地": 4, "給与": 2, ...}}）
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return json.loads(response.choices[0].message.content.strip())
    except:
        return {}

def recommend_by_interest(scores: dict) -> str:
    if not scores or not any(scores.values()):
        return "まだ情報が少ないですが、幅広い職種をご紹介します。\n例：事務職、営業職、ITサポート職"
    top_interest = max(scores, key=scores.get)
    if top_interest == "勤務地":
        return "勤務地の柔軟性が高い職種がおすすめです。\n例：リモートワーク可能なIT職、営業職、カスタマーサポート"
    elif top_interest == "給与":
        return "高収入が期待できる職種がおすすめです。\n例：コンサルタント、外資系営業、AIエンジニア"
    elif top_interest == "業務内容":
        return "仕事内容が明確でやりがいのある職種がおすすめです。\n例：プロジェクトマネージャー、企画職、研究開発職"
    elif top_interest == "職場環境":
        return "職場の雰囲気や文化を重視する職種がおすすめです。\n例：スタートアップ企業、フラットな組織のIT企業"
    elif top_interest == "福利厚生":
        return "福利厚生が充実した企業の職種がおすすめです。\n例：大手企業の総合職、公務員、医療系事務"
    elif top_interest == "勤務時間":
        return "柔軟な勤務時間が可能な職種がおすすめです。\n例：フレックス制度のある職種、在宅勤務可能な職種"
    return "適切な職種を特定できませんでした。"

def get_jobs_by_category(job_db: dict, category_id: int) -> list:
    return [job for job in job_db.values() if job.get("カテゴリ") == category_id]

def extract_category_from_message(message: str) -> int | None:
    for name, cid in CATEGORY_MAP.items():
        if name in message:
            return cid
    return None

def extract_location_from_message(message: str) -> str | None:
    patterns = {
        "東京": r"(東京|東京都|都内|23区|千代田区|新宿|渋谷|品川|港区|中野|練馬|大田区|杉並|板橋|新橋)",
        "大阪": r"(大阪|大阪府|梅田|難波)",
        "福岡": r"(福岡|福岡県)",
        "札幌": r"(札幌|北海道)",
        "京都": r"(京都|京都府)",
        "横浜": r"(横浜|神奈川県)",
        "仙台": r"(仙台|宮城県)",
        "広島": r"(広島|広島県)",
        "名古屋": r"(名古屋|愛知県)"
    }
    for city, pattern in patterns.items():
        if re.search(pattern, message):
            return city
    return None

def get_coordinates_from_location(location_name: str) -> tuple | None:
    geolocator = Nominatim(user_agent="job-matcher")
    try:
        geo = geolocator.geocode(location_name)
        if geo:
            return (geo.latitude, geo.longitude)
    except:
        pass
    return None

def find_nearby_jobs(user_coords: tuple, job_db: dict, max_distance_km=50) -> list:
    nearby = []
    for job in job_db.values():
        job_coords = (job.get("緯度"), job.get("経度"))
        if None in job_coords:
            continue
        distance = geodesic(user_coords, job_coords).km
        if distance <= max_distance_km:
            nearby.append((distance, job))
    nearby.sort(key=lambda x: x[0])
    return [job for _, job in nearby]

#勤務地スコア
def match_top_jobs(user_scores: dict, job_db: dict, top_n: int = 3) -> list:
    if not user_scores:
        return []
    match_results = []
    for job_type, job_data in job_db.items():
        job_scores = job_data.get("スコア", {})
        match_score = sum(
            user_scores.get(k, 0) * job_scores.get(k, 0) * (2 if k == "勤務地" else 1)
            for k in job_scores  # ← user_scores ではなく job_scores に合わせると柔軟
        )
        match_results.append((job_type, match_score, job_data))
    match_results.sort(key=lambda x: x[1], reverse=True)
    return [job for _, _, job in match_results[:top_n]]

def generate_followup_question(scores: dict) -> str:
    if not scores or all(v == 3 for v in scores.values()):
        return "ご希望の条件について、もう少し詳しく教えていただけますか？勤務地や勤務時間、職場環境など、気になる点はございますか？"
    top_interest = max(scores, key=scores.get)
    if top_interest == "職場環境":
        return "職場の雰囲気について、どんな環境が理想ですか？（例：静か・活発・少人数など）"
    elif top_interest == "勤務時間":
        return "勤務時間について、希望の時間帯や柔軟性などありますか？"
    elif top_interest == "勤務地":
        return "勤務地について、通勤時間や地域の希望などありますか？"
    elif top_interest == "給与":
        return "給与について、希望の年収や待遇などありますか？"
    elif top_interest == "業務内容":
        return "業務内容について、どんな仕事に興味がありますか？"
    return ""

def suggest_high_salary_jobs(job_db, min_salary=700):
    results = []
    for job in job_db.values():
        if "給与下限" in job:
            try:
                if job["給与下限"] >= min_salary:
                    results.append(job)
            except:
                continue
    return results[:3]

def filter_jobs_by_job_types(job_db: dict, job_types: list[str]) -> dict:
    return {k: v for k, v in job_db.items() if v.get("職種名") in job_types}

def extract_job_type_from_history(history: list) -> str | None:
    for entry in reversed(history):
        msg = entry.get("message", "")
        if "営業職" in msg:
            return "営業職"
        elif "カスタマーサポート" in msg:
            return "カスタマーサポート"
        elif "人事" in msg:
            return "人事職"
        elif "IT" in msg:
            return "ITエンジニア"
        elif "研究" in msg:
            return "研究職"
    return None

#最新のスコアだけ取得
def load_latest_scores(user_id: str) -> dict:
    history = load_user_log(user_id)
    if not history:
        return {}
    return history[-1]["scores"]

def load_latest_preferences(user_id: str) -> dict:
    history = load_user_log(user_id)
    for entry in reversed(history):
        if "preferences" in entry:
            return entry["preferences"]
    return {}

#新しいスコアで上書き
def merge_scores_preserving_old(new_scores: dict, old_scores: dict) -> dict:
    merged = old_scores.copy()
    merged.update(new_scores) 
    return merged

def merge_preferences(new_prefs: dict, old_prefs: dict) -> dict:
    merged = old_prefs.copy()
    for key, val in new_prefs.items():
        merged[key] = val  # 新しいものがあれば上書き
    return merged

#業務スタイルと職種のマッピング
WORK_STYLE_MAP = {
    "静か": ["研究職", "ITエンジニア", "データ入力", "バックオフィス"],
    "一人作業": ["デザイナー", "ライター", "エンジニア", "研究職"],
    "体を動かす": ["配送", "介護", "清掃", "施工管理"],
    "創造的": ["デザイナー", "企画職", "動画編集", "ライター"],
    "ルーチン": ["事務", "データ入力", "経理"],
    "対人少なめ": ["ITエンジニア", "研究職", "事務"],
    "対人多め": ["営業", "接客", "カスタマーサポート"]
}

#希望条件の（具体的な値）抽出
def extract_user_preferences(message: str) -> dict:
    prefs = {}

    # 例：勤務地
    if "東京" in message or "東京都" in message:
        prefs["勤務地"] = {"score": 5, "value": "東京都"}

    # 例：給与
    if "600万" in message or "年収600" in message:
        prefs["給与"] = {"score": 4, "value": 600}

    # 例：勤務時間
    if "フレックス" in message:
        prefs["勤務時間"] = {"score": 3, "value": "フレックス可"}

    #業務内容
    matched_roles = []
    for keyword, roles in WORK_STYLE_MAP.items():
        if re.search(rf"{keyword}|{keyword}な", message):
            matched_roles.extend(roles)

    if matched_roles:
        prefs["業務内容"] = {
            "score": 5,
            "value": list(set(matched_roles))
        }

    return prefs

@cl.on_chat_start
async def start():
    await cl.Message(content="こんにちは！求職サポート「お仕事探すくん」です。お気軽にご希望をお聞かせください 😊").send()

@cl.on_message
async def handle_message(message: cl.Message):
    user_id = "Saki"
    job_db = load_job_database()
    goto_job_explanation = False

    # 位置情報の履歴取得（先にログを読み込む）
    previous_coords = None
    history = load_user_log(user_id)
    for entry in reversed(history):
        if "coords" in entry:
            previous_coords = tuple(entry["coords"])
            break

    # 地名抽出 → 緯度取得
    location_name = extract_location_from_message(message.content)
    user_coords = get_coordinates_from_location(location_name) if location_name else None

    #位置情報がない場合は履歴から復元
    if not user_coords and previous_coords:
        user_coords = previous_coords

    # 希望条件（実値）を抽出
    new_prefs = extract_user_preferences(message.content)  # ← あなたが定義する関数
    previous_prefs = load_latest_preferences(user_id)      # ← 過去の希望条件を取得
    merged_prefs = merge_preferences(new_prefs, previous_prefs)

    # スコア統合処理（前回＋今回）
    interest_scores = analyze_interests(message.content)
    previous_scores = load_latest_scores(user_id)
    merged_scores = merge_scores_preserving_old(interest_scores, previous_scores)

    #ユーザーログの保存
    save_user_log(
    user_id,
    message.content,
    merged_scores,
    coords=user_coords or previous_coords,
    preferences=merged_prefs  # ← ここに保存！
    )

    category_id = extract_category_from_message(message.content)
    if category_id:
        category_jobs = get_jobs_by_category(job_db, category_id)
        job_infos = [format_job_info(job) for job in category_jobs[:5]]
        reply = f"「{CATEGORY_LABELS[category_id]}」に該当する求人をご紹介します：\n"
        for info in job_infos:
            reply += f"\n{info}"
        await cl.Message(content=reply).send()
        return

    tags = extract_tags_from_message(message.content)
    filtered_titles = []
    filtered_db = {}

    if tags:
        filtered_titles = get_job_titles_by_tags(job_db, tags)
        filtered_db = filter_jobs_by_job_types(job_db, filtered_titles)

        if filtered_titles:
            suggestion = suggest_job_type_from_message(message.content, filtered_titles)
            job_type = suggestion["職種名"]
            job_description = suggestion["説明"]

            if job_type not in get_valid_job_titles(job_db):
                job_type = "営業職"
                job_description = "幅広い業界で活躍できる職種です。"

            related_job_types = list(set([job_type] + filtered_titles))
            filtered_db = filter_jobs_by_job_types(job_db, related_job_types)
            goto_job_explanation = True

    if not filtered_titles:

        # タグが空 or filtered_titlesが空 → GPTによる職種推定
        suggestion = suggest_job_type_from_message(message.content, get_valid_job_titles(job_db))
        job_type = suggestion["職種名"]
        job_description = suggestion["説明"]
        related_job_types = [job_type]
        filtered_db = filter_jobs_by_job_types(job_db, related_job_types)
        goto_job_explanation = True

    prompt = message.content if "詳しく" not in message.content else f"""
ユーザーは「{job_type}」について詳しく知りたいようです。
以下の形式で説明してください：

1. 職種の概要  
2. 主な仕事内容  
3. 求められるスキルや資格  
4. 向いている人の特徴  
5. この職種のメリット・デメリット  
"""

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    reply = response.choices[0].message.content.strip()

    # filtered_db が空なら全職種から推薦
    if not filtered_db:
        filtered_db = job_db

    #希望勤務地でフィルタ（merged_prefs を活用）
    if "勤務地" in merged_prefs:
        preferred_location = merged_prefs["勤務地"]["value"]
        filtered_db = {
            k: v for k, v in filtered_db.items()
            if preferred_location in v.get("勤務地", "")
        }

    if "業務内容" in merged_prefs:
        preferred_roles = merged_prefs["業務内容"]["value"]
        filtered_db = {
            k: v for k, v in filtered_db.items()
            if v.get("職種名") in preferred_roles or any(role in v.get("仕事内容", "") for role in preferred_roles)
        }

    # 求人推薦処理
    top_jobs = []

    # 希望勤務地が明言されている場合は距離フィルタを使わない
    if "勤務地" in merged_prefs:
        top_jobs = match_top_jobs(merged_scores, filtered_db, top_n=3)
    else:
        if user_coords:
            nearby_jobs = find_nearby_jobs(user_coords, filtered_db, max_distance_km=50)
            if nearby_jobs:
                filtered_jobs_dict = {f"{j['職種名']}_{j['会社名']}": j for j in nearby_jobs}
                top_jobs = match_top_jobs(merged_scores, filtered_jobs_dict, top_n=3)
            else:
                top_jobs = match_top_jobs(merged_scores, filtered_db, top_n=3)
        else:
            top_jobs = match_top_jobs(merged_scores, filtered_db, top_n=3)

    # top_jobs が空なら fallback 表示
    if not top_jobs:

        #filtered_db が空なら再フォールバック
        if not filtered_db:
            filtered_db = job_db

        fallback_jobs = list(filtered_db.values())[:3]
        reply = "完全に一致する求人は見つかりませんでしたが、近い条件の求人をご紹介します：\n"
        for job in fallback_jobs:
            reply += f"\n{format_job_info(job)}"
        await cl.Message(content=reply).send()
        return

    top_job_infos = [format_job_info(job) for job in top_jobs]
    job_suggestion = recommend_by_interest(merged_scores)
    followup_question = generate_followup_question(merged_scores) if merged_scores else ""

    supplemental_jobs = []
    if merged_scores and "給与" in merged_scores and merged_scores["給与"] >= 4:
        supplemental_jobs = suggest_high_salary_jobs(job_db, min_salary=700)

    full_reply = f"{reply}\n\n{job_suggestion}\n\n{followup_question}\n\n【おすすめ求人情報】\n"
    for job_info in top_job_infos:
        full_reply += f"\n{job_info}"

    if supplemental_jobs:
        full_reply += "\n\n💰 給与重視のあなたに、さらに高収入の求人もご紹介します：\n"
        for job in supplemental_jobs:
            full_reply += f"\n{format_job_info(job)}"

    await cl.Message(content=full_reply).send()