import requests
from dotenv import load_dotenv
import os

load_dotenv('.env')

token = os.getenv('META_LONG_TOKEN')
ad_account_id = os.getenv('META_AD_ACCOUNT_ID')

def get_meta_data(date_preset):
    url = f"https://graph.facebook.com/v19.0/act_{ad_account_id}/insights"
    params = {
        "access_token": token,
        "date_preset": date_preset,
        "fields": "spend,clicks,impressions,ctr,cpc,cpm,actions,action_values",
        "level": "account"
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "data" not in data or len(data["data"]) == 0:
        return None

    d = data["data"][0]
    spend = float(d.get("spend", 0))
    purchases = 0
    purchase_value = 0.0
    for action in d.get("actions", []):
        if action["action_type"] == "purchase":
            purchases = int(action["value"])
    for action in d.get("action_values", []):
        if action["action_type"] == "purchase":
            purchase_value = float(action["value"])

    roas = round(purchase_value / spend, 2) if spend > 0 else 0

    return {
        "spend": round(spend, 2),
        "clicks": int(d.get("clicks", 0)),
        "impressions": int(d.get("impressions", 0)),
        "ctr": round(float(d.get("ctr", 0)), 2),
        "cpc": round(float(d.get("cpc", 0)), 2),
        "cpm": round(float(d.get("cpm", 0)), 2),
        "purchases": purchases,
        "purchase_value": round(purchase_value, 2),
        "roas": roas
    }

def get_top_ads(date_preset, limit=5):
    url = f"https://graph.facebook.com/v19.0/act_{ad_account_id}/insights"
    params = {
        "access_token": token,
        "date_preset": date_preset,
        "fields": "ad_name,spend,actions,action_values",
        "level": "ad",
        "sort": "spend_descending",
        "limit": 50
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "data" not in data:
        return []

    ads = []
    for d in data["data"]:
        spend = float(d.get("spend", 0))
        if spend == 0:
            continue
        purchase_value = 0.0
        for action in d.get("action_values", []):
            if action["action_type"] == "purchase":
                purchase_value = float(action["value"])
        roas = round(purchase_value / spend, 2) if spend > 0 else 0
        ads.append({
            "ad_name": d.get("ad_name", ""),
            "spend": round(spend, 2),
            "purchase_value": round(purchase_value, 2),
            "roas": roas
        })

    ads.sort(key=lambda x: x["roas"], reverse=True)
    return ads[:limit]

def get_all_data(date_preset):
    return {
        "metrics": get_meta_data(date_preset),
        "top_ads": get_top_ads(date_preset)
    }

if __name__ == "__main__":
    for period in ["yesterday", "last_7d", "last_30d", "this_month"]:
        print(f"\n=== {period.upper()} ===")
        result = get_all_data(period)
        print("Metrikler:", result["metrics"])
        print("Top Reklamlar:")
        for ad in result["top_ads"]:
            print(f"  {ad['ad_name']} → ROAS: {ad['roas']}x | Harcama: ₺{ad['spend']}")
