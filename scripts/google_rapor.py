from google.ads.googleads.client import GoogleAdsClient
from dotenv import load_dotenv
import os

load_dotenv('.env')

client = GoogleAdsClient.load_from_storage('google-ads.yaml')
customer_id = "7145021056"

def get_google_data(date_range):
    ga_service = client.get_service("GoogleAdsService")
    
    query = f"""
        SELECT
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value,
            metrics.clicks,
            metrics.impressions,
            metrics.ctr,
            metrics.average_cpc
        FROM customer
        WHERE segments.date DURING {date_range}
    """
    
    response = ga_service.search(customer_id=customer_id, query=query)
    
    spend = 0
    conversions = 0
    conversion_value = 0
    clicks = 0
    impressions = 0
    ctr = 0
    cpc = 0

    for row in response:
        spend += row.metrics.cost_micros / 1_000_000
        conversions += row.metrics.conversions
        conversion_value += row.metrics.conversions_value
        clicks += row.metrics.clicks
        impressions += row.metrics.impressions
        ctr = row.metrics.ctr * 100
        cpc = row.metrics.average_cpc / 1_000_000

    roas = round(conversion_value / spend, 2) if spend > 0 else 0
    bgbm = round((spend / impressions) * 1000, 2) if impressions > 0 else 0
    tbm = round(spend / clicks, 2) if clicks > 0 else 0

    return {
        "spend": round(spend, 2),
        "conversions": round(conversions, 0),
        "conversion_value": round(conversion_value, 2),
        "clicks": clicks,
        "impressions": impressions,
        "ctr": round(ctr, 2),
        "tbm": tbm,
        "bgbm": bgbm,
        "roas": roas
    }

def get_top_ads(date_range, limit=5):
    ga_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            ad_group_ad.ad.name,
            campaign.name,
            metrics.cost_micros,
            metrics.conversions_value,
            metrics.conversions
        FROM ad_group_ad
        WHERE segments.date DURING {date_range}
        AND metrics.cost_micros > 0
        ORDER BY metrics.cost_micros DESC
        LIMIT 50
    """

    response = ga_service.search(customer_id=customer_id, query=query)

    ads = []
    for row in response:
        spend = row.metrics.cost_micros / 1_000_000
        conv_value = row.metrics.conversions_value
        roas = round(conv_value / spend, 2) if spend > 0 else 0
        name = row.ad_group_ad.ad.name or row.campaign.name
        ads.append({
            "name": name,
            "spend": round(spend, 2),
            "roas": roas
        })

    ads.sort(key=lambda x: x["roas"], reverse=True)
    return ads[:limit]

def get_all_data(date_range):
    return {
        "metrics": get_google_data(date_range),
        "top_ads": get_top_ads(date_range)
    }

if __name__ == "__main__":
    periods = {
        "Dün": "YESTERDAY",
        "Son 7 Gün": "LAST_7_DAYS",
        "Son 30 Gün": "LAST_30_DAYS",
        "Bu Ay": "THIS_MONTH"
    }
    for label, period in periods.items():
        print(f"\n=== {label.upper()} ===")
        result = get_all_data(period)
        print("Metrikler:", result["metrics"])
        print("Top Reklamlar:")
        for ad in result["top_ads"]:
            print(f"  {ad['name']} → ROAS: {ad['roas']}x | Harcama: ₺{ad['spend']}")
