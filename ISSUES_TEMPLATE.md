# Issues Analysis

> **Instructions**: Document the three highest-priority product issues and the three highest-priority code issues. Rank the issues within each category from highest to lowest priority.
> Replace the example entries with your actual findings and explain why each issue deserves its priority. Complete all four questions in the Edge Case Analysis section.
> Rename this file to `ISSUES.md` before submitting.

## Summary

| Type | Critical | High | Medium | Low | Total |
|------|----------|------|--------|-----|-------|
| Product Issues | 0 | 0 | 0 | 0 | 0 |
| Code Issues | 0 | 0 | 0 | 0 | 0 |

---

## Product Issues

> Product issues are user-facing problems: broken functionality, missing validation, poor UX, data integrity risks visible to users.

### [P1] Example: Missing Confirmation Dialog

**Severity**: Medium

**Location**: `problems/templates/problems/index.html` (migrate buttons)

**Description**:
When clicking "Migrate to Azure", the action executes immediately without asking for confirmation. This could lead to accidental data overwrites.

**Impact**:

- Users might accidentally overwrite test cases
- No way to cancel a mistaken click
- Potential data loss

**Suggested Fix**:
Add a JavaScript confirmation dialog before form submission for destructive actions.

---

### [P2] Test case migration error

**Severity**: High

**Location**: `Migrate Test Description to Database [Diango admin panel at -admin/problems/problemtestcase]'

**Description**:
[Polygon page shows me 21 tast case for 'Guess the number' but when we migrate test descripton to database it we see in the [Diango admin panel at -admin/problems/problemtestcase] only 8, 13 remaning tast case was not saved. But the actual product issue is the application dose not showes me any error message.]

**Impact**:
[User assume after migrate test description that all 21 test case were migrated. Also the missing 13 test case cause a signeficent dataloss]

**Suggested Fix**:
[I thing we need to approch idempotent approach like 'update-or-create()' that might be prevent deplicate in the re-migration. And one more thing we can do like after the migration we can comare the test case that was fateched and if all successfull then we should show clear feedback message]

---

### [P3] Incomplete Test case migration

**Severity**:  High

**Location**: '/admin/problems/problemtestcase/'

**Description**:
[The Polygon problem page reports 21 test cases for 'Guess the Number', but the Admin panelcontains 10 'ProblemTestCase' after migration. The 11 test cases are not saved, and the application does not clearly report that the migration was incomplete.]

**Impact**:
[Any later Google Drive upload based on these records may also omit the missing test cases. (As i am using google drive fo the storage)]

**Suggested Fix**:
[I thing we need to approch idempotent approach like 'update-or-create()' that might be prevent deplicate in the re-migration. And one more thing we can do like after the migration we can comare the test case that was fateched and if all successfull then we should show clear feedback message]

---

### [P4] Showing Zero tags

**Severity**:  High

**Location**: 'Create/Update problem in Database" button on / (PolygonMigration/problems/templates/problems/index.html, form id="migrate-db-form")'

**Description**:
[#69927 have 2 tags taht i included (java & spring) . After migration no tags returned, and the row ended with 0 tags.]

**Impact**:
[If user remigrate carelessly the tag drop wroking with a success message]

**Suggested Fix**:
[If less then 2 tags submitted reject with error message, and skipp the migration.]

---

<!-- Keep this section to three product issues, ranked from highest to lowest priority. -->

---

## Code Issues

> Code issues are technical problems: bugs, security vulnerabilities, performance problems, code quality concerns, architectural issues.

### [C1] Example: Unused Imports

**Severity**: Low

**Location**: `problems/views.py:6-8`

**Description**:

```python
from bs4 import BeautifulSoup  # Never used
from django.core.cache import cache  # Never used
```

These imports are declared but never used in the file.

**Impact**:

- Slightly increases memory usage
- Makes code harder to understand (suggests these modules are used when they're not)
- May cause confusion during code review

**Suggested Fix**:
Remove unused imports. Consider using a linter (flake8, ruff) to catch these automatically.

---

### [C2] Your Issue Title Here

**Severity**: High

**Location**: `PolygonMigration/problems/views.py`  - Google drive uploda and database migration flow

**Description**:
[The application migrate the test case to google drive and database also but the problem is if later the database operation failes the database role back and chnage but the google drive upload not chnages automatically]

**Impact**:
[Unused test case files remain in the google drive, and the google drive and database was contain different data, and it may conflict in re-running the migration and confuse that which file are currect in google drive]

**Suggested Fix**:
[Save the database record 1st, and upload the google cloude upload after that, and shows successful only ater google drive return valid id. And if we use gcp and auzure may be that conflict ends.]

---

### [C3] Same title can fail during migration

**Severity**: Low

**Location**: `PolygonMigration/problems/models.py` — `Problem.slug`

**Description**:
[When a problem is migrated, the application creates its slug from the problem title. The `Problem.slug` field is unique, but the migration logic does not add the Polygon problem ID or another unique value to the slug.]

**Impact**:
[A valid Polygon problem may not be migrated. And The user may receive only a generic migration error.]

**Suggested Fix**:
[Generate a unique slug using the title and Polygon problem ID, for example.]

---

<!-- Keep this section to three code issues, ranked from highest to lowest priority. -->

---

## Edge Case Analysis

### Q1

> A Polygon problem has 0 sample test cases but 15 regular test cases. What happens when you migrate this problem?

[Your answer here]

---

### Q2

> A problem is migrated with 20 test cases. Later, the problem setter removes 8 test cases on Polygon (now 12 remain). The problem is re-migrated. What happens?

[Your answer here]

---

### Q3

> Two different Polygon problems have the exact same title: "Two Sum". You migrate the first one successfully. Then you try to migrate the second one. What happens?

[Your answer here]

---

### Q4

> When test cases are saved to the database via "Migrate Test Cases to DB", some data is intentionally discarded. What data is lost? Why might this cause problems?

[Your answer here]

---

## Severity Guidelines

Use these definitions when assigning severity:

| Severity | Definition | Examples |
| ---------- | ------------ | ---------- |
| **Critical** | System broken, security vulnerability, data loss | SQL injection, authentication bypass, data corruption |
| **High** | Major functionality broken, significant data integrity risk | Feature doesn't work, orphaned records, race conditions |
| **Medium** | Feature partially broken, poor UX, code maintainability | Missing validation, confusing errors, code duplication |
| **Low** | Minor issues, cosmetic, best practice violations | Unused imports, inconsistent formatting, missing logs |

---

## Notes

[Add any additional observations, patterns you noticed, or architectural concerns that don't fit into specific issues above]
