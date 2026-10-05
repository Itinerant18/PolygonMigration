# Issues Analysis

## Summary

| Type | Critical | High | Medium | Low | Total |
|------|----------|------|--------|-----|-------|
| Product Issues | 0 | 2 | 1 | 0 | 3 |
| Code Issues | 0 | 1 | 1 | 1 | 3 |

---

## Product Issues

### [P1] Test-case migration saves only some test cases but reports success

**Severity**: High

**Location**: `PolygonMigration/problems/views.py` (`migrate_test_cases_to_db` block), visible at `/admin/problems/problemtestcase/`

**Description**:
The Polygon page shows 21 test cases for a problem, but after clicking "Migrate Test Description to Database" only 8-10 records appear in the admin. The old code skipped every test case with empty input or output (`if input_data and output_data`) and truncated the rest to 260 characters, then still showed a success message. The user has no way to know the migration was incomplete.

**Impact**:

- Users believe all 21 test cases were migrated when they were not.
- Missing test cases cause significant data loss for judging.
- Re-running the migration does not fix the count because of index-based matching.

**Suggested Fix**:
Save every fetched test case (delete-and-recreate per problem, or `update_or_create` on `(problem, order)`), never truncate input/output, and compare saved vs fetched counts: show `21 test cases saved to database.` on full success and a warning otherwise.

---

### [P2] Test-case input/output truncated to 260 characters

**Severity**: High

**Location**: `PolygonMigration/problems/views.py` (`truncated_input = input_data[:260]`)

**Description**:
Before saving, input and output were cut to the first 260 characters. Full test data was silently discarded, so stored cases do not match the Polygon originals.

**Impact**:

- Judge results are wrong for any test longer than 260 characters.
- Data cannot be recovered without re-migrating from Polygon.

**Suggested Fix**:
Store the full input and output text. The fix removes the `[:260]` truncation.

---

### [P3] Repeated uploads can create duplicate files in storage

**Severity**: Medium

**Location**: `PolygonMigration/problems/views.py` (Google Drive upload block), `PolygonMigration/problems/google_drive.py`

**Description**:
Clicking "Upload Test Cases to Google Drive" twice uploads everything again unless the helper checks for existing files first. The user gets no feedback about what was skipped or reused.

**Impact**:

- Drive folder fills up with duplicate files.
- Users cannot tell whether the second run did anything.

**Suggested Fix**:
Before uploading, search the Drive folder for a file with the same name (`find_file_id`). Reuse the existing file ID when found, save the IDs on the matching `ProblemTestCase` rows, and report `21 test cases uploaded to Google Drive.` only after all uploads resolve.

---

## Code Issues

### [C1] Test cases matched by list position instead of a stable key

**Severity**: High

**Location**: `PolygonMigration/problems/views.py:521-554` (old code: `if idx < len(existing_test_cases)`)

**Description**:
Existing rows were updated by enumeration position (`idx`) while new rows were appended. When Polygon adds, removes, or reorders tests, positions no longer line up: the wrong rows get overwritten, stale rows are never deleted, and re-migration creates an inconsistent set.

**Impact**:

- Wrong test data attached to the wrong order numbers.
- Orphaned rows after the setter removes tests on Polygon.
- Duplicates accumulate across migrations.

**Suggested Fix**:
Delete all `ProblemTestCase` rows for the problem inside the existing transaction and recreate them from the fetched list with `order` starting at 1. Re-running then always yields exactly the fetched count.

---

### [C2] Hard dependency on Azure SDK and settings in the request path

**Severity**: Medium

**Location**: `PolygonMigration/problems/AzureTestcase.py`, `PolygonMigration/problems/polygon_api.py` (`migrate_to_azure_blob`), `PolygonMigration/PolygonMigration/settings.py` (`AZURE_*`)

**Description**:
The upload view read `AZURE_*` settings and built `BlobServiceClient` via `UsernamePasswordCredential` on every upload request. The Azure packages were required imports at module level, so the feature (and potentially startup) depended on Azure credentials even when Drive is the storage backend.

**Impact**:

- Upload breaks without Azure credentials.
- Unused heavy dependencies stay installed.

**Suggested Fix**:
Disable the Azure code (imports and upload/delete bodies commented out with a `# Azure upload disabled. Google Drive is used for storage now.` note), read only `GOOGLE_DRIVE_*` settings at upload time, and comment out the Azure lines in `requirement.txt`.

---

### [C3] Redis test-case cache can serve stale data

**Severity**: Low

**Location**: `PolygonMigration/problems/polygon_api.py` (`store_test_cases_in_redis`, `delete_problem_test_case_cache`)

**Description**:
Fetched test cases are cached in Redis for 30 minutes per Polygon ID, but the invalidation helper scans a different key pattern (database problem ID prefix `oj_dev_with_redis_storage_test_cases_*`), so it never deletes the keys that were actually written (`polygon_migration_test_cases_*`). A re-migrate within the TTL window can read stale tests.

**Impact**:

- Recently changed Polygon tests are missed until the cache expires.
- Hard to notice because the UI still shows the old count.

**Suggested Fix**:
Use one key pattern everywhere, or bypass the cache during migration (fetch fresh from Polygon on migrate actions, keep the cache for display only).

---

## Edge Case Analysis

### Q1

> A Polygon problem has 0 sample test cases but 15 regular test cases. What happens when you migrate this problem?

All 15 test cases are saved to `ProblemTestCase` with `is_sample=False`, and zero rows go to `SampleTestCase`. The message shows `15 test cases saved to database.` Upload still uploads all 15 files to Drive, since upload does not filter on `is_sample`.

---

### Q2

> A problem is migrated with 20 test cases. Later, the problem setter removes 8 test cases on Polygon (now 12 remain). The problem is re-migrated. What happens?

The migration deletes the 20 existing rows for the problem and creates 12 fresh rows, so the database ends with exactly 12 records and no duplicates. On Drive, files are matched by name, so the 12 current files are reused, but files for the 8 removed tests stay in the folder (known limitation, noted below).

---

### Q3

> Two different Polygon problems have the exact same title: "Two Sum". You migrate the first one successfully. Then you try to migrate the second one. What happens?

Lookup is by `polygon_id`, so the second problem creates a separate `Problem` row. But the slug is derived from the title (`slugify("Two Sum")` both times) and `slug` is unique, so saving the second problem raises an `IntegrityError` and the transaction rolls back. This is a known limitation: identical titles need slug disambiguation (for example, appending the Polygon ID).

---

### Q4

> When test cases are saved to the database via "Migrate Test Cases to DB", some data is intentionally discarded. What data is lost? Why might this cause problems?

The old code discarded three things: (1) input/output beyond 260 characters via `[:260]` truncation, (2) any test case with empty input or output via the `if input_data and output_data` guard, and (3) all test metadata except input, output, description, and `is_sample`. Truncated or dropped cases make judging incorrect and hide the loss behind a success message. The fix stores full input/output for every fetched case and warns when saved and fetched counts differ.

---

## Notes

- Storage backend is Google Drive (service account, folder shared with the service-account email). Old Azure code is commented out, not deleted, so it can be restored.
- Known limitation: re-upload reuses Drive files by name, but files for tests removed on Polygon are not cleaned from the Drive folder.
- Known limitation: identical problem titles collide on the unique `slug` field.
