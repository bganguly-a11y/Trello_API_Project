"""SQLAlchemy engine, session factory, and declarative base."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# SQLite needs this special arg; for Postgres/MySQL, drop connect_args.
connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _migrate_sqlite_users_name_column() -> None:
    """Upgrade old dev SQLite DBs from first/last names to a single name."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        user_columns = conn.execute(text("PRAGMA table_info(users)")).mappings().all()
        column_names = {column["name"] for column in user_columns}
        if not column_names:
            return
        if "name" in column_names and "first_name" not in column_names and "last_name" not in column_names:
            return

        if "name" in column_names:
            name_expression = (
                "COALESCE(NULLIF(name, ''), "
                "NULLIF(TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')), ''), "
                "email)"
            )
        elif {"first_name", "last_name"}.issubset(column_names):
            name_expression = (
                "COALESCE(NULLIF(TRIM(COALESCE(first_name, '') || ' ' || "
                "COALESCE(last_name, '')), ''), email)"
            )
        else:
            name_expression = "email"

        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("DROP TABLE IF EXISTS users_new"))
        conn.execute(text("""
            CREATE TABLE users_new (
                id INTEGER NOT NULL,
                email VARCHAR NOT NULL,
                hashed_password VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                created_at DATETIME,
                PRIMARY KEY (id)
            )
        """))
        conn.execute(text(f"""
            INSERT INTO users_new (id, email, hashed_password, name, created_at)
            SELECT id, email, hashed_password, {name_expression}, created_at
            FROM users
        """))
        conn.execute(text("DROP TABLE users"))
        conn.execute(text("ALTER TABLE users_new RENAME TO users"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
        conn.execute(text("PRAGMA foreign_keys=ON"))


def init_db() -> None:
    """Create database tables and apply lightweight SQLite dev migrations."""
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_users_name_column()


def get_db():
    """FastAPI dependency that yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
