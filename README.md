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
- React frontend for managing boards, sections, tickets, and invitations
- Full end-to-end test suite

## Tech stack

- **FastAPI** — web framework
- **SQLAlchemy 2.0** — ORM
- **Pydantic v2** — request/response validation
- **python-jose** — JWT signing/verification
- **passlib + bcrypt** — password hashing
- **PostgreSQL 18** — relational database (via `psycopg2-binary`)
- **Uvicorn** — ASGI server
- **React + Vite** — frontend application

## Project structure

```
trello-clone/
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
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # React Trello UI
│   │   └── styles.css       # Frontend styling
│   ├── package.json
│   └── vite.config.js       # Dev proxy to FastAPI
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Setup and Execution

There are three ways to set up and run this application locally:

---

### Option A: Running with Docker Compose (Recommended)
This runs the entire stack (Postgres Database, FastAPI Backend, and React Frontend via Nginx) inside containerized environments without installing Python or Node.js locally.

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

### Option B: Running with Automated Dev Script (`start-dev.sh`)
This automates the configuration, packages installation, and runs both servers concurrently.

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

### Option C: Manual Setup (From Scratch)

#### 1. Clone the repo
```bash
git clone <your-repo-url>
cd trello-clone
```

#### 2. Create and Activate a Virtual Environment
```bash
# Linux / macOS (Python 3.10+)
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

#### 4. Set up PostgreSQL
Create the database:
```bash
psql -U <your-pg-user> -d postgres -c "CREATE DATABASE trello_clone;"
```

#### 5. Configure Environment Variables
Create a `.env` file from the template:
```bash
cp .env.example .env
```
Update the settings in your `.env`:
```env
# Generate a strong key with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=<your-secret-key>
DATABASE_URL=postgresql://<user>:<password>@localhost:<port>/trello_clone
```

#### 6. Run the FastAPI backend
```bash
cd backend
uvicorn app.main:app --reload
```
The database tables are created automatically on the first run.

#### 7. Run the React frontend
Open a new terminal window:
```bash
cd frontend
npm install
npm run dev
```

---

### Open the interactive docs


- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## API reference

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/auth/register` | Create a new account | No |
| POST | `/auth/login` | Get a JWT access token | No |
| POST | `/auth/reset-password` | Reset password by email | No |
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


## Running tests

```bash
cd backend
python -m pytest tests/ -v
```

Tests use an **in-memory SQLite database** (independent of PostgreSQL) and exercise:
- Registration, login, password reset, JWT auth
- Board creation and access isolation between users
- Section CRUD
- Invitation creation, acceptance, and reuse blocking
- Ticket creation, move-within-board, cross-board move blocking
- Permission checks (owner vs member, creator-only ticket editing)

## Permission rules in plain English

- A **board owner** can do anything on their board: edit board details, create/edit/delete sections, edit any ticket, generate invitations.
- A **board member** (joined via invitation) can: view the board, create new tickets, and edit/delete tickets they created themselves. They cannot modify sections or other people's tickets.
- A **non-member** has no access at all (403).
- A **ticket** can be moved between sections, but only within the same board.
- An **invitation token** is single-use; reusing it returns 400.

## Database

The application uses **PostgreSQL** as its primary database. The connection is configured via the `DATABASE_URL` environment variable in `.env`.

### PostgreSQL Tables

| Table | Purpose |
|-------|--------|
| `users` | User accounts (email, password hash, name) |
| `boards` | Board details (name, description, owner) |
| `sections` | Sections within boards |
| `tickets` | Tickets within sections (creator, assignee) |
| `board_members` | User ↔ Board membership join table |
| `invitations` | One-time invite tokens for board access |

For production use, replace the auto `Base.metadata.create_all()` in `app/main.py` with **Alembic** migrations.

## Notes for grading

- No `.env` file is committed — it is listed in `.gitignore`.
- Schema is created automatically on first run.
- User registration accepts a single `name` field with `email` and `password`.
- All endpoints validate inputs via Pydantic and return clean 4xx errors with detail messages.
- Auth uses bearer JWT tokens; the Swagger UI "Authorize" button works with the `/auth/login` endpoint.
