import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from collections import defaultdict

load_dotenv('/Users/ahmetkidik/riccon/.env')

token = os.getenv('SHOPIFY_ACCESS_TOKEN')
shop = os.getenv('SHOPIFY_STORE')
headers = {"X-Shopify-Access-Token": token}

today = datetime.now().date()
start = (today - timedelta(days=1)).isoformat()
end = (today - timedelta(days=1)).isoformat()

url = f"https://{shop}/admin/api/2024-01/orders.json"
params = {
    "status": "any",
    "created_at_min": f"{start}T00:00:00",
    "created_at_max": f"{end}T23:59:59",
    "limit": 250,
    "fields": "created_at,total_price,financial_status"
}

r = requests.get(url, headers=headers, params=params)
orders = r.json().get('orders', [])

hourly = defaultdict(lambda: {"count": 0, "revenue": 0})
for order in orders:
    if order.get('financial_status') not in ['refunded', 'voided']:
        hour = int(order['created_at'][11:13])
        hourly[hour]["count"] += 1
        hourly[hour]["revenue"] += float(order.get('total_price', 0))

print("Saat | Sipariş | Gelir")
for h in range(24):
    d = hourly[h]
    print(f"{h:02d}:00 | {d['count']} | ₺{d['revenue']:.2f}")
