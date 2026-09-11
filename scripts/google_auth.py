from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json',
    scopes=['https://www.googleapis.com/auth/adwords']
)

creds = flow.run_local_server(port=8080)
print("REFRESH TOKEN:")
print(creds.refresh_token)
