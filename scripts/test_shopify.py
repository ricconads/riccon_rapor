import requests
from dotenv import load_dotenv
import os

load_dotenv('/Users/ahmetkidik/riccon/.env')

token = os.getenv('SHOPIFY_ACCESS_TOKEN')
shop = os.getenv('SHOPIFY_STORE')

url = f"https://{shop}/admin/api/2024-01/shop.json"
headers = {"X-Shopify-Access-Token": token}

response = requests.get(url, headers=headers)
data = response.json()
print(data.get('shop', {}).get('name'))
print(data.get('shop', {}).get('currency'))
print(data.get('shop', {}).get('domain'))
