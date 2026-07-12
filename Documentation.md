# Local Setup & Development Guide

Complete instructions for setting up the Trello REST API project from scratch on your local machine. Follow these steps in order — by the end you'll have a working development environment, a running server, and a passing test suite.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Setup](#2-project-setup)
3. [Virtual Environment](#3-virtual-environment)
4. [Installing Dependencies](#4-installing-dependencies)
5. [Environment Configuration](#5-environment-configuration)
6. [Database Setup](#6-database-setup)
7. [Running the Server](#7-running-the-server)
8. [Verifying the Setup](#8-verifying-the-setup)
9. [Running Tests](#9-running-tests)
10. [Project Structure](#10-project-structure)
11. [Development Workflow](#11-development-workflow)
12. [Switching to PostgreSQL](#12-switching-to-postgresql-optional)
13. [Common Issues & Troubleshooting](#13-common-issues--troubleshooting)
14. [Useful Commands Reference](#14-useful-commands-reference)

---

## 1. Prerequisites

Install these tools before starting. Versions listed are minimums; newer is fine.

| Tool | Version | Verification command |
|---|---|---|
| Python | 3.10 or higher | `python --version` |
| pip | 22.0 or higher | `pip --version` |
| Git | 2.30 or higher | `git --version` |
| A code editor | — | VS Code, PyCharm, or any editor of your choice |

### Installing Python

- **Windows:** Download from [python.org/downloads](https://www.python.org/downloads/). During installation, **check "Add Python to PATH"**.
- **macOS:** Use Homebrew: `brew install python@3.12`
- **Linux (Ubuntu/Debian):** `sudo apt update && sudo apt install python3 python3-pip python3-venv`

### Verifying installations

Open a terminal and run:

```bash
python --version       # Should print: Python 3.10+ (or python3 --version on Linux/macOS)
pip --version
git --version
```

If `python` doesn't work, try `python3`. On Windows, you may need to use `py` instead.

---

## 2. Project Setup & Quickstart

There are three ways to get this project running on your local machine:

### Method A: Docker Compose (Recommended)
This runs the entire stack (PostgreSQL, FastAPI Backend, and React Frontend) inside containerized environments. No need to install Python or Node.js on your host system.

1. Ensure **Docker Desktop** is open and running.
2. Build and start the containers in detached mode:
   ```bash
   docker compose up --build -d
   ```
3. Access the services:
   * **Frontend UI**: [http://localhost](http://localhost)
   * **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
4. To stop the containers:
   ```bash
   docker compose down
   ```

---

### Method B: Automated Dev Script (`start-dev.sh`)
This script automates setting up your Python virtual environment (using the most appropriate Python 3.11/3.10/3 version), installing both backend and frontend dependencies, creating config files, and launching both servers concurrently.

1. Make the script executable:
   ```bash
   chmod +x start-dev.sh
   ```
2. Run the script:
   ```bash
   ./start-dev.sh
   ```
3. Access the services:
   * **Frontend UI**: [http://localhost:5173](http://localhost:5173)
   * **Backend API**: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

### Method C: Manual Step-by-Step Setup
Use this method if you want full control over each component's initialization.

#### 1. Clone or copy the files
Change directory to the project folder:
```bash
cd trello-clone
```

After this step, your working directory contains:
```
trello-clone/
├── backend/
│   ├── app/
│   └── requirements.txt
├── frontend/
├── tests/
├── .env.example
├── docker-compose.yml
├── start-dev.sh
└── README.md
```

---

## 3. Virtual Environment

A virtual environment isolates your project's Python dependencies so they don't conflict with other projects.

### Create the virtual environment
Ensure you are using **Python 3.10+** (Python 3.11 is recommended):
```bash
# Linux / macOS
python3.11 -m venv venv

# Windows
python -m venv venv
```

### Activate the virtual environment
You must activate the `venv` every time you open a new terminal window:
```bash
# Linux / macOS
source venv/bin/activate

# Windows (Command Prompt)
venv\Scripts\activate.bat

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

When activated, your prompt will show `(venv)` at the beginning, like:
```
(venv) $
```

### Deactivate (when you're done)

```bash
deactivate
```

> **Note:** The `venv/` folder is already in `.gitignore` and should never be committed to git.

---

## 4. Installing Dependencies

With the virtual environment activated, install all required packages:

```bash
pip install -r backend/requirements.txt
```

This installs:

| Package | Purpose |
|---|---|
| `fastapi` | Web framework for building the API |
| `uvicorn[standard]` | ASGI server to run FastAPI |
| `sqlalchemy` | ORM for database interactions |
| `pydantic` | Data validation and settings management |
| `pydantic-settings` | Loads config from `.env` file |
| `python-jose[cryptography]` | JWT token creation and verification |
| `passlib[bcrypt]` | Secure password hashing |
| `python-multipart` | Form data parsing (for OAuth2 login) |

Verify the installation:

```bash
pip list
```

You should see all the packages from `backend/requirements.txt`.

### If you encounter installation errors

- **bcrypt error on Windows:** Run `pip install --upgrade pip setuptools wheel` first, then retry.
- **Permission denied:** Make sure your virtual environment is activated. Never use `sudo pip install`.
- **SSL errors:** Try `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt`.

---

## 5. Environment Configuration

The application reads sensitive settings (secret keys, database URLs) from a `.env` file. **This file is never committed to git** — each developer creates their own.

### Step 1: Copy the example file

```bash
# Linux / macOS
cp .env.example .env

# Windows
copy .env.example .env
```

### Step 2: Generate a secure secret key

The `SECRET_KEY` is used to sign JWT tokens. It must be a long, random string. Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

This prints something like:
```
H8x3Qz9pK_LmN2vR5tYbW7eA1cDfGhJkLmNoPqRsTuVw
```

### Step 3: Edit `.env`

Open `.env` in your editor and paste the generated key:

```env
SECRET_KEY=H8x3Qz9pK_LmN2vR5tYbW7eA1cDfGhJkLmNoPqRsTuVw

ACCESS_TOKEN_EXPIRE_MINUTES=60
ALGORITHM=HS256

DATABASE_URL=sqlite:///./trello.db
```

### What each setting does

| Setting | Description |
|---|---|
| `SECRET_KEY` | Signs JWT tokens. Keep secret. Never commit. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | How long a login token stays valid (default 60 min). |
| `ALGORITHM` | JWT signing algorithm. `HS256` is fine. |
| `DATABASE_URL` | Database connection string. SQLite by default. |

> **⚠️ Security warning:** Never commit `.env` to git. Never share your `SECRET_KEY`. The `.gitignore` already excludes it, but always double-check before pushing.

---

## 6. Database Setup

The project is configured for **PostgreSQL** by default, connecting via the connection string in your `.env` file:
```env
DATABASE_URL=postgresql://postgres:Binbud123%23@localhost:5433/trello_clone
```

### Option A: Using PostgreSQL (Default)
Ensure your PostgreSQL database server is running (either locally or through Docker using `docker compose up -d`). The application expects a database named `trello_clone` to be created.

### Option B: Using SQLite (Local Fallback)
If you do not want to run PostgreSQL, you can change the connection string in your `.env` to use SQLite. SQLite stores your entire database in a single local file:
```env
DATABASE_URL=sqlite:///./trello.db
```

### Automatic Table Creation
You do not need to run any manual SQL schema scripts. When the FastAPI server starts, SQLAlchemy automatically registers and creates the required database tables:
* `users` — user accounts (name, email, password hash)
* `boards` — boards details (name, description, owner)
* `board_members` — membership join table (which user has access to which board)
* `sections` — columns on a board (To Do, In Progress, etc.)
* `tickets` — task cards inside sections
* `invitations` — single-use invite tokens

### Resetting the Database
To reset your database during development:
* **For SQLite**: Simply delete the `trello.db` file:
  ```bash
  rm trello.db
  ```
* **For PostgreSQL**: Run the following commands in your database terminal:
  ```sql
  DROP DATABASE trello_clone;
  CREATE DATABASE trello_clone;
  ```


---

## 7. Running the Server

With everything set up, start the development server:

```bash
uvicorn app.main:app --reload
```

You should see output like:

```
INFO:     Will watch for changes in these directories: ['/path/to/trello-api']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Application startup complete.
```

### What the flags mean

- `app.main:app` — tells uvicorn to load the `app` object from `app/main.py`
- `--reload` — auto-restarts the server when you change any code (development only; remove for production)

### Custom host/port

```bash
# Listen on all network interfaces (e.g., for testing from a phone on the same WiFi)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Stopping the server

Press `Ctrl + C` in the terminal where uvicorn is running.

---

## 8. Verifying the Setup

### Step 1: Open the interactive docs

In your browser, visit:

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

You should see a beautifully formatted API documentation page with all endpoints listed.

### Step 2: Test the health endpoint

Visit http://127.0.0.1:8000/ in your browser. You should see:

```json
{ "status": "ok", "docs": "/docs" }
```

### Step 3: Try registering a user

In Swagger UI:

1. Expand `POST /auth/register`
2. Click **Try it out**
3. Paste this body:
   ```json
   {
     "email": "test@example.com",
     "password": "secret123",
     "name": "Test User"
   }
   ```
4. Click **Execute**

You should get a **201 Created** response with the new user data.

### Step 4: Login and authorize

1. Expand `POST /auth/login`, click **Try it out**
2. Enter `username: test@example.com` and `password: secret123`
3. Click **Execute** — copy the `access_token` from the response
4. At the top right of the page, click the **🔒 Authorize** button
5. Enter your username/password in the dialog (leave `client_id` and `client_secret` empty)
6. Click **Authorize**, then **Close**

Now you can call any protected endpoint (boards, sections, tickets) directly from Swagger UI.

### Step 5: Reset a forgotten password

In the React login screen, click **Forgot password?**, enter your email and a new password, then return to login.

You can also test it in Swagger UI with `POST /auth/reset-password`:

```json
{
  "email": "test@example.com",
  "password": "newsecret123"
}
```

---

## 9. Running Tests

The project includes an end-to-end test that exercises password reset and the full flow: register → login → create board → invite user → manage sections and tickets → check permissions.

### Install the test dependency

```bash
pip install httpx
```

(`httpx` is required by FastAPI's `TestClient`. It's not in `requirements.txt` because it's only needed for testing.)

### Run the tests

```bash
python tests/test_api.py
```

Expected output:

```
ALL TESTS PASSED
```

If any assertion fails, the script will raise an `AssertionError` showing which step broke.

### What the test covers

- User registration and login with JWT
- Board creation and access isolation between users
- Invitation token generation and acceptance
- Section CRUD with owner-only restrictions
- Ticket CRUD with creator-or-owner edit permissions
- Cross-board ticket move blocking
- Single-use invitation token enforcement

The test uses an **in-memory SQLite database**, so it doesn't touch your real `trello.db`.

---

## 10. Project Structure

```
trello-api/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entrypoint, router registration
│   ├── config.py                # Settings loaded from .env
│   ├── database.py              # SQLAlchemy engine, session, Base
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py          # Password hashing, JWT helpers
│   │   └── deps.py              # Auth + permission dependencies
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py            # ORM tables (User, Board, Section, Ticket, ...)
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic request/response shapes
│   │
│   └── routers/
│       ├── __init__.py
│       ├── auth.py              # /auth/register, /auth/login
│       ├── boards.py            # /boards CRUD + invitations
│       ├── sections.py          # /sections CRUD
│       ├── tickets.py           # /tickets CRUD
│       └── invitations.py       # /invitations/accept
│
├── tests/
│   ├── __init__.py
│   └── test_api.py              # End-to-end tests
│
├── requirements.txt             # Production dependencies
├── .env.example                 # Template for .env (committed)
├── .env                         # Your local config (NOT committed)
├── .gitignore                   # Files git should ignore
├── README.md                    # Project overview
├── SETUP.md                     # This file
└── trello.db                    # SQLite database (NOT committed, auto-generated)
```

### Layered architecture

```
HTTP request
    ↓
[Router]              ← endpoints in app/routers/
    ↓
[Dependencies]        ← auth + permission checks in app/core/deps.py
    ↓
[Schemas]             ← Pydantic validation in app/schemas/
    ↓
[Models]              ← SQLAlchemy ORM in app/models/
    ↓
[Database]            ← SQLite or Postgres
```

---

## 11. Development Workflow

### Day-to-day workflow

```bash
# 1. Open a terminal in the project folder
cd trello-clone

# 2. Activate the virtual environment
source venv/bin/activate            # Linux/macOS
venv\Scripts\activate               # Windows

# 3. Pull the latest code (if collaborating)
git pull

# 4. Install any new dependencies
pip install -r backend/requirements.txt

# 5. Start the server
uvicorn app.main:app --reload

# 6. (In another terminal) Run tests after making changes
python tests/test_api.py
```

### Adding a new feature

1. **Define the data shape** — add or modify Pydantic schemas in `app/schemas/schemas.py`.
2. **Update the database model** — modify SQLAlchemy classes in `app/models/models.py` if needed.
3. **Reset the database** — recreate the database (development only).
4. **Add the endpoint** — write the route handler in the appropriate router file.
5. **Test it** — try the endpoint in Swagger UI at `/docs`.
6. **Add a test case** — extend `tests/test_api.py` to cover the new behavior.
7. **Commit** — `git add . && git commit -m "Add X feature"`.

### Adding a new dependency

```bash
pip install <package-name>
pip freeze > backend/requirements.txt    # Update backend requirements
git add backend/requirements.txt
```

### Code style

- Use type hints everywhere (`def foo(x: int) -> str:`).
- Group imports: standard library → third-party → local (already enforced in this project).
- Keep route handlers focused; push business logic into helpers in `app/core/`.

---

## 12. Switching to PostgreSQL (optional)

PostgreSQL is the default database format in `.env` and Docker. If you are running locally without Docker and want to switch back to PostgreSQL:

### Step 1: Install PostgreSQL

- **Windows:** Download installer from [postgresql.org/download/windows](https://www.postgresql.org/download/windows/)
- **macOS:** `brew install postgresql@16 && brew services start postgresql@16`
- **Linux:** `sudo apt install postgresql postgresql-contrib`

### Step 2: Create a database and user

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE trello_clone;
CREATE USER trello_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE trello_clone TO trello_user;
\q
```

### Step 3: Install the Python driver

```bash
pip install psycopg2-binary
echo "psycopg2-binary==2.9.12" >> backend/requirements.txt
```


### Step 4: Update `.env`

```env
DATABASE_URL=postgresql+psycopg2://trello_user:your_password@localhost:5432/trello
```

### Step 5: Restart the server

```bash
uvicorn app.main:app --reload
```

The tables will be created automatically on startup.

### For production: use Alembic migrations

The auto-create-tables approach in `app/main.py` is fine for development but should be replaced with proper migrations in production:

```bash
pip install alembic
alembic init alembic
# Configure alembic.ini and env.py
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

---

## 13. Common Issues & Troubleshooting

### `ModuleNotFoundError: No module named 'fastapi'`

The virtual environment isn't activated, or dependencies aren't installed.

```bash
source venv/bin/activate              # Activate venv
pip install -r requirements.txt       # Reinstall
```

### `ModuleNotFoundError: No module named 'app'`

You're running uvicorn from the wrong directory. Make sure you're in the project root (`trello-api/`), not inside `app/`.

```bash
cd /path/to/trello-api
uvicorn app.main:app --reload
```

### `sqlalchemy.exc.OperationalError: no such column ...`

Your database schema is out of date because you changed a model. In development, just delete the DB file:

```bash
rm trello.db
# Restart the server — fresh tables will be created
```

In production, use Alembic to write a migration instead.

### `String should match pattern 'password'` (422 on login)

The Swagger UI's login form requires the `grant_type` field to be `password`. Either type `password` in that field, or use the **🔒 Authorize** button at the top of the page (which fills it in correctly).

### `401 Unauthorized` on protected endpoints

You haven't authorized Swagger UI yet. Click the **🔒 Authorize** button at the top right, log in, and click Close. After that, all protected requests will include the token.

### `bcrypt` warnings

If you see warnings like `(trapped) error reading bcrypt version`, they're harmless. To silence them:

```bash
pip install bcrypt==4.0.1
```

(Already pinned in `requirements.txt`.)

### Port 8000 already in use

Another process is using port 8000. Either stop it, or run uvicorn on a different port:

```bash
uvicorn app.main:app --reload --port 8001
```

### Tests fail with `ModuleNotFoundError: No module named 'httpx'`

```bash
pip install -r requirements.txt
```

### `--reload` not detecting changes

This rarely happens on some Windows configurations. Restart the server manually with `Ctrl+C` and re-run `uvicorn app.main:app --reload`.

---

## 14. Useful Commands Reference

### Server

```bash
uvicorn app.main:app --reload                          # Development server
uvicorn app.main:app --host 0.0.0.0 --port 8000        # Network-accessible
uvicorn app.main:app --workers 4                       # Production-style (no --reload)
```

### Frontend

```bash
cd frontend
npm install
npm run dev
npm run build
```

### Virtual environment

```bash
python -m venv venv                  # Create
source venv/bin/activate             # Activate (Linux/macOS)
venv\Scripts\activate                # Activate (Windows)
deactivate                           # Deactivate
```

### Dependencies

```bash
pip install -r requirements.txt      # Install all
pip install <package>                # Install one
pip freeze > requirements.txt        # Save current state
pip list                             # See installed packages
```

### Database

```bash
rm trello.db                         # Reset (Linux/macOS)
del trello.db                        # Reset (Windows)
```

### Tests

```bash
python tests/test_api.py             # Run all tests
```

### Git

```bash
git status                           # See what changed
git add .                            # Stage all changes
git commit -m "Description"          # Commit
git push                             # Push to remote
git pull                             # Pull latest
```

### Generate secret key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Check what port is in use (Linux/macOS)

```bash
lsof -i :8000
```

### Check what port is in use (Windows)

```bash
netstat -ano | findstr :8000
```

---

## Need help?

- **API reference:** See `README.md` for the complete endpoint list.
- **Interactive docs:** Run the server and visit http://127.0.0.1:8000/docs
- **FastAPI docs:** https://fastapi.tiangolo.com
- **SQLAlchemy docs:** https://docs.sqlalchemy.org
- **Pydantic docs:** https://docs.pydantic.dev

---

**Last updated:** May 2026
**Project version:** 1.0.0
