"""Board endpoints — create, list, detail, update, delete, invite."""
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import (get_board_for_user, get_current_user,
                            require_board_owner)
from app.database import get_db
from app.models import (Board, BoardMember, Invitation, Section, Ticket,
                         User)
from app.schemas import (BoardCreate, BoardDetail, BoardMemberOut, BoardOut,
                          BoardUpdate, InvitationOut, SectionDetail,
                          TicketDetail)

router = APIRouter(prefix="/boards", tags=["boards"])


@router.post("/", response_model=BoardOut,
             status_code=status.HTTP_201_CREATED)
def create_board(payload: BoardCreate,
                 db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """Create a board. Creator becomes owner and is added as a member."""
    board = Board(name=payload.name,
                   description=payload.description,
                   owner_id=user.id)
    db.add(board)
    db.flush()  # need board.id before creating membership

    membership = BoardMember(board_id=board.id, user_id=user.id, is_owner=True)
    db.add(membership)
    db.commit()
    db.refresh(board)
    return board


@router.get("/", response_model=List[BoardOut])
def list_boards(db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """List every board the current user can access (owner or member)."""
    boards = (
        db.query(Board)
        .join(BoardMember, BoardMember.board_id == Board.id)
        .filter(BoardMember.user_id == user.id)
        .all()
    )
    return boards


@router.get("/{board_id}", response_model=BoardDetail)
def get_board_detail(board_id: int,
                     db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """
    Return full board info: sections (with tickets), members, and
    invitation tokens. Available only to board members.
    """
    board = get_board_for_user(db, board_id, user)

    # Build nested sections + tickets
    sections = (
        db.query(Section)
        .filter(Section.board_id == board.id)
        .order_by(Section.id)
        .all()
    )
    section_details = []
    for sec in sections:
        tickets = (
            db.query(Ticket)
            .filter(Ticket.section_id == sec.id)
            .order_by(Ticket.id)
            .all()
        )
        section_details.append(SectionDetail(
            id=sec.id,
            name=sec.name,
            description=sec.description,
            board_id=sec.board_id,
            created_at=sec.created_at,
            tickets=[TicketDetail.model_validate(t) for t in tickets],
        ))

    # Members
    member_rows = (
        db.query(BoardMember, User)
        .join(User, User.id == BoardMember.user_id)
        .filter(BoardMember.board_id == board.id)
        .all()
    )
    members = [
        BoardMemberOut(
            user_id=u.id, email=u.email,
            first_name=u.first_name, last_name=u.last_name,
            is_owner=m.is_owner,
        )
        for m, u in member_rows
    ]

    # Invitations — only the owner sees these (others get an empty list)
    invitations: List[InvitationOut] = []
    if board.owner_id == user.id:
        invitations = [
            InvitationOut.model_validate(inv) for inv in board.invitations
        ]

    return BoardDetail(
        id=board.id,
        name=board.name,
        description=board.description,
        owner_id=board.owner_id,
        created_at=board.created_at,
        sections=section_details,
        members=members,
        invitations=invitations,
    )


@router.patch("/{board_id}", response_model=BoardOut)
def update_board(board_id: int,
                 payload: BoardUpdate,
                 db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """Only the owner can edit board details."""
    board = require_board_owner(db, board_id, user)
    if payload.name is not None:
        board.name = payload.name
    if payload.description is not None:
        board.description = payload.description
    db.commit()
    db.refresh(board)
    return board


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board(board_id: int,
                 db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """Owner-only. Cascades to sections, tickets, members, invitations."""
    board = require_board_owner(db, board_id, user)
    db.delete(board)
    db.commit()
    return None


# ---------- Invitations on a board ----------

@router.post("/{board_id}/invitations",
             response_model=InvitationOut,
             status_code=status.HTTP_201_CREATED)
def create_invitation(board_id: int,
                      db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """
    Owner-only. Generates a one-time-use token. Hand the token to the
    invitee — they POST it to /invitations/accept to join.
    """
    require_board_owner(db, board_id, user)
    invite = Invitation(
        board_id=board_id,
        token=secrets.token_urlsafe(24),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite
