import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import re
from collections import defaultdict

load_dotenv('/Users/ahmetkidik/riccon/.env')

token = os.getenv('SHOPIFY_ACCESS_TOKEN')
shop = os.getenv('SHOPIFY_STORE')
headers = {"X-Shopify-Access-Token": token}

def get_date_range(period):
    today = datetime.now().date()
    if period == "yesterday":
        start = today - timedelta(days=1)
        end = today - timedelta(days=1)
    elif period == "last_7d":
        start = today - timedelta(days=7)
        end = today - timedelta(days=1)
    elif period == "last_30d":
        start = today - timedelta(days=30)
        end = today - timedelta(days=1)
    elif period == "this_month":
        start = today.replace(day=1)
        end = today - timedelta(days=1)
    return start.isoformat(), end.isoformat()

def get_next_url(link_header):
    if not link_header:
        return None
    parts = link_header.split(',')
    for part in parts:
        if 'rel="next"' in part:
            match = re.search(r'<([^>]+)>', part)
            if match:
                return match.group(1)
    return None

def get_shopify_data(period):
    start, end = get_date_range(period)

    url = f"https://{shop}/admin/api/2024-01/orders.json"
    params = {
        "status": "any",
        "created_at_min": f"{start}T00:00:00",
        "created_at_max": f"{end}T23:59:59",
        "limit": 250,
        "fields": "total_price,total_discounts,financial_status,line_items,created_at"
    }

    all_orders = []
    while True:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        orders = data.get('orders', [])
        all_orders.extend(orders)
        next_url = get_next_url(response.headers.get('Link', ''))
        if not next_url:
            break
        url = next_url
        params = {}

    total_sales = 0
    total_orders = 0
    product_sales = {}
    hourly = defaultdict(lambda: {"count": 0, "revenue": 0.0})

    for order in all_orders:
        if order.get('financial_status') not in ['refunded', 'voided']:
            price = float(order.get('total_price', 0))
            total_sales += price
            total_orders += 1
            hour = int(order['created_at'][11:13])
            hourly[hour]["count"] += 1
            hourly[hour]["revenue"] += price
            for item in order.get('line_items', []):
                name = item.get('title', '')
                qty = int(item.get('quantity', 0))
                item_price = float(item.get('price', 0)) * qty
                product_sales[name] = product_sales.get(name, 0) + item_price

    aov = round(total_sales / total_orders, 2) if total_orders > 0 else 0
    top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:20]

    hourly_data = []
    for h in range(24):
        hourly_data.append({
            "hour": f"{h:02d}:00",
            "count": hourly[h]["count"],
            "revenue": round(hourly[h]["revenue"], 2)
        })

    checkout_url = f"https://{shop}/admin/api/2024-01/checkouts.json"
    checkout_params = {
        "created_at_min": f"{start}T00:00:00",
        "created_at_max": f"{end}T23:59:59",
        "limit": 250
    }
    all_checkouts = []
    while True:
        checkout_response = requests.get(checkout_url, headers=headers, params=checkout_params)
        checkouts = checkout_response.json().get('checkouts', [])
        all_checkouts.extend(checkouts)
        next_url = get_next_url(checkout_response.headers.get('Link', ''))
        if not next_url:
            break
        checkout_url = next_url
        checkout_params = {}

    checkout_count = len(all_checkouts)
    add_to_cart = checkout_count + total_orders

    return {
        "total_sales": round(total_sales, 2),
        "total_orders": total_orders,
        "aov": aov,
        "top_products": top_products,
        "add_to_cart": add_to_cart,
        "checkout_count": checkout_count,
        "hourly_data": hourly_data,
        "sessions": 0
    }

if __name__ == "__main__":
    for period in ["yesterday"]:
        print(f"\n=== {period.upper()} ===")
        result = get_shopify_data(period)
        print(f"Toplam Satış: ₺{result['total_sales']}")
        print(f"Sipariş: {result['total_orders']}")
        print("Saatlik:")
        for h in result['hourly_data']:
            if h['count'] > 0:
                print(f"  {h['hour']} | {h['count']} sipariş | ₺{h['revenue']}")
