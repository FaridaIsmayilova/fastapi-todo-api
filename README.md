# fastapi-todo-api

A clean, interview-ready **ToDo REST API** built with **FastAPI**, **SQLAlchemy 2.0**, **Pydantic v2**, and **PostgreSQL**.
Includes JWT auth (OAuth2 password flow), owner-only updates/deletes, status filter, **search (`q`)**, **safe sorting (`sort_by`, `sort_dir`)**, and **pagination** with `total_pages`. A full **pytest** suite is included.

## Table of Contents

* [Features](#features)
* [Tech Stack](#tech-stack)
* [Project Structure](#project-structure)
* [Getting Started](#getting-started)

  * [1) Clone & Create venv](#1-clone--create-venv)
  * [2) Install Dependencies](#2-install-dependencies)
  * [3) Configure Environment](#3-configure-environment)
  * [4) Run the API](#4-run-the-api)
  * [5) Open Swagger](#5-open-swagger)
* [Database Setup (PostgreSQL)](#database-setup-postgresql)
* [Authentication](#authentication)
* [API Overview](#api-overview)

  * [Auth Endpoints](#auth-endpoints)
  * [Task Endpoints](#task-endpoints)
  * [List Query Parameters](#list-query-parameters)
  * [Schemas](#schemas)
* [Examples (curl)](#examples-curl)
* [Testing](#testing)
* [.env Example](#env-example)
* [Common Issues](#common-issues)
* [License](#license)



## Features

* **Users**: `first_name` (required), `last_name` (optional), `username` (unique), `password` (**min 6**, stored **bcrypt-hashed**)
* **Tasks**: `title` (required), `description` (optional), `status` ∈ `{ New, In Progress, Completed }`, `user_id` (FK, **cascade delete**)
* **CRUD**: list all tasks (auth-only), list current user’s tasks, get by id, create, **update (owner-only)**, **delete (owner-only)**
* **Extras**: mark **Completed**, filter by **status**, **search `q`** (title/description), **safe sorting**, **pagination** (`total_pages`)
* **Auth**: JWT with **OAuth2 password flow** (use Swagger **Authorize**)
* **Tests**: pytest suite (auth + tasks) using **SQLite (in-memory)**



## Tech Stack

* FastAPI, Uvicorn
* SQLAlchemy 2.0 (ORM)
* Pydantic v2, pydantic-settings
* passlib\[bcrypt], python-jose\[cryptography], python-multipart
* PostgreSQL (runtime) via psycopg2-binary
* Pytest



## Project Structure

```
app/
  __init__.py
  main.py
  database.py
  models.py
  schemas.py
  security.py
  config.py
  routes/
    __init__.py
    auth.py
    tasks.py
tests/
  conftest.py
  test_auth.py
  test_tasks.py
README.md
requirements.txt
.env
```



## Getting Started

### 1) Clone & Create venv

```powershell
git clone https://github.com/<your-user>/fastapi-todo-api.git
cd fastapi-todo-api

python -m venv .venv
.\.venv\Scripts\activate
```

### 2) Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3) Configure Environment

Create a `.env` file (recommended) or set env vars in your shell.

```
POSTGRES_USER=todo_user
POSTGRES_PASSWORD=StrongPassword123!
POSTGRES_DB=todo
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

SECRET_KEY=Q1GkZvJhN8FJ+KXKwZ4vJK8B7Vq2TfVnmcj0ZcqC0jg=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### 4) Run the API

```powershell
python -m uvicorn app.main:app --reload
```

### 5) Open Swagger

Go to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
Health check: `GET /health` → `{"status":"ok"}`
Click **Authorize** → in **Bearer (OAuth2, password)** enter username/password (leave client fields blank).



## Database Setup (PostgreSQL)

If you don’t already have DB + user:

```sql
CREATE USER todo_user WITH PASSWORD 'StrongPassword123!';
CREATE DATABASE todo OWNER todo_user;
GRANT ALL PRIVILEGES ON DATABASE todo TO todo_user;
```

Tables are created automatically at app startup.



## Authentication

* `POST /auth/register` — password ≥ 6; server stores a bcrypt hash
* `POST /auth/login` — OAuth2 password flow (`application/x-www-form-urlencoded`) → `{"access_token":"<JWT>","token_type":"bearer"}`
* `GET /auth/me` — current user (requires Bearer token)



## API Overview

### Auth Endpoints

| Method | Path           | Description                             |
| -----: | -------------- | --------------------------------------- |
|   POST | /auth/register | Create a user (min 6 char password)     |
|   POST | /auth/login    | OAuth2 password flow → JWT access token |
|    GET | /auth/me       | Current user (requires Bearer token)    |

### Task Endpoints (all require Bearer token)

| Method | Path                 | Description                                  |
| -----: | -------------------- | -------------------------------------------- |
|    GET | /tasks               | List all tasks (filter/search/sort/paginate) |
|    GET | /tasks/mine          | List only current user’s tasks               |
|    GET | /tasks/{id}          | Get task by id                               |
|   POST | /tasks               | Create a task                                |
|  PATCH | /tasks/{id}          | Update a task (owner-only)                   |
|  PATCH | /tasks/{id}/complete | Mark as Completed (owner-only)               |
| DELETE | /tasks/{id}          | Delete a task (owner-only)                   |

### List Query Parameters

* `status`: `"New" | "In Progress" | "Completed"`
* `q`: case-insensitive search in **title** or **description**
* `sort_by`: `id | title | status | user_id`
* `sort_dir`: `asc | desc`
* `page`: integer ≥ 1
* `limit`: 1..100

**Paginated response**

```json
{
  "items": [],
  "total": 42,
  "page": 1,
  "limit": 10,
  "total_pages": 5
}
```

### Schemas

**TaskOut**

```json
{ "id": 7, "title": "Buy milk", "description": "2L", "status": "New", "user_id": 1 }
```

**UserOut**

```json
{ "id": 1, "first_name": "Farida", "last_name": "Jahidzade", "username": "farida" }
```



## Examples (curl)

```bash
# Register
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Farida","last_name":"Jahidzade","username":"farida","password":"StrongPass1"}'

# Login (OAuth2 password flow: form data)
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=farida&password=StrongPass1" | python - <<'PY'
import sys, json; print(json.load(sys.stdin)['access_token'])
PY
)

# Create a task
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Buy milk","description":"2L","status":"New"}'

# List my tasks with search + sort + pagination
curl "http://127.0.0.1:8000/tasks/mine?q=milk&sort_by=title&sort_dir=asc&page=1&limit=5" \
  -H "Authorization: Bearer $TOKEN"
```



## Testing

Tests run against an **in-memory SQLite** DB and **do not** touch Postgres.

```powershell
pytest -q
```



## .env Example

```
POSTGRES_USER=todo_user
POSTGRES_PASSWORD=StrongPassword123!
POSTGRES_DB=todo
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

SECRET_KEY=REPLACE_ME_WITH_A_RANDOM_32B_VALUE
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```



## Common Issues

* **401 Unauthorized** — Not logged in or token expired. Click **Authorize** in Swagger and sign in again.
* **401 after restart** — `SECRET_KEY` changed; log in again (or keep a stable key in `.env`).
* **Cannot connect to Postgres** — Ensure the service is running and `POSTGRES_HOST/PORT` are correct.
* **Login 422** — `python-multipart` is required for OAuth2 form login.


## License

MIT

