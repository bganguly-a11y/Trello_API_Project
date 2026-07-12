"""Ticket CRUD. Section can change but must remain on the same board."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import (can_edit_ticket, get_board_for_user,
                            get_current_user, require_board_owner)
from app.database import get_db
from app.models import BoardMember, Section, Ticket, User
from app.schemas import TicketCreate, TicketOut, TicketUpdate

router = APIRouter(tags=["tickets"])


def _validate_assignee(db: Session, board_id: int,
                        assignee_id: Optional[int]) -> None:
    """Make sure assignee (if set) is a member of the board."""
    if assignee_id is None:
        return
    is_member = (
        db.query(BoardMember)
        .filter(BoardMember.board_id == board_id,
                BoardMember.user_id == assignee_id)
        .first()
    )
    if is_member is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be a member of the board",
        )


@router.post("/sections/{section_id}/tickets",
             response_model=TicketOut,
             status_code=status.HTTP_201_CREATED)
def create_ticket(section_id: int,
                  payload: TicketCreate,
                  db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """Any board member can create tickets in any section of that board."""
    section = db.query(Section).filter(Section.id == section_id).first()
    if section is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Section not found")
    get_board_for_user(db, section.board_id, user)
    _validate_assignee(db, section.board_id, payload.assignee_id)

    ticket = Ticket(
        name=payload.name,
        description=payload.description,
        section_id=section_id,
        creator_id=user.id,
        assignee_id=payload.assignee_id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/sections/{section_id}/tickets",
            response_model=List[TicketOut])
def list_tickets(section_id: int,
                 db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    section = db.query(Section).filter(Section.id == section_id).first()
    if section is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Section not found")
    get_board_for_user(db, section.board_id, user)
    return (
        db.query(Ticket)
        .filter(Ticket.section_id == section_id)
        .order_by(Ticket.id)
        .all()
    )


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int,
               db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    section = db.query(Section).filter(Section.id == ticket.section_id).first()
    get_board_for_user(db, section.board_id, user)
    return ticket


@router.patch("/tickets/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int,
                  payload: TicketUpdate,
                  db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """
    Editable by:
      - The board owner (any ticket on the board), or
      - The user who created the ticket (their own tickets only).
    Can move the ticket to a different section on the SAME board.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    current_section = (
        db.query(Section).filter(Section.id == ticket.section_id).first()
    )
    # Make sure the user is at least a member of the parent board.
    get_board_for_user(db, current_section.board_id, user)

    if not can_edit_ticket(db, ticket, user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You can only edit tickets you created (or be the board owner)",
        )

    # Optional move: validate target section is on the same board.
    if payload.section_id is not None and payload.section_id != ticket.section_id:
        target = db.query(Section).filter(Section.id == payload.section_id).first()
        if target is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Target section not found",
            )
        if target.board_id != current_section.board_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Cannot move ticket to a section on a different board",
            )
        ticket.section_id = target.id

    if payload.name is not None:
        ticket.name = payload.name
    if payload.description is not None:
        ticket.description = payload.description
    if payload.assignee_id is not None:
        _validate_assignee(db, current_section.board_id, payload.assignee_id)
        ticket.assignee_id = payload.assignee_id

    db.commit()
    db.refresh(ticket)
    return ticket


@router.delete("/tickets/{ticket_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: int,
                  db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """Same permission rule as edit: owner or creator."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    section = db.query(Section).filter(Section.id == ticket.section_id).first()
    get_board_for_user(db, section.board_id, user)

    if not can_edit_ticket(db, ticket, user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You can only delete tickets you created (or be the board owner)",
        )
    db.delete(ticket)
    db.commit()
    return None
