# PolygonMigration — Documentation

## 1. Project overview

PolygonMigration is a Django web app that migrates programming problems from
[Polygon](https://polygon.codeforces.com/) into a local PostgreSQL database
and uploads the problem's test-case files to Google Drive.

- `PolygonMigration/` — Django project (settings, root URLs, `manage.py`).
- `PolygonMigration/problems/` — Polygon integration and migration logic:
  `views.py` (`index`), `polygon_api.py` (`PolygonAPI`),
  `google_drive.py` (Drive helper), `models.py`
  (`Problem`, `ProblemTag`, `SampleTestCase`, `ProblemTestCase`),
  `AzureTestcase.py` (disabled legacy code, kept for reference),
  `templates/problems/index.html` (main UI).
- `PolygonMigration/users/` — email-based login (`views.py::login_view`,
  `backends.py::EmailBackend`, `templates/users/login.html`).
- `PolygonMigration/contents/` — topic/content management (not part of the
  migration flow).
- Storage: PostgreSQL for problem/test-case data, Google Drive for
  test-case files. Google Drive is the only active cloud provider;
  Azure code is commented out and no Azure button is shown.

## 2. Local setup

Prerequisites: Python 3.12, Docker (PostgreSQL + Redis), Polygon API
credentials, a Google Drive folder shared with a service account.

```powershell
cd PolygonMigration
python -m venv venv
.\venv\Scripts\activate
pip install -r ..\requirement.txt
```

Copy `PolygonMigration/.env.example` to `PolygonMigration/.env`
(beside `manage.py`) and fill in the values from section 3.

## 3. Required environment variables (no real values here)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` locally, `False` in production |
| `ALLOWED_HOSTS` | e.g. `localhost,127.0.0.1` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | PostgreSQL connection |
| `POLYGON_API_KEY` / `POLYGON_API_SECRET` | Polygon API auth (section 15) |
| `GOOGLE_DRIVE_CREDENTIALS_FILE` | Service-account JSON path, e.g. `credentials/google-drive-service-account.json` |
| `GOOGLE_DRIVE_FOLDER_ID` | Target Drive folder ID |
| `GOOGLE_DRIVE_UPLOAD_ENABLED` | `True` to allow uploads |
| `GOOGLE_DRIVE_TOKEN_FILE` | Optional OAuth fallback, e.g. `gdrive-token.json` |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` / `REDIS_SSL` | Redis cache for test cases |
| `CUSTOM_CHECKER_DIR` | Optional dir for compiling custom checkers |

## 4. Docker PostgreSQL and Redis startup

```powershell
docker run --name polygon-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=polygon_migration -p 5432:5432 -d postgres:15
docker run --name polygon-redis -p 6379:6379 -d redis:7
```

Match these to the `DB_*` / `REDIS_*` variables in `.env`
(`DB_HOST=localhost`, `DB_PORT=5432`, `REDIS_HOST=localhost`, `REDIS_PORT=6379`).

## 5. Django migration and startup commands

Run from `PolygonMigration/` (beside `manage.py`):

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

App: `http://localhost:8000/` · Admin: `http://localhost:8000/admin/`

Validation used for this project:

```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py migrate
python manage.py test
```

## 6. Login flow

- The user opens `/users/login/` (`users/urls.py`, `users/views.py::login_view`).
- The user enters email + password and submits.
  Request: `POST /users/login/` with `email`, `password`.
- The backend authenticates via `users/backends.py::EmailBackend` and
  `django.contrib.auth.authenticate`.
- Only staff users are let in: on success `login(request, user)` runs and the
  user is redirected to `problems:index` (`/`). Non-staff users see
  "You do not have staff access." Wrong credentials show
  "Invalid email or password." (`users/templates/users/login.html` renders
  these via Django messages).
- Database records written: none (session only).
- Files uploaded: none.
- The migration page itself (`problems/views.py::index`) is additionally
  guarded by `user_passes_test(lambda u: u.is_authenticated and u.is_staff)`,
  so non-staff users are sent back to `/users/login/`.

## 7. Polygon problem-fetch flow

- The user clicks **Fetch Problem** on `/` after typing a Polygon Problem ID.
  Request: `POST /` with `problem_id`.
- Handler: `problems/views.py::index`.
- The backend (`problems/polygon_api.py::PolygonAPI`):
  1. `get_problem_info(polygon_id)` — problem metadata (time/memory limits).
  2. `download_and_extract_package(polygon_id)` — downloads the latest
     `standard` package, unzips it, returns `problem.html`.
  3. `views.py::parse_problem_html` — extracts title, legend, input/output
     formats, notes.
  4. `get_all_test_cases(polygon_id)` — lists tests, then fetches each test's
     input/output; result cached 30 min via `store_test_cases_in_redis`.
  5. `problem.checker` request + `get_custom_checker_info` — checker type.
  6. Main solution lookup via `problem.solutions` + `problem.viewSolution`.
- Polygon API called: `problem.info`, `problem.packages`, `problem.package`,
  `problem.tests`, `problem.testInput`, `problem.testAnswer`,
  `problem.updateWorkingCopy`, `problem.solutions`, `problem.viewSolution`,
  `problem.checker`.
- Database records written: none on fetch alone.
- Files uploaded: none.
- Messages: the page re-renders with statement, formats, test-case previews,
  and the reference solution. Errors show in the red alert box.

## 8. Problem-to-database flow

- The user picks a difficulty, picks/creates tags, then clicks
  **Create/Update problem in Database**.
  Request: `POST /` with `problem_id`, `migrate_to_db=1`, `difficulty`,
  `tags` (one per selected tag).
- Handler: `problems/views.py::index` (`if migrate_to_db:` branch).
- The backend reuses the fetched data from section 7, requires `difficulty`,
  then updates the existing `Problem` row for that `polygon_id` or creates it
  (`title`, `slug`, `difficulty`, statement/formats, limits, checker type,
  `test_case_count`, `notes`). Selected tags are attached via
  `ProblemTag.objects.get_or_create` + `problem_obj.extra_tags`.
  Sample tests from the fetched set are written to `SampleTestCase`.
- Polygon API called: same as section 7 (data is re-fetched for display).
- Database records written: one `Problem` row (created or updated);
  `ProblemTag` rows as needed; `SampleTestCase` rows for statement samples.
- Files uploaded: none.
- Messages: "Problem saved to database." Missing difficulty shows
  "Please select a difficulty level before migrating to database."

## 9. Test-case-to-database flow

- The user clicks **Migrate Test Description to Database** (enabled only after
  the problem row exists).
  Request: `POST /` with `problem_id`, `migrate_test_cases_to_db=1`.
- Handler: `problems/views.py::index` (`if migrate_test_cases_to_db:` branch).
- The backend loads every test case from Redis
  (`get_test_cases_from_redis`, falling back to `get_all_test_cases` +
  `store_test_cases_in_redis`), remembers existing Drive file IDs per test
  order, deletes this problem's `ProblemTestCase` rows, then re-creates one
  row per fetched test (`is_sample`, `input`, `output`, `description`,
  `order`, preserved `drive_input_file_id`/`drive_output_file_id`).
  Nothing is skipped: rows are written even when input/output is empty.
- Polygon API called: `problem.tests` / `problem.testInput` /
  `problem.testAnswer` only on a Redis cache miss.
- Database records written: `ProblemTestCase` rows — exactly one per fetched
  test, so re-running replaces instead of duplicating.
- Files uploaded: none.
- Messages: "N test cases saved to database." If the saved count ever
  differs from the fetched count, a warning is shown instead:
  "Warning: only X of Y test cases saved to database." Migrating before the
  problem row exists shows "Please migrate the problem to the database first."

## 10. Test-case-to-Google-Drive flow

- The user clicks **Upload Test Cases to Google Drive** (enabled only after
  the problem row exists).
  Request: `POST /` with `problem_id`, `migrate_to_drive=1`.
- Handler: `problems/views.py::index` (`if migrate_to_drive:` branch).
- The backend loads every test case (Redis first, Polygon fallback, same as
  section 9), then for each test calls `problems/google_drive.py::
  upload_text_file` twice — once for the input file, once for the output
  file — and stores the returned Drive file IDs on the matching
  `ProblemTestCase` row (`drive_input_file_id`, `drive_output_file_id`).
- Google Drive API called: `files.list` (find existing by name in the folder),
  then `files.create` (new file) or `files.update` (file with the same name
  already exists, so re-uploads update instead of duplicating).
- Database records written: `ProblemTestCase.drive_input_file_id` and
  `drive_output_file_id` per test.
- Files uploaded: one input + one output file per test case (section 12).
- Messages: "N test cases uploaded to Google Drive." Per-test failures are
  counted and reported as "Upload failed for N test cases." Uploads are
  refused with "Google Drive upload is disabled." /
  "Google Drive folder is not configured." when the settings are missing.

## 11. Google Drive configuration

1. Create a Google Cloud service account and download its JSON key.
2. Create a Drive folder for test-case uploads.
3. Share the folder with the service-account email (Editor access),
   otherwise uploads fail with an API permission error.
4. Set in `PolygonMigration/.env`:

```env
GOOGLE_DRIVE_CREDENTIALS_FILE=credentials/google-drive-service-account.json
GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id
GOOGLE_DRIVE_UPLOAD_ENABLED=True
```

`problems/google_drive.py::get_drive_service` loads the service-account file
(relative paths resolve against `settings.BASE_DIR`) and builds the
Drive v3 client; if that file is missing it falls back to the OAuth token in
`GOOGLE_DRIVE_TOKEN_FILE`. `authenticate_gdrive.py` is a standalone helper
for the one-time OAuth flow and manual upload test.

## 12. Google Drive folder/file naming structure

Drive has no real subfolders in this implementation: all files live flat in
the configured folder, and the names carry the problem ID and test number
(this is the equivalent of the logical layout
`test_cases/{problem_id}/{test_number}` input /
`test_cases/{problem_id}/{test_number}.a` output):

- Input: `problems/google_drive.py::input_filename` →
  `problem_{db_problem_id}_test_{NN}.txt`
  (e.g. `problem_12_test_03.txt`). Kept as `.txt` per the working prototype.
- Output: `problems/google_drive.py::output_filename` →
  `problem_{db_problem_id}_test_{NN}.a`
  (e.g. `problem_12_test_03.a`).

`{db_problem_id}` is the `Problem` database ID (`problem_obj.id`) and `{NN}`
is the 1-based, zero-padded test number. The `.txt` vs `.a` suffix keeps
input and output clearly distinguishable.
`drive_file_url(file_id)` builds
`https://drive.google.com/file/d/{id}/view` for any stored file ID.

## 13. How to verify uploaded files

1. Open Google Drive in a browser and open the folder whose ID is in
   `GOOGLE_DRIVE_FOLDER_ID`.
2. Search for `problem_{id}_test_` to list one problem's files; open an
   input/output pair and confirm the contents match the test-case preview
   on the migration page.
3. In Django admin (`/admin/` → Problems → Problem test cases), each row
   shows its stored Drive file IDs after upload.
4. In a Django shell, compare counts:
   `ProblemTestCase.objects.filter(problem_id=<id>).count()` should equal the
   "All Test Cases (N total)" number on the page.
5. Re-click **Upload Test Cases to Google Drive**: no duplicates should
   appear — existing names are updated in place (`files.update`).

## 14. External Polygon API endpoints used by the code

Base URL: `https://polygon.codeforces.com/api/`
(`problems/polygon_api.py::PolygonAPI.API_URL`).

| Endpoint | Used by |
|---|---|
| `problem.info` | `get_problem_info` — metadata, limits |
| `problem.packages` | `download_and_extract_package` — find latest package |
| `problem.package` | `download_and_extract_package` — download zip |
| `problem.tests` | `get_test_cases`, `get_all_test_cases` — test list |
| `problem.testInput` | `get_all_test_cases` — per-test input |
| `problem.testAnswer` | `get_all_test_cases` — per-test output |
| `problem.updateWorkingCopy` | `views.py::index` — before reading solutions |
| `problem.solutions` | solution lookup in `views.py::index` |
| `problem.viewSolution` | solution content in `views.py::index` |
| `problem.checker` | checker type + `get_custom_checker_info` |
| `problem.statements` | `get_statements` helper (defined, not in main flow) |
| `problem.script` | `get_test_script` helper (defined, not in main flow) |
| `problem.files` / `problem.viewFile` | `get_problem_files`, `get_file_content`, custom-checker fetch helpers |

## 15. How Polygon requests are authenticated

`PolygonAPI._generate_api_sig(method_name, params)`:

1. Adds `apiKey` and current `time` to the params.
2. Sorts params, URL-encodes them, prepends a random 6-char prefix:
   `{rand}/{method}?{params}#{api_secret}`.
3. SHA-512 hashes that string; `apiSig = {rand}{hash}`.
4. `_make_request` POSTs `apiKey`, `apiSig`, `time` plus the method params.
   A `status == FAILED` response raises `Polygon API Error: <comment>`.
   `_make_plain_request` returns raw text (used for test input/output and
   solution source).

## 16. Short troubleshooting section

| Symptom | Likely cause / fix |
|---|---|
| `POLYGON_API_KEY and POLYGON_API_SECRET must be set` at startup | Missing vars in `PolygonMigration/.env` |
| "Google Drive folder is not configured." | `GOOGLE_DRIVE_FOLDER_ID` empty |
| "Google Drive upload is disabled." | `GOOGLE_DRIVE_UPLOAD_ENABLED` is not `True` |
| Drive permission/404 errors | Folder not shared with the service-account email (needs Editor) |
| Fetch works but test list is empty/slow | Redis keys expired (30 min TTL) — page refetches from Polygon; large test sets take minutes |
| "Migration failed and all changes have been rolled back." | Any exception inside the POST (e.g. duplicate `slug` for same-title problems); check `logs/project.log` |
| `g++` missing when compiling a custom checker | Install a C++ compiler or set `CUSTOM_CHECKER_DIR`; checker compile is optional |
| DB connection errors | PostgreSQL Docker container not running; check `DB_*` vars and `docker ps` |

## 17. A note that .env and credential files must not be committed

Never commit `PolygonMigration/.env`, `*-service-account.json`,
`gdrive-oauth-credentials.json`, or `gdrive-token.json`. The repo
`.gitignore` already excludes `.env`, `.env.*`, and `*.json`, and
`GOOGLE_DRIVE_*` values must only ever live in the local `.env` file —
`settings.py` and `problems/google_drive.py` read them from the
environment and contain no hardcoded emails, keys, folder IDs, or passwords.
