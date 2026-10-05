import os
import io
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ['https://www.googleapis.com/auth/drive']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, 'gdrive-oauth-credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'gdrive-token.json')

def authenticate():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print(f"Error: OAuth client secrets file not found at: {CLIENT_SECRETS_FILE}")
                print("Please download your OAuth client JSON from GCP Console and save it as:")
                print(f"  {CLIENT_SECRETS_FILE}")
                sys.exit(1)
            print(f"Starting authentication flow using {CLIENT_SECRETS_FILE}...")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print(f"Credentials successfully saved to {TOKEN_FILE}")
        
    return creds

def test_drive_upload(creds, folder_id):
    service = build('drive', 'v3', credentials=creds)
    print(f"\nTesting upload to folder ID: {folder_id}...")
    file_metadata = {
        'name': 'oauth_upload_test.txt',
        'parents': [folder_id]
    }
    media = MediaIoBaseUpload(io.BytesIO(b'OAuth 2.0 user upload test successful!'), mimetype='text/plain')
    try:
        created_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name'
        ).execute()
        print(f"SUCCESS! Uploaded test file: {created_file.get('name')} (ID: {created_file.get('id')})")
        service.files().delete(fileId=created_file.get('id')).execute()
        print("SUCCESS! Cleaned up test file.")
        print("\nYour Google Drive is fully ready for Polygon Migration!")
    except Exception as e:
        print(f"Upload test failed: {e}")

if __name__ == '__main__':
    creds = authenticate()
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')
    test_drive_upload(creds, folder_id)
