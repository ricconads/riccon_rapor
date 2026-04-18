import requests
from dotenv import load_dotenv
import os

load_dotenv('.env')

token = os.getenv('SHOPIFY_ACCESS_TOKEN')
shop = os.getenv('SHOPIFY_STORE')
headers = {"X-Shopify-Access-Token": token}

url = f"https://{shop}/admin/api/2024-01/reports.json"
r = requests.get(url, headers=headers)
print("Status:", r.status_code)
data = r.json()
reports = data.get('reports', [])
print(f"Toplam rapor: {len(reports)}")
for rep in reports:
    print(f"  ID: {rep.get('id')} | {rep.get('name')} | {rep.get('category')}")
