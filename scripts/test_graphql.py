import requests
from dotenv import load_dotenv
import os

load_dotenv('.env')

token = os.getenv('SHOPIFY_ACCESS_TOKEN')
shop = os.getenv('SHOPIFY_STORE')

url = f"https://{shop}/admin/api/2024-01/graphql.json"
headers = {
    "X-Shopify-Access-Token": token,
    "Content-Type": "application/json"
}

query = """
{
  orders(first: 1, query: "created_at:>=2026-04-17 created_at:<=2026-04-17") {
    edges {
      node {
        id
        createdAt
        subtotalPriceSet {
          shopMoney {
            amount
          }
        }
      }
    }
    pageInfo {
      hasNextPage
    }
  }
}
"""

r = requests.post(url, json={"query": query}, headers=headers)
print("Status:", r.status_code)
print(r.json())
