import requests
from dotenv import load_dotenv
import os

load_dotenv('.env')

token = os.getenv('SHOPIFY_ACCESS_TOKEN')
shop = os.getenv('SHOPIFY_STORE')
headers = {"X-Shopify-Access-Token": token}

url = f"https://{shop}/admin/api/2024-01/orders/count.json"
params = {
    "status": "any",
    "created_at_min": "2026-04-16T21:00:00Z",
    "created_at_max": "2026-04-17T20:59:59Z",
    "financial_status": "paid,partially_paid,pending,authorized"
}
r = requests.get(url, headers=headers, params=params)
print("Sipariş sayısı:", r.json())
