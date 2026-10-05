# Polygon Migration Tool — Full-Stack Engineer Assessment

## Overview

At AlgoUniversity, a full-time full-stack engineer should be able to work with an unfamiliar codebase, get it running, and explain how it works and where it needs improvement.

[Polygon](https://polygon.codeforces.com/) is a platform provided by Codeforces for creating and managing competitive programming problems, including their statements, test cases, and reference solutions.

You are given the codebase for the **Polygon Migration Tool**, a web application that copies problems from Polygon into your own database and uploads their test-case files to cloud storage.

Your task is to set up the application, demonstrate a complete migration, document the user flows, and identify the most important product and code issues. Think of this as taking over a tool that your team needs to understand and maintain.

**Estimated effort:** 5.5–8 hours across all three parts; allow additional time if you are new to the setup.
**Deadline:** Within 24 hours of receiving the assignment.
**Submit to:** [nalin@algouniversity.com](mailto:nalin@algouniversity.com)
**Deliverables:** Your code repository, a 5–10 minute demo video, `DOCUMENTATION.md`, and `ISSUES.md`.
**Evaluation:** All three parts carry equal weight.

## Getting Started

- Download the [starter codebase](https://drive.google.com/file/d/1vf2zAJyKqotyNrYcQVe0qnTNc5Lu5RRb/view?usp=sharing).
- Create an account on [Polygon](https://polygon.codeforces.com/) and email your username to [nalin@algouniversity.com](mailto:nalin@algouniversity.com) immediately after signing up.
- Use the [Polygon tutorial](https://quangloc99.github.io/posts/polygon-codeforces-tutorial/#the-checker) and [Polygon API documentation](https://docs.google.com/document/d/1mb6CDWpbLQsi7F5UjAdwXdbCpyvSgWSXTJVHl52zZUQ) as references wherever needed.

## Part 1: Setup & Working Demo

**Estimated effort: 2–3 hours**

Get the application working and show that a problem and its test cases can be migrated successfully.

### 1.1 Environment Setup

- [ ]  Extract the starter codebase and install its dependencies.
- [ ]  Set up PostgreSQL and Redis. PostgreSQL is required; do not substitute SQLite.
- [ ]  Create your own simple problem on Polygon with a clear statement, input/output format, a reference solution, at least **3 sample test cases**, and at least **10 regular test cases**.
- [ ]  Generate your Polygon API key and secret.
- [ ]  Configure your `.env` file using `.env.example`.
- [ ]  Run database migrations, create a superuser, and start the application.

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 1.2 Cloud Storage Integration

The starter code uses **Azure Blob Storage** to store test-case files. You may use Azure or another cloud storage provider you can access, such as AWS S3, Google Cloud Storage, Cloudflare R2, or Google Drive.

Make any changes needed to support your chosen provider. If you use Azure, you do not need to add a second provider, but your implementation must still meet these requirements:

- Preserve the file structure shown below.
- Read storage configuration and credentials from environment variables.
- Keep provider-specific logic behind a clear storage interface so the provider can be changed without rewriting the migration flow.

```
test_cases/{problem_id}/{test_number}      # Input file
test_cases/{problem_id}/{test_number}.a    # Output file
```

### 1.3 Recorded Walkthrough

Record a **5–10 minute video** using [Loom](https://www.loom.com/) or another screen-recording tool. Keep your camera on, your face visible, and your voice clearly audible without background noise.

Explain the walkthrough as if you were helping a teammate set up and use the application for the first time. Show:

1. **Setup and startup:** Briefly explain your setup, then show the running server and login page.
2. **Login:** Sign in with your superuser account.
3. **Fetch a problem:** Enter your Polygon problem ID and fetch the data.
4. **Review the data:** Show the problem statement, test-case previews, and reference solution.
5. **Migrate the problem:** Select a difficulty, add at least two tags, and click “Migrate to Database.”
6. **Migrate test cases:** Click “Migrate Test Cases to DB” and show the result.
7. **Upload to storage:** Run the cloud storage migration and show the result.
8. **Verify the upload:** Open your storage console or file listing, show the expected folder structure, and open an input/output pair to confirm its contents.

Explain what each step accomplishes, including the difference between saving data in the database and uploading files to storage. Keep credentials hidden in the recording.

**Deliverable:** Your working code and demo video.

## Part 2: Functionality Documentation

**Estimated effort: 1.5–2 hours**

Write `DOCUMENTATION.md` in the repository root. Imagine that a new engineer is joining your team: they should be able to use this document to follow a user action from the browser through the backend to the database or external service.

### 2.1 User Flows

Document these five flows:

- User login.
- Fetching a problem from Polygon.
- Migrating a problem to the database.
- Migrating test cases to the database.
- Uploading test cases to cloud storage.

For each flow, explain:

1. What the user clicks or submits.
2. What data the frontend sends to the backend.
3. What the backend does, in order.
4. Which external APIs are called, if any.
5. What is read or written in the database or storage.
6. What the user sees when the action completes.

Describe the actual implementation. Use relevant file, function, and endpoint names to help the reader find the code.

### 2.2 External Integrations

Explain which **Polygon API endpoints** the application uses and how requests are authenticated. For your **cloud storage integration**, explain how files are named and organized.

**Deliverable:** `DOCUMENTATION.md`.

## Part 3: Issue Analysis & Edge Cases

**Estimated effort: 2–3 hours**

Write `ISSUES.md` in the repository root using the provided issue template. Show that you can recognize important problems and explain what your team should prioritize.

### 3.1 Issue Identification

Identify **three product issues** and **three code issues**. Rank the issues within each category from highest to lowest priority.

- **Product issues** affect the person using the tool: broken functionality, missing validation or feedback, confusing workflows, or incorrect data.
- **Code issues** affect the implementation: bugs, security weaknesses, performance problems, or structural choices that make the system unreliable or difficult to maintain.

For each issue, explain the problem, its impact, and why you assigned that priority. Support your findings with relevant code references or observed behavior.

Write as if you were preparing work for your engineering team. Focus on issues that matter to users or to the team's ability to develop the product.

You are expected to analyze these issues; you do not need to fix all six as part of this assignment.

### 3.2 Edge Case Analysis

Add an **Edge Case Analysis** section to `ISSUES.md` and answer all four questions:

1. A Polygon problem has **0 sample test cases** and **15 regular test cases**. What happens when you migrate it?
2. A problem is migrated with **20 test cases**. The problem setter later removes eight on Polygon, leaving **12**. What happens when you migrate the same problem again?
3. Two different Polygon problems have the same title, **“Two Sum.”** You migrate the first successfully, then try to migrate the second. What happens?
4. When you click **“Migrate Test Cases to DB,”** some data is intentionally discarded. What data is lost, and why could that cause problems?

Use code reading, testing, or both. Explain what happens and why, identify the migration action you are discussing, and distinguish behavior you tested from conclusions based on reading the code.

**Deliverable:** `ISSUES.md`, including the six prioritized issues and four edge-case answers.

## Use of AI

You may use an AI assistant to explore and understand the codebase. However, you must write **`DOCUMENTATION.md` and `ISSUES.md` yourself, in your own words**, including the edge-case answers. Submissions containing AI-generated documentation or issue analysis will not be considered.

## Submission

Before submitting, check that you have:

- [ ]  A private repository containing the working code. Give [nalinabrol](https://github.com/nalinabrol/) collaborator access.
- [ ]  Any storage changes committed, with a pull request description explaining what changed and how to configure and verify it.
- [ ]  A 5–10 minute video link accessible to the reviewer.
- [ ]  `DOCUMENTATION.md` in the repository root.
- [ ]  `ISSUES.md` in the repository root, including the edge-case answers.
- [ ]  Your Polygon username, actual time spent, and any blockers or assumptions.

Exclude `.env` and secrets from the repository. Keep `.env.example` suitable for another engineer to configure the application.

Email [**nalin@algouniversity.com**](mailto:nalin@algouniversity.com) with the subject **[Polygon Assessment] — Your Name**:

```
Repository URL:
Video URL:
Polygon Username:
Polygon Problem ID:
Storage Provider:
Time Spent:

Notes (optional):
Blockers, assumptions, or what you would do differently with more time.
```

## Evaluation

All three parts carry equal weight:

- **Setup and demo:** A working migration flow, appropriate storage integration, verification of uploaded files, and a clear walkthrough.
- **Functionality documentation:** An accurate explanation of how user actions connect the frontend, backend, database, and external services.
- **Issue analysis:** Useful findings, sound prioritization, and edge-case answers supported by reasoning and evidence.

If setup or access blocks you, email us with the error and what you have tried, and include the blocker in your submission.
