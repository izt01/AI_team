import json
from geopy.geocoders import Nominatim
import time

INPUT_PATH = "jobs.json"
OUTPUT_PATH = "jobs_with_coordinates.json"

def get_coordinates(address: str) -> tuple | None:
    geolocator = Nominatim(user_agent="job-matcher")
    try:
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
    except Exception as e:
        print(f"⚠️ 住所変換失敗: {address} → {e}")
    return None

def enrich_jobs_with_coordinates(input_path: str, output_path: str):
    with open(input_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    for key, job in jobs.items():
        address = job.get("勤務地")
        if not address:
            job["緯度"] = None
            job["経度"] = None
            continue

        coords = get_coordinates(address)
        if coords:
            job["緯度"], job["経度"] = coords
            print(f"✅ {address} → {coords}")
        else:
            job["緯度"] = None
            job["経度"] = None
            print(f"❌ 緯度経度取得失敗: {address}")

        time.sleep(1)  # Nominatimのレート制限対策

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"\n🎉 完了！保存先: {output_path}")

if __name__ == "__main__":
    enrich_jobs_with_coordinates(INPUT_PATH, OUTPUT_PATH)