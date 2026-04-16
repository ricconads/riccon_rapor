from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    '/Users/ahmetkidik/riccon/client_secret.json',
    scopes=['https://www.googleapis.com/auth/adwords']
)

flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'

auth_url, _ = flow.authorization_url(prompt='consent')
print("Bu URL'yi tarayıcında aç:")
print(auth_url)
print()
code = input("Gelen kodu buraya yapıştır: ")

flow.fetch_token(code=code)
print("REFRESH TOKEN:")
print(flow.credentials.refresh_token)
