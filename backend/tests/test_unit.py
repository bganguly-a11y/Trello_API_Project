"""
Unit tests for pure utility functions.
No HTTP calls — functions are tested directly with minimal stubs.
Covers: security.py, core/deps.py permission helpers, tickets._validate_assignee,
        database helpers.
"""
import pytest
from datetime import timedelta
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.core.deps import (
    get_board_for_user,
    require_board_owner,
    can_edit_ticket,
)


# ===========================================================================
# security.py — hash_password / verify_password
# ===========================================================================

class TestPasswordHashing:
    def test_hash_is_not_plain_text(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"

    def test_hash_starts_with_bcrypt_prefix(self):
        hashed = hash_password("mysecret")
        assert hashed.startswith("$2")  # bcrypt prefix

    def test_verify_correct_password_returns_true(self):
        hashed = hash_password("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_verify_wrong_password_returns_false(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_two_hashes_of_same_password_differ(self):
        """bcrypt uses a random salt each time."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_verify_still_works_with_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert verify_password("same", h1) is True
        assert verify_password("same", h2) is True


# ===========================================================================
# security.py — create_access_token / decode_access_token
# ===========================================================================

class TestJWT:
    def test_create_token_returns_string(self):
        token = create_access_token("42")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token_returns_subject(self):
        token = create_access_token("99")
        subject = decode_access_token(token)
        assert subject == "99"

    def test_decode_invalid_token_returns_none(self):
        result = decode_access_token("not.a.valid.token")
        assert result is None

    def test_decode_garbage_string_returns_none(self):
        result = decode_access_token("garbage")
        assert result is None

    def test_decode_empty_string_returns_none(self):
        result = decode_access_token("")
        assert result is None

    def test_expired_token_returns_none(self):
        # Create a token that expired immediately
        token = create_access_token("123", expires_minutes=-1)
        result = decode_access_token(token)
        assert result is None

    def test_token_round_trip_preserves_subject(self):
        for user_id in ["1", "100", "9999"]:
            token = create_access_token(user_id)
            assert decode_access_token(token) == user_id


# ===========================================================================
# core/deps.py — permission helpers
# ===========================================================================

def _make_user(user_id=1):
    user = MagicMock()
    user.id = user_id
    return user


def _make_board(board_id=10, owner_id=1):
    board = MagicMock()
    board.id = board_id
    board.owner_id = owner_id
    return board


def _make_membership(board_id=10, user_id=1):
    m = MagicMock()
    m.board_id = board_id
    m.user_id = user_id
    return m


class TestGetBoardForUser:
    def _make_db(self, board=None, membership=None):
        """Build a minimal mock db whose .query().filter().first() chain works."""
        db = MagicMock()
        board_q = MagicMock()
        board_q.filter.return_value.first.return_value = board
        member_q = MagicMock()
        member_q.filter.return_value.first.return_value = membership

        def query_side_effect(model):
            from app.models import Board, BoardMember
            if model is Board:
                return board_q
            if model is BoardMember:
                return member_q
            return MagicMock()

        db.query.side_effect = query_side_effect
        return db

    def test_returns_board_for_member(self):
        user = _make_user(1)
        board = _make_board(10, owner_id=1)
        membership = _make_membership(10, 1)
        db = self._make_db(board=board, membership=membership)

        result = get_board_for_user(db, 10, user)
        assert result is board

    def test_raises_404_when_board_missing(self):
        user = _make_user(1)
        db = self._make_db(board=None, membership=None)
        with pytest.raises(HTTPException) as exc:
            get_board_for_user(db, 99, user)
        assert exc.value.status_code == 404

    def test_raises_403_when_not_member(self):
        user = _make_user(2)
        board = _make_board(10, owner_id=1)
        db = self._make_db(board=board, membership=None)
        with pytest.raises(HTTPException) as exc:
            get_board_for_user(db, 10, user)
        assert exc.value.status_code == 403


class TestRequireBoardOwner:
    def _make_db(self, board=None, membership=None):
        db = MagicMock()
        board_q = MagicMock()
        board_q.filter.return_value.first.return_value = board
        member_q = MagicMock()
        member_q.filter.return_value.first.return_value = membership

        def query_side_effect(model):
            from app.models import Board, BoardMember
            if model is Board:
                return board_q
            if model is BoardMember:
                return member_q
            return MagicMock()

        db.query.side_effect = query_side_effect
        return db

    def test_returns_board_for_owner(self):
        user = _make_user(1)
        board = _make_board(10, owner_id=1)
        membership = _make_membership(10, 1)
        db = self._make_db(board=board, membership=membership)
        result = require_board_owner(db, 10, user)
        assert result is board

    def test_raises_403_for_non_owner_member(self):
        user = _make_user(2)
        board = _make_board(10, owner_id=1)   # owner is user 1
        membership = _make_membership(10, 2)  # user 2 is a member
        db = self._make_db(board=board, membership=membership)
        with pytest.raises(HTTPException) as exc:
            require_board_owner(db, 10, user)
        assert exc.value.status_code == 403


class TestCanEditTicket:
    def _make_ticket(self, section_id=1, creator_id=1):
        t = MagicMock()
        t.section_id = section_id
        t.creator_id = creator_id
        return t

    def _make_db(self, section_board_id=10, board_owner_id=1):
        db = MagicMock()
        section = MagicMock()
        section.id = 1
        section.board_id = section_board_id
        board = MagicMock()
        board.id = section_board_id
        board.owner_id = board_owner_id

        sec_q = MagicMock()
        sec_q.filter.return_value.first.return_value = section
        board_q = MagicMock()
        board_q.filter.return_value.first.return_value = board

        def query_side_effect(model):
            from app.models import Section, Board
            if model is Section:
                return sec_q
            if model is Board:
                return board_q
            return MagicMock()

        db.query.side_effect = query_side_effect
        return db

    def test_board_owner_can_edit_any_ticket(self):
        user = _make_user(1)  # owner
        ticket = self._make_ticket(creator_id=2)
        db = self._make_db(board_owner_id=1)
        assert can_edit_ticket(db, ticket, user) is True

    def test_creator_can_edit_own_ticket(self):
        user = _make_user(3)  # neither owner nor admin
        ticket = self._make_ticket(creator_id=3)
        db = self._make_db(board_owner_id=1)
        assert can_edit_ticket(db, ticket, user) is True

    def test_non_owner_non_creator_cannot_edit(self):
        user = _make_user(5)
        ticket = self._make_ticket(creator_id=3)
        db = self._make_db(board_owner_id=1)
        assert can_edit_ticket(db, ticket, user) is False

    def test_returns_false_when_section_missing(self):
        user = _make_user(1)
        ticket = self._make_ticket()
        db = MagicMock()
        # section query returns None
        q = MagicMock()
        q.filter.return_value.first.return_value = None
        db.query.return_value = q
        assert can_edit_ticket(db, ticket, user) is False


# ===========================================================================
# tickets._validate_assignee
# ===========================================================================

class TestValidateAssignee:
    def test_none_assignee_does_not_raise(self):
        """_validate_assignee should be a no-op for None."""
        from app.routers.tickets import _validate_assignee
        db = MagicMock()
        # Should not raise, no db calls needed
        _validate_assignee(db, board_id=1, assignee_id=None)

    def test_valid_member_does_not_raise(self):
        from app.routers.tickets import _validate_assignee
        db = MagicMock()
        member_q = MagicMock()
        member_q.filter.return_value.first.return_value = MagicMock()
        db.query.return_value = member_q
        # Should not raise
        _validate_assignee(db, board_id=1, assignee_id=2)

    def test_non_member_assignee_raises_400(self):
        from app.routers.tickets import _validate_assignee
        db = MagicMock()
        member_q = MagicMock()
        member_q.filter.return_value.first.return_value = None  # not a member
        db.query.return_value = member_q
        with pytest.raises(HTTPException) as exc:
            _validate_assignee(db, board_id=1, assignee_id=99)
        assert exc.value.status_code == 400
