# Polygon Migration Tool

## Overview

I worked on a Django app that fetches programming problems from Polygon, saves the problem and test-case data to PostgreSQL, and uploads the test-case input/output files to Google Drive. Only staff users can use the migration pages.

## Setup

I ran the project from the `PolygonMigration` folder (the one containing `manage.py`):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r ..\requirement.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

PostgreSQL and Redis run in Docker. The container names in this project are `polygon-postgres` and `polygon-redis`:

```powershell
docker run --name polygon-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=polygon_migration -p 5432:5432 -d postgres:15
docker run --name polygon-redis -p 6379:6379 -d redis:7
```

The app runs at:

```text
http://127.0.0.1:8000/
```

## Environment Variables

These are the actual variables read in `PolygonMigration/settings.py`. I only list names here; real values stay in my local `.env`.

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` — Django settings.
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` — PostgreSQL connection.
- `POLYGON_API_KEY`, `POLYGON_API_SECRET` — Polygon API credentials.
- `GOOGLE_DRIVE_CREDENTIALS_FILE` — path to the service-account JSON.
- `GOOGLE_DRIVE_FOLDER_ID` — Drive folder receiving the uploads.
- `GOOGLE_DRIVE_UPLOAD_ENABLED` — `True` enables uploads.
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_SSL` — Redis cache for test cases.

My `.env` sits next to `manage.py` and I never commit it. The repo `.gitignore` already excludes `.env` and `*.json`, so credential files can't be committed by accident.

## Login Flow

1. I open `http://127.0.0.1:8000/users/login/`.
2. The form in `users/templates/users/login.html` posts email + password to `users/views.py::login_view`.
3. Django authenticates via `users/backends.py::EmailBackend`.
4. A staff login redirects to the migration page (`problems:index` at `/`); non-staff users get "You do not have staff access."
5. Wrong credentials show "Invalid email or password." I tested both.

## Fetching a Polygon Problem

1. I type a Polygon problem ID into the form on `/` and click Fetch Problem.
2. `problems/views.py::index` sends the ID to the backend.
3. `problems/polygon_api.py::PolygonAPI` calls `get_problem_info`, `download_and_extract_package`, `get_all_test_cases` (cached 30 minutes with `store_test_cases_in_redis`), plus solution and checker lookups. `parse_problem_html` in `views.py` extracts the title, legend, formats, and notes.
4. The page shows the title, slug, statement, input/output formats, test-case previews with sample flags, the test count, and the reference solution.
5. I review everything before saving anything.

Authentication is simple: each request sends the API key with a `time` stamp and an `apiSig` signature, which `_generate_api_sig` builds from the request params plus the API secret using SHA-512. The secret itself never leaves the server.

## Saving a Problem

1. I select a difficulty and add tags.
2. I click **Create/Update problem in Database**.
3. `problems/views.py::index` creates or updates the `Problem` row in `problems/models.py` (matched by `polygon_id`).
4. Tags are saved through `ProblemTag` (`get_or_create` + the `extra_tags` relation), and statement samples go to `SampleTestCase`.
5. I see "Problem saved to database." If I forget the difficulty, I get "Please select a difficulty level before migrating to database." The template is `problems/templates/problems/index.html`.

## Saving Test Cases

1. I click **Migrate Test Description to Database** (active only after the problem row exists).
2. The backend refuses with "Please migrate the problem to the database first." if there is no `Problem` row.
3. The current code uses delete-and-recreate: it deletes this problem's `ProblemTestCase` rows and creates one row per fetched test, so re-running never duplicates. Nothing is skipped, even empty input/output.
4. Each row stores input, output, order, description, and `is_sample`.
5. Before deleting, the code remembers each row's Drive file IDs by test order and writes them back, so re-migration keeps the Drive links.
6. I see "N test cases saved to database." If saved and fetched counts ever differ, it shows a warning instead.

## Uploading to Google Drive

1. I click **Upload Test Cases to Google Drive**.
2. `problems/google_drive.py::get_drive_service` loads the service-account file from `GOOGLE_DRIVE_CREDENTIALS_FILE` and builds the Drive v3 client.
3. For every test case, `upload_text_file` uploads the input file, then the matching output file.
4. If a same-named file already exists in the folder (`find_file_id`), the code calls `files.update` on it instead of creating a duplicate.
5. The returned file IDs are stored on the matching `ProblemTestCase` row (`drive_input_file_id`, `drive_output_file_id`).
6. I see "N test cases uploaded to Google Drive." plus "Upload failed for N test cases." if any single upload fails.

Current filename format (flat names in the one configured folder, carrying the problem ID and test number):

```text
problem_{problem_id}_test_{number}.txt
problem_{problem_id}_test_{number}.a
```

The `.txt` file is the test input, the `.a` file is the expected output. `{problem_id}` here is the database `Problem` ID and `{number}` is the 1-based test number.

## Database and Storage Difference

- PostgreSQL holds the problem metadata and every test-case record.
- Google Drive holds the actual input/output files.
- The `ProblemTestCase` row links the two through its Drive file IDs.

## Verification

I ran:

```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py migrate
python manage.py test
```

`check` was clean, no model changes were pending, migrations were up to date, and all 5 tests passed.

My manual test on problem "A+B" (Polygon ID 69927):

- Logged in as staff.
- Fetched the problem: 12 test cases shown (3 sample, 9 regular).
- Saved the problem: 1 row, "Problem saved to database."
- Saved test cases: "12 test cases saved to database.", 12 rows in the database.
- Uploaded to Drive: "12 test cases uploaded to Google Drive.", 12 `.txt` + 12 `.a` files, contents matching the database.
- Re-uploaded: still 24 files, no duplicates.
- Re-ran the test-case migration: still 12 rows, Drive IDs intact.

## Troubleshooting

- **Django package missing:** my fresh venv had no Django, so `manage.py` failed with `ModuleNotFoundError`. Check with `python -c "import django"` and reinstall from `..\requirement.txt` using Python 3.12.
- **PostgreSQL not reachable:** check `docker ps` for `polygon-postgres` and test the port with `Test-NetConnection 127.0.0.1 -Port 5432` (same for Redis: `polygon-redis`, port 6379).
- **Drive upload refused:** "Google Drive folder is not configured." means `GOOGLE_DRIVE_FOLDER_ID` is empty; "Google Drive upload is disabled." means `GOOGLE_DRIVE_UPLOAD_ENABLED` is not `True`. Also confirm the folder is shared with the service-account email.
- **Bad Polygon ID:** fetching ID `0` shows "Migration failed and all changes have been rolled back." with no traceback. Double-check `POLYGON_API_KEY`/`POLYGON_API_SECRET` in `.env` (never print them).

## Current Storage Choice

The starter repo was written for Azure, but that path needs Cloud Storage billing that wasn't enabled. The working implementation uses Google Drive instead. Azure code is still visible but disabled/commented out (`problems/AzureTestcase.py`, the Azure methods in `problems/polygon_api.py`, the Azure settings in `PolygonMigration/settings.py`, and the pinned Azure packages in `requirement.txt`). No Azure upload runs anywhere in the current flow.

## Security Notes

- I never commit `.env` or any `*-service-account.json` / token JSON.
- I never paste Polygon secrets into screenshots, videos, or docs.
- The Drive folder should stay private to the project accounts (I found mine shared link-readable during testing and flagged it separately).
- `.env.example` uses placeholder values only.
