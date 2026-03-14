from google_auth_oauthlib.flow import InstalledAppFlow
import json

credentials_dict = {
      "installed": {
          "client_id": "448903201916-t7ifcld715t2nvfh7oeaj9gpkv8sj19l.apps.googleusercontent.com",
          "client_secret": "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",
          "auth_uri": "https://accounts.google.com/o/oauth2/auth",
          "token_uri": "https://oauth2.googleapis.com/token",
          "redirect_uris": ["http://localhost"]
      }
}

flow = InstalledAppFlow.from_client_config(credentials_dict, ['https://www.googleapis.com/auth/drive'])
creds = flow.run_local_server(port=0)

print("\n" + "="*80)
print("SUCCESS! New refresh token:")
print("="*80)
print(f"{creds.refresh_token}\n")