import requests
from dotenv import load_dotenv
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser
import threading

load_dotenv('/Users/ahmetkidik/riccon/.env')

shop = "t9dr0s-s8.myshopify.com"
client_id = os.getenv('SHOPIFY_CLIENT_ID')
client_secret = os.getenv('SHOPIFY_CLIENT_SECRET')
scopes = "read_orders,read_products,read_analytics,read_inventory"
redirect_uri = "http://localhost:3000/callback"

auth_code = None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if 'code' in params:
            auth_code = params['code'][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Kod alindi! Terminale don.")
    def log_message(self, format, *args):
        pass

server = HTTPServer(('localhost', 3000), Handler)

auth_url = f"https://{shop}/admin/oauth/authorize?client_id={client_id}&scope={scopes}&redirect_uri={redirect_uri}"
print("Tarayıcı açılıyor...")
webbrowser.open(auth_url)

server.handle_request()

if auth_code:
    response = requests.post(f"https://{shop}/admin/oauth/access_token", json={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code
    })
    data = response.json()
    print("ACCESS TOKEN:")
    print(data.get('access_token'))
