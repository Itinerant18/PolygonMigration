import io
import os

from django.conf import settings
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


SCOPES = ["https://www.googleapis.com/auth/drive"]


def _resolve_path(path):
    if os.path.isabs(path):
        return path
    return os.path.join(str(settings.BASE_DIR), path)


def get_drive_service():
    creds_file = _resolve_path(settings.GOOGLE_DRIVE_CREDENTIALS_FILE)
    try:
        creds = service_account.Credentials.from_service_account_file(
            creds_file, scopes=SCOPES
        )
    except Exception:
        token_file = _resolve_path(settings.GOOGLE_DRIVE_TOKEN_FILE)
        creds = Credentials.from_authorized_user_file(token_file)
    return build("drive", "v3", credentials=creds)


def find_file_id(service, name, folder_id):
    result = service.files().list(
        q="name = '%s' and '%s' in parents and trashed = false" % (name, folder_id),
        fields="files(id, name)",
    ).execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]
    return None


def input_filename(problem_id, number):
    return "problem_%s_test_%02d.txt" % (problem_id, number)


def output_filename(problem_id, number):
    return "problem_%s_test_%02d.a" % (problem_id, number)


def upload_text_file(name, content):
    folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
    if not folder_id:
        raise Exception("Google Drive folder is not configured.")

    service = get_drive_service()

    # Google Drive is used for storage now (replaces Azure).
    # If the file already exists in the folder, update it
    # instead of creating a duplicate.
    existing_id = find_file_id(service, name, folder_id)
    with io.BytesIO((content or "").encode("utf-8")) as data:
        media = MediaIoBaseUpload(data, mimetype="text/plain")
        if existing_id:
            service.files().update(
                fileId=existing_id,
                media_body=media,
            ).execute()
            return existing_id
        created = service.files().create(
            body={"name": name, "parents": [folder_id]},
            media_body=media,
            fields="id",
        ).execute()
        return created.get("id")


def drive_file_url(file_id):
    return "https://drive.google.com/file/d/%s/view" % file_id
