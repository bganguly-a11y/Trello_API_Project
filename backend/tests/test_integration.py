"""
Integration tests using FastAPI TestClient + in-memory SQLite DB.
Covers ≥50% of all API endpoints (auth, boards, sections, tickets, invitations).

Fixtures are defined in conftest.py.
"""
import pytest
# pyrefly: ignore [missing-import]
from tests.conftest import auth, _register, _login


# ===========================================================================
# Auth endpoints — /auth/*
# ===========================================================================

class TestAuthRegister:
    def test_register_success(self, client):
        r = client.post("/auth/register", json={
            "email": "new_user@example.com",
            "password": "password123",
            "name": "New User",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "new_user@example.com"
        assert data["name"] == "New User"
        assert "id" in data
        assert "hashed_password" not in data  # never leak the hash

    def test_register_duplicate_email_returns_400(self, client):
        client.post("/auth/register", json={
            "email": "dup@example.com",
            "password": "abc12345",
            "name": "First",
        })
        r = client.post("/auth/register", json={
            "email": "dup@example.com",
            "password": "xyz98765",
            "name": "Second",
        })
        assert r.status_code == 400
        assert "already exists" in r.json()["detail"].lower()

    def test_register_missing_fields_returns_422(self, client):
        r = client.post("/auth/register", json={"email": "bad@example.com"})
        assert r.status_code == 422


class TestAuthLogin:
    def test_login_success_returns_token(self, client):
        _register(client, "login_ok@example.com")
        r = client.post("/auth/login",
                         data={"username": "login_ok@example.com",
                               "password": "secret123"})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client):
        _register(client, "login_bad@example.com")
        r = client.post("/auth/login",
                         data={"username": "login_bad@example.com",
                               "password": "WRONG"})
        assert r.status_code == 401

    def test_login_unknown_email_returns_401(self, client):
        r = client.post("/auth/login",
                         data={"username": "nobody@example.com",
                               "password": "whatever"})
        assert r.status_code == 401


class TestAuthMe:
    def test_me_returns_current_user(self, client, alice_token):
        r = client.get("/auth/me", headers=auth(alice_token))
        assert r.status_code == 200
        assert r.json()["email"] == "alice_fix@example.com"

    def test_me_without_token_returns_401(self, client):
        r = client.get("/auth/me")
        assert r.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        r = client.get("/auth/me", headers=auth("bad.token.here"))
        assert r.status_code == 401


class TestPasswordReset:
    def test_reset_password_success(self, client):
        _register(client, "reset_test@example.com", password="old_pass")
        r = client.post("/auth/reset-password", json={
            "email": "reset_test@example.com",
            "password": "new_pass_456",
        })
        assert r.status_code == 200
        # Old password no longer works
        r2 = client.post("/auth/login",
                          data={"username": "reset_test@example.com",
                                "password": "old_pass"})
        assert r2.status_code == 401
        # New password works
        r3 = client.post("/auth/login",
                          data={"username": "reset_test@example.com",
                                "password": "new_pass_456"})
        assert r3.status_code == 200

    def test_reset_unknown_email_returns_404(self, client):
        r = client.post("/auth/reset-password", json={
            "email": "ghost@example.com",
            "password": "irrelevant",
        })
        assert r.status_code == 404


# ===========================================================================
# Board endpoints — /boards/*
# ===========================================================================

class TestBoardCreate:
    def test_create_board_success(self, client, alice_token):
        r = client.post("/boards/", json={"name": "My Board"},
                        headers=auth(alice_token))
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "My Board"
        assert "id" in data

    def test_create_board_with_description(self, client, alice_token):
        r = client.post("/boards/",
                        json={"name": "Described", "description": "A desc"},
                        headers=auth(alice_token))
        assert r.status_code == 201
        assert r.json()["description"] == "A desc"

    def test_create_board_unauthenticated_returns_401(self, client):
        r = client.post("/boards/", json={"name": "Nope"})
        assert r.status_code == 401


class TestBoardList:
    def test_owner_sees_own_board(self, client, alice_token):
        r_create = client.post("/boards/", json={"name": "ListMe"},
                               headers=auth(alice_token))
        board_id = r_create.json()["id"]

        r = client.get("/boards/", headers=auth(alice_token))
        assert r.status_code == 200
        ids = [b["id"] for b in r.json()]
        assert board_id in ids

    def test_non_member_does_not_see_board(self, client, alice_token, bob_token):
        r_create = client.post("/boards/", json={"name": "AliceOnly"},
                               headers=auth(alice_token))
        board_id = r_create.json()["id"]

        r = client.get("/boards/", headers=auth(bob_token))
        assert r.status_code == 200
        ids = [b["id"] for b in r.json()]
        assert board_id not in ids


class TestBoardDetail:
    def _create_board(self, client, token, name="Detail Board"):
        r = client.post("/boards/", json={"name": name}, headers=auth(token))
        return r.json()["id"]

    def test_owner_sees_detail(self, client, alice_token):
        bid = self._create_board(client, alice_token)
        r = client.get(f"/boards/{bid}", headers=auth(alice_token))
        assert r.status_code == 200
        assert "sections" in r.json()
        assert "members" in r.json()

    def test_non_member_gets_403(self, client, alice_token, bob_token):
        bid = self._create_board(client, alice_token, "Private Board")
        r = client.get(f"/boards/{bid}", headers=auth(bob_token))
        assert r.status_code == 403

    def test_nonexistent_board_returns_404(self, client, alice_token):
        r = client.get("/boards/99999", headers=auth(alice_token))
        assert r.status_code == 404


class TestBoardUpdate:
    def _create_board(self, client, token):
        r = client.post("/boards/", json={"name": "Patchable"},
                        headers=auth(token))
        return r.json()["id"]

    def test_owner_can_rename_board(self, client, alice_token):
        bid = self._create_board(client, alice_token)
        r = client.patch(f"/boards/{bid}",
                         json={"name": "Renamed"},
                         headers=auth(alice_token))
        assert r.status_code == 200
        assert r.json()["name"] == "Renamed"

    def test_non_owner_cannot_rename(self, client, alice_token, bob_token):
        """Bob cannot rename Alice's board."""
        bid = self._create_board(client, alice_token)
        # Invite Bob so he has access
        inv = client.post(f"/boards/{bid}/invitations",
                          headers=auth(alice_token)).json()["token"]
        client.post("/invitations/accept", json={"token": inv},
                    headers=auth(bob_token))
        r = client.patch(f"/boards/{bid}",
                         json={"name": "HijackedName"},
                         headers=auth(bob_token))
        assert r.status_code == 403


class TestBoardDelete:
    def test_owner_can_delete_board(self, client, alice_token):
        r_create = client.post("/boards/", json={"name": "ToDelete"},
                               headers=auth(alice_token))
        bid = r_create.json()["id"]
        r = client.delete(f"/boards/{bid}", headers=auth(alice_token))
        assert r.status_code == 204

    def test_non_owner_cannot_delete(self, client, alice_token, bob_token):
        r_create = client.post("/boards/", json={"name": "AliceProtected"},
                               headers=auth(alice_token))
        bid = r_create.json()["id"]
        # Bob is not a member at all, should get 403 (via member check first)
        r = client.delete(f"/boards/{bid}", headers=auth(bob_token))
        assert r.status_code in (403, 404)


# ===========================================================================
# Section endpoints — /boards/{id}/sections  &  /sections/{id}
# ===========================================================================

class TestSections:
    @pytest.fixture()
    def board_id(self, client, alice_token):
        r = client.post("/boards/", json={"name": "SectionBoard"},
                        headers=auth(alice_token))
        return r.json()["id"]

    @pytest.fixture()
    def board_and_invited_bob(self, client, alice_token, bob_token, board_id):
        inv = client.post(f"/boards/{board_id}/invitations",
                          headers=auth(alice_token)).json()["token"]
        client.post("/invitations/accept", json={"token": inv},
                    headers=auth(bob_token))
        return board_id

    def test_owner_can_create_section(self, client, alice_token, board_id):
        r = client.post(f"/boards/{board_id}/sections",
                        json={"name": "To Do"},
                        headers=auth(alice_token))
        assert r.status_code == 201
        assert r.json()["name"] == "To Do"

    def test_member_cannot_create_section(self, client, alice_token, bob_token,
                                           board_and_invited_bob):
        bid = board_and_invited_bob
        r = client.post(f"/boards/{bid}/sections",
                        json={"name": "Sneaky"},
                        headers=auth(bob_token))
        assert r.status_code == 403

    def test_member_can_list_sections(self, client, alice_token, bob_token,
                                       board_and_invited_bob):
        bid = board_and_invited_bob
        client.post(f"/boards/{bid}/sections", json={"name": "Backlog"},
                    headers=auth(alice_token))
        r = client.get(f"/boards/{bid}/sections", headers=auth(bob_token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_owner_can_update_section(self, client, alice_token, board_id):
        sec = client.post(f"/boards/{board_id}/sections",
                           json={"name": "Original"},
                           headers=auth(alice_token)).json()
        r = client.patch(f"/sections/{sec['id']}",
                         json={"name": "Updated"},
                         headers=auth(alice_token))
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"

    def test_owner_can_delete_section(self, client, alice_token, board_id):
        sec = client.post(f"/boards/{board_id}/sections",
                           json={"name": "DeleteMe"},
                           headers=auth(alice_token)).json()
        r = client.delete(f"/sections/{sec['id']}", headers=auth(alice_token))
        assert r.status_code == 204

    def test_get_section_by_id(self, client, alice_token, board_id):
        sec = client.post(f"/boards/{board_id}/sections",
                           json={"name": "Fetchable"},
                           headers=auth(alice_token)).json()
        r = client.get(f"/sections/{sec['id']}", headers=auth(alice_token))
        assert r.status_code == 200
        assert r.json()["name"] == "Fetchable"


# ===========================================================================
# Ticket endpoints — /sections/{id}/tickets  &  /tickets/{id}
# ===========================================================================

class TestTickets:
    @pytest.fixture()
    def setup(self, client, alice_token, bob_token):
        """Create a board, invite Bob, create a section, return IDs."""
        board = client.post("/boards/",
                             json={"name": "TicketBoard"},
                             headers=auth(alice_token)).json()
        bid = board["id"]
        inv = client.post(f"/boards/{bid}/invitations",
                           headers=auth(alice_token)).json()["token"]
        client.post("/invitations/accept", json={"token": inv},
                    headers=auth(bob_token))
        sec = client.post(f"/boards/{bid}/sections",
                           json={"name": "Todo"},
                           headers=auth(alice_token)).json()
        return {"board_id": bid, "section_id": sec["id"]}

    def test_member_can_create_ticket(self, client, bob_token, setup):
        r = client.post(f"/sections/{setup['section_id']}/tickets",
                        json={"name": "My Task"},
                        headers=auth(bob_token))
        assert r.status_code == 201
        assert r.json()["name"] == "My Task"

    def test_member_can_list_tickets(self, client, alice_token, bob_token, setup):
        client.post(f"/sections/{setup['section_id']}/tickets",
                    json={"name": "Task A"},
                    headers=auth(alice_token))
        r = client.get(f"/sections/{setup['section_id']}/tickets",
                       headers=auth(bob_token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_creator_can_update_own_ticket(self, client, bob_token, setup):
        t = client.post(f"/sections/{setup['section_id']}/tickets",
                        json={"name": "Bob Task"},
                        headers=auth(bob_token)).json()
        r = client.patch(f"/tickets/{t['id']}",
                         json={"name": "Bob Task Renamed"},
                         headers=auth(bob_token))
        assert r.status_code == 200
        assert r.json()["name"] == "Bob Task Renamed"

    def test_member_cannot_update_others_ticket(self, client, alice_token,
                                                  bob_token, setup):
        t = client.post(f"/sections/{setup['section_id']}/tickets",
                        json={"name": "Alice Task"},
                        headers=auth(alice_token)).json()
        r = client.patch(f"/tickets/{t['id']}",
                         json={"name": "hacked"},
                         headers=auth(bob_token))
        assert r.status_code == 403

    def test_board_owner_can_update_any_ticket(self, client, alice_token,
                                                 bob_token, setup):
        t = client.post(f"/sections/{setup['section_id']}/tickets",
                        json={"name": "Bob Task 2"},
                        headers=auth(bob_token)).json()
        r = client.patch(f"/tickets/{t['id']}",
                         json={"description": "Owner edited"},
                         headers=auth(alice_token))
        assert r.status_code == 200

    def test_ticket_move_within_board(self, client, alice_token, bob_token, setup):
        """Ticket can be moved between sections on the same board."""
        sec2 = client.post(f"/boards/{setup['board_id']}/sections",
                            json={"name": "Done"},
                            headers=auth(alice_token)).json()
        t = client.post(f"/sections/{setup['section_id']}/tickets",
                        json={"name": "Movable"},
                        headers=auth(bob_token)).json()
        r = client.patch(f"/tickets/{t['id']}",
                         json={"section_id": sec2["id"]},
                         headers=auth(bob_token))
        assert r.status_code == 200
        assert r.json()["section_id"] == sec2["id"]

    def test_ticket_cross_board_move_blocked(self, client, alice_token,
                                               bob_token, setup):
        """Moving a ticket to a section on a different board returns 400."""
        other_board = client.post("/boards/", json={"name": "Other"},
                                   headers=auth(bob_token)).json()
        other_sec = client.post(f"/boards/{other_board['id']}/sections",
                                 json={"name": "Inbox"},
                                 headers=auth(bob_token)).json()
        t = client.post(f"/sections/{setup['section_id']}/tickets",
                        json={"name": "Cross"},
                        headers=auth(bob_token)).json()
        r = client.patch(f"/tickets/{t['id']}",
                         json={"section_id": other_sec["id"]},
                         headers=auth(bob_token))
        assert r.status_code == 400

    def test_creator_can_delete_own_ticket(self, client, bob_token, setup):
        t = client.post(f"/sections/{setup['section_id']}/tickets",
                        json={"name": "Delete Me"},
                        headers=auth(bob_token)).json()
        r = client.delete(f"/tickets/{t['id']}", headers=auth(bob_token))
        assert r.status_code == 204

    def test_get_ticket_by_id(self, client, alice_token, setup):
        t = client.post(f"/sections/{setup['section_id']}/tickets",
                        json={"name": "Fetchable Ticket"},
                        headers=auth(alice_token)).json()
        r = client.get(f"/tickets/{t['id']}", headers=auth(alice_token))
        assert r.status_code == 200
        assert r.json()["name"] == "Fetchable Ticket"

    def test_get_nonexistent_ticket_returns_404(self, client, alice_token):
        r = client.get("/tickets/99999", headers=auth(alice_token))
        assert r.status_code == 404


# ===========================================================================
# Invitation endpoints — /boards/{id}/invitations  &  /invitations/accept
# ===========================================================================

class TestInvitations:
    @pytest.fixture()
    def alice_board(self, client, alice_token):
        r = client.post("/boards/", json={"name": "InviteBoard"},
                        headers=auth(alice_token))
        return r.json()["id"]

    def test_owner_can_create_invitation(self, client, alice_token, alice_board):
        r = client.post(f"/boards/{alice_board}/invitations",
                        headers=auth(alice_token))
        assert r.status_code == 201
        assert "token" in r.json()

    def test_non_owner_cannot_create_invitation(self, client, alice_token,
                                                  bob_token, alice_board):
        r = client.post(f"/boards/{alice_board}/invitations",
                        headers=auth(bob_token))
        assert r.status_code in (403, 404)

    def test_valid_token_adds_member(self, client, alice_token, bob_token,
                                      alice_board):
        inv = client.post(f"/boards/{alice_board}/invitations",
                           headers=auth(alice_token)).json()["token"]
        r = client.post("/invitations/accept", json={"token": inv},
                        headers=auth(bob_token))
        assert r.status_code == 200
        # Bob should now see the board in his list
        boards = client.get("/boards/", headers=auth(bob_token)).json()
        ids = [b["id"] for b in boards]
        assert alice_board in ids

    def test_reusing_token_returns_400(self, client, alice_token, bob_token,
                                        alice_board):
        inv = client.post(f"/boards/{alice_board}/invitations",
                           headers=auth(alice_token)).json()["token"]
        client.post("/invitations/accept", json={"token": inv},
                    headers=auth(bob_token))
        # Second use
        r = client.post("/invitations/accept", json={"token": inv},
                        headers=auth(bob_token))
        assert r.status_code == 400

    def test_invalid_token_returns_404(self, client, alice_token):
        r = client.post("/invitations/accept",
                        json={"token": "completely_fake_token"},
                        headers=auth(alice_token))
        assert r.status_code == 404
