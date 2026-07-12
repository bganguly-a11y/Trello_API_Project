"""End-to-end tests using FastAPI TestClient + an in-memory SQLite DB."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Use a fresh in-memory DB for the test run.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(email: str, password: str = "secret123",
                        name: str = "Test User") -> str:
    r = client.post("/auth/register", json={
        "email": email, "password": password, "name": name,
    })
    assert r.status_code == 201, r.text
    # Login uses OAuth2PasswordRequestForm — submit form-encoded
    r = client.post("/auth/login",
                     data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_password_reset():
    email = "reset@example.com"
    old_password = "secret123"
    new_password = "newsecret123"

    r = client.post("/auth/register", json={
        "email": email, "password": old_password, "name": "Reset User",
    })
    assert r.status_code == 201, r.text

    r = client.post("/auth/reset-password", json={
        "email": email, "password": new_password,
    })
    assert r.status_code == 200, r.text
    assert r.json()["email"] == email

    r = client.post("/auth/login",
                    data={"username": email, "password": old_password})
    assert r.status_code == 401

    r = client.post("/auth/login",
                    data={"username": email, "password": new_password})
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


def test_full_flow():
    # 1. Register two users: Alice (owner) and Bob (invited)
    alice_token = register_and_login("alice@example.com", name="Alice")
    bob_token = register_and_login("bob@example.com", name="Bob")

    # 2. Alice creates a board
    r = client.post("/boards/",
                     json={"name": "Capstone", "description": "Trello clone"},
                     headers=auth_headers(alice_token))
    assert r.status_code == 201, r.text
    board = r.json()
    board_id = board["id"]

    # 3. Alice lists her boards — sees the new one
    r = client.get("/boards/", headers=auth_headers(alice_token))
    assert r.status_code == 200
    assert any(b["id"] == board_id for b in r.json())

    # 4. Bob does NOT see the board
    r = client.get("/boards/", headers=auth_headers(bob_token))
    assert r.status_code == 200
    assert all(b["id"] != board_id for b in r.json())

    # 5. Bob can't view the board's detail (403)
    r = client.get(f"/boards/{board_id}", headers=auth_headers(bob_token))
    assert r.status_code == 403

    # 6. Alice creates two sections
    r = client.post(f"/boards/{board_id}/sections",
                     json={"name": "To Do"},
                     headers=auth_headers(alice_token))
    assert r.status_code == 201
    section_todo_id = r.json()["id"]

    r = client.post(f"/boards/{board_id}/sections",
                     json={"name": "Done"},
                     headers=auth_headers(alice_token))
    section_done_id = r.json()["id"]

    # 7. Alice creates an invitation, Bob accepts
    r = client.post(f"/boards/{board_id}/invitations",
                     headers=auth_headers(alice_token))
    assert r.status_code == 201
    token = r.json()["token"]

    r = client.post("/invitations/accept",
                     json={"token": token},
                     headers=auth_headers(bob_token))
    assert r.status_code == 200

    # 8. Bob now sees the board
    r = client.get(f"/boards/{board_id}", headers=auth_headers(bob_token))
    assert r.status_code == 200
    detail = r.json()
    assert len(detail["members"]) == 2
    # Bob is not the owner, so he doesn't see invitations
    assert detail["invitations"] == []

    # 9. Bob creates a ticket in 'To Do'
    r = client.post(f"/sections/{section_todo_id}/tickets",
                     json={"name": "Write README", "description": "..."},
                     headers=auth_headers(bob_token))
    assert r.status_code == 201, r.text
    bob_ticket_id = r.json()["id"]

    # 10. Alice creates a ticket too
    r = client.post(f"/sections/{section_todo_id}/tickets",
                     json={"name": "Design schema"},
                     headers=auth_headers(alice_token))
    alice_ticket_id = r.json()["id"]

    # 11. Bob can edit his own ticket
    r = client.patch(f"/tickets/{bob_ticket_id}",
                      json={"name": "Write a great README"},
                      headers=auth_headers(bob_token))
    assert r.status_code == 200
    assert r.json()["name"] == "Write a great README"

    # 12. Bob CANNOT edit Alice's ticket
    r = client.patch(f"/tickets/{alice_ticket_id}",
                      json={"name": "hacked"},
                      headers=auth_headers(bob_token))
    assert r.status_code == 403

    # 13. Alice (owner) CAN edit Bob's ticket
    r = client.patch(f"/tickets/{bob_ticket_id}",
                      json={"description": "edited by owner"},
                      headers=auth_headers(alice_token))
    assert r.status_code == 200

    # 14. Bob moves his ticket from To Do -> Done (same board, allowed)
    r = client.patch(f"/tickets/{bob_ticket_id}",
                      json={"section_id": section_done_id},
                      headers=auth_headers(bob_token))
    assert r.status_code == 200
    assert r.json()["section_id"] == section_done_id

    # 15. Create a separate board owned by Bob and confirm cross-board
    #     ticket move is blocked
    r = client.post("/boards/",
                     json={"name": "Bob's other board"},
                     headers=auth_headers(bob_token))
    other_board_id = r.json()["id"]
    r = client.post(f"/boards/{other_board_id}/sections",
                     json={"name": "Inbox"},
                     headers=auth_headers(bob_token))
    other_section_id = r.json()["id"]

    r = client.patch(f"/tickets/{bob_ticket_id}",
                      json={"section_id": other_section_id},
                      headers=auth_headers(bob_token))
    assert r.status_code == 400  # different board not allowed

    # 16. Bob cannot create sections on Alice's board (only owner can)
    r = client.post(f"/boards/{board_id}/sections",
                     json={"name": "Sneaky"},
                     headers=auth_headers(bob_token))
    assert r.status_code == 403

    # 17. Token reuse is blocked
    r = client.post("/invitations/accept",
                     json={"token": token},
                     headers=auth_headers(bob_token))
    assert r.status_code == 400

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    test_password_reset()
    test_full_flow()
