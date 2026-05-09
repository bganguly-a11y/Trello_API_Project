# Trello Clone REST API

A FastAPI implementation of a Trello-style project management API. Built as Part 1 of a capstone project.

## Features

- User registration and JWT-based login
- Boards owned by users (with description)
- Board membership via single-use invitation tokens
- CRUD for sections (parent board immutable)
- CRUD for tickets (movable between sections on the same board)
- Permission model: board owners can edit anything; invited members can only edit tickets they created
- Auto-generated interactive docs at `/docs` (Swagger UI) and `/redoc` (ReDoc)
- Full end-to-end test suite

## Tech stack

- **FastAPI** — web framework
- **SQLAlchemy 2.0** — ORM
- **Pydantic v2** — request/response validation
- **python-jose** — JWT signing/verification
- **passlib + bcrypt** — password hashing
- **SQLite** — default DB (swap `DATABASE_URL` for Postgres/MySQL)
- **Uvicorn** — ASGI server

## Project structure

```
trello-api/
├── app/
│   ├── main.py              # FastAPI app, router registration, CORS
│   ├── config.py            # Settings loaded from .env
│   ├── database.py          # SQLAlchemy engine, session, Base
│   ├── core/
│   │   ├── security.py      # Password hashing, JWT helpers
│   │   └── deps.py          # Auth + permission dependencies
│   ├── models/
│   │   └── models.py        # ORM models (User, Board, Section, Ticket, ...)
│   ├── schemas/
│   │   └── schemas.py       # Pydantic schemas
│   └── routers/
│       ├── auth.py
│       ├── boards.py
│       ├── sections.py
│       ├── tickets.py
│       └── invitations.py
├── tests/
│   └── test_api.py          # End-to-end tests
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Setup (from scratch)

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd trello-api
```

### 2. Create a virtual environment

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` from the example

```bash
cp .env.example .env
```

Generate a secure secret key and paste it into `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

The server starts on `http://127.0.0.1:8000`. Database tables are created automatically on first run (SQLite file `trello.db`).

### 6. Open the interactive docs

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## API reference

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/auth/register` | Create a new account | No |
| POST | `/auth/login` | Get a JWT access token | No |
| POST | `/boards/` | Create a board | Yes |
| GET | `/boards/` | List boards I'm a member of | Yes |
| GET | `/boards/{id}` | Detailed board view | Member |
| PATCH | `/boards/{id}` | Update board name/description | Owner |
| DELETE | `/boards/{id}` | Delete a board | Owner |
| POST | `/boards/{id}/invitations` | Generate invite token | Owner |
| POST | `/invitations/accept` | Redeem a token to join a board | Yes |
| POST | `/boards/{id}/sections` | Create a section | Owner |
| GET | `/boards/{id}/sections` | List sections | Member |
| GET | `/sections/{id}` | Get one section | Member |
| PATCH | `/sections/{id}` | Update a section | Owner |
| DELETE | `/sections/{id}` | Delete a section | Owner |
| POST | `/sections/{id}/tickets` | Create a ticket | Member |
| GET | `/sections/{id}/tickets` | List tickets | Member |
| GET | `/tickets/{id}` | Get one ticket | Member |
| PATCH | `/tickets/{id}` | Update a ticket | Owner or creator |
| DELETE | `/tickets/{id}` | Delete a ticket | Owner or creator |

## Quick example with curl

```bash
# 1. Register
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"secret123","first_name":"Alice","last_name":"A"}'

# 2. Login (form-encoded, OAuth2 standard)
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -d "username=alice@example.com&password=secret123" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 3. Create a board
curl -X POST http://127.0.0.1:8000/boards/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Capstone","description":"Trello clone"}'

# 4. List my boards
curl http://127.0.0.1:8000/boards/ -H "Authorization: Bearer $TOKEN"
```

## Running tests

```bash
pip install httpx
python tests/test_api.py
```

The test runs an in-memory SQLite database and exercises:
- Registration, login, JWT auth
- Board creation and access isolation between users
- Section CRUD
- Invitation creation, acceptance, and reuse blocking
- Ticket creation, move-within-board, cross-board move blocking
- Permission checks (owner vs member, creator-only ticket editing)

Expected output: `ALL TESTS PASSED`.

## Permission rules in plain English

- A **board owner** can do anything on their board: edit board details, create/edit/delete sections, edit any ticket, generate invitations.
- A **board member** (joined via invitation) can: view the board, create new tickets, and edit/delete tickets they created themselves. They cannot modify sections or other people's tickets.
- A **non-member** has no access at all (403).
- A **ticket** can be moved between sections, but only within the same board.
- An **invitation token** is single-use; reusing it returns 400.

## Switching to PostgreSQL

Update `DATABASE_URL` in `.env`:

```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/trello
```

Add `psycopg2-binary` to `requirements.txt` and reinstall.

For real production use, replace the auto `Base.metadata.create_all()` in `app/main.py` with **Alembic** migrations.

## Notes for grading

- No DB file or `.env` is committed — both are listed in `.gitignore`.
- Schema is created automatically on first run.
- All endpoints validate inputs via Pydantic and return clean 4xx errors with detail messages.
- Auth uses bearer JWT tokens; the Swagger UI "Authorize" button works with the `/auth/login` endpoint.
