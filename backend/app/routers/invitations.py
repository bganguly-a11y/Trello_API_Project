"""Accepting invitation tokens to join a board."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import BoardMember, Invitation, User
from app.schemas import BoardOut, InvitationAccept

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post("/accept", response_model=BoardOut)
def accept_invitation(payload: InvitationAccept,
                      db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """
    Redeem an invite token. The current user is added as a (non-owner)
    member of the board. The token is single-use.
    """
    invite = (
        db.query(Invitation)
        .filter(Invitation.token == payload.token)
        .first()
    )
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                             detail="Invalid invitation token")
    if invite.used_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                             detail="This invitation has already been used")

    # Idempotency: if the user is already a member, just return the board.
    existing = (
        db.query(BoardMember)
        .filter(BoardMember.board_id == invite.board_id,
                BoardMember.user_id == user.id)
        .first()
    )
    if existing is None:
        db.add(BoardMember(board_id=invite.board_id,
                            user_id=user.id, is_owner=False))

    invite.used_at = datetime.utcnow()
    db.commit()
    db.refresh(invite)
    return invite.board
