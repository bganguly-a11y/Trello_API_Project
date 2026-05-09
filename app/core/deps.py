"""Reusable FastAPI dependencies — auth and permission checks."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models import Board, BoardMember, Section, Ticket, User

# tokenUrl is just the path the OpenAPI docs "Authorize" button posts to.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the JWT to the authenticated User, or raise 401."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id_str = decode_access_token(token)
    if user_id_str is None:
        raise credentials_exc
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        raise credentials_exc
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exc
    return user


# ---------- Permission helpers ----------

def get_board_for_user(db: Session, board_id: int, user: User) -> Board:
    """Return the board only if the user is a member; raise 404/403 otherwise."""
    board = db.query(Board).filter(Board.id == board_id).first()
    if board is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found")
    membership = (
        db.query(BoardMember)
        .filter(BoardMember.board_id == board_id,
                BoardMember.user_id == user.id)
        .first()
    )
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                             detail="You don't have access to this board")
    return board


def require_board_owner(db: Session, board_id: int, user: User) -> Board:
    """Like get_board_for_user but also requires owner role."""
    board = get_board_for_user(db, board_id, user)
    if board.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                             detail="Only the board owner can perform this action")
    return board


def can_edit_ticket(db: Session, ticket: Ticket, user: User) -> bool:
    """Owner of the parent board or creator of the ticket can edit."""
    section = db.query(Section).filter(Section.id == ticket.section_id).first()
    if section is None:
        return False
    board = db.query(Board).filter(Board.id == section.board_id).first()
    if board is None:
        return False
    if board.owner_id == user.id:
        return True
    return ticket.creator_id == user.id
