from google.ads.googleads.client import GoogleAdsClient
from dotenv import load_dotenv

load_dotenv('/Users/ahmetkidik/riccon/.env')

client = GoogleAdsClient.load_from_storage('/Users/ahmetkidik/riccon/google-ads.yaml')

ga_service = client.get_service("GoogleAdsService")

query = """
    SELECT
        campaign.id,
        campaign.name,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros
    FROM campaign
    WHERE segments.date DURING YESTERDAY
    ORDER BY metrics.cost_micros DESC
    LIMIT 5
"""

response = ga_service.search(customer_id="7145021056", query=query)

for row in response:
    cost = row.metrics.cost_micros / 1_000_000
    print(f"Kampanya: {row.campaign.name} | Tıklama: {row.metrics.clicks} | Harcama: ₺{cost:.2f}")
