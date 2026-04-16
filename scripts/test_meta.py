import requests
from dotenv import load_dotenv
import os

load_dotenv('/Users/ahmetkidik/riccon/.env')

token = os.getenv('META_LONG_TOKEN')
ad_account_id = os.getenv('META_AD_ACCOUNT_ID')

url = f"https://graph.facebook.com/v19.0/act_{ad_account_id}"
params = {
    "fields": "name,currency,account_status",
    "access_token": token
}

response = requests.get(url, params=params)
data = response.json()
print(data)
