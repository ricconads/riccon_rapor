import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv('.env')

token = os.getenv('SHOPIFY_ACCESS_TOKEN')
shop = os.getenv('SHOPIFY_STORE')

url = f"https://{shop}/admin/api/2024-01/graphql.json"
headers = {
    "X-Shopify-Access-Token": token,
    "Content-Type": "application/json"
}

# 17 Nisan Türkiye = 16 Nisan 21:00 UTC - 17 Nisan 20:59 UTC
start_utc = "2026-04-16T21:00:00Z"
end_utc = "2026-04-17T20:59:59Z"

query = f"""
{{
  orders(first: 250, query: "created_at:>={start_utc} created_at:<={end_utc} financial_status:paid OR financial_status:partially_paid OR financial_status:pending") {{
    edges {{
      node {{
        subtotalPriceSet {{
          shopMoney {{
            amount
          }}
        }}
      }}
    }}
    pageInfo {{
      hasNextPage
    }}
  }}
}}
"""

r = requests.post(url, json={"query": query}, headers=headers)
data = r.json()
orders = data['data']['orders']['edges']
total = sum(float(o['node']['subtotalPriceSet']['shopMoney']['amount']) for o in orders)
print(f"Sipariş sayısı: {len(orders)}")
print(f"Toplam: ₺{total:.2f}")
print(f"Sonraki sayfa var mı: {data['data']['orders']['pageInfo']['hasNextPage']}")
