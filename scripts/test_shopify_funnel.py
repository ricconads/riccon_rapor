import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv('/Users/ahmetkidik/riccon/.env')

token = os.getenv('SHOPIFY_ACCESS_TOKEN')
shop = os.getenv('SHOPIFY_STORE')
headers = {"X-Shopify-Access-Token": token}

today = datetime.now().date()
start = (today - timedelta(days=1)).isoformat()
end = (today - timedelta(days=1)).isoformat()

print("=== CHECKOUTS (Ödeme Başlatma) ===")
url = f"https://{shop}/admin/api/2024-01/checkouts.json"
params = {
    "created_at_min": f"{start}T00:00:00",
    "created_at_max": f"{end}T23:59:59",
    "limit": 250
}
r = requests.get(url, headers=headers, params=params)
data = r.json()
print(f"Toplam checkout: {len(data.get('checkouts', []))}")

print("\n=== EVENTS (Ürün Görüntüleme) ===")
url2 = f"https://{shop}/admin/api/2024-01/events.json"
params2 = {
    "created_at_min": f"{start}T00:00:00",
    "created_at_max": f"{end}T23:59:59",
    "verb": "viewed",
    "limit": 10
}
r2 = requests.get(url2, headers=headers, params=params2)
print(r2.status_code)
print(r2.json())
