"""Section CRUD. Sections live under a board; parent board is immutable."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import (get_board_for_user, get_current_user,
                            require_board_owner)
from app.database import get_db
from app.models import Section, User
from app.schemas import SectionCreate, SectionOut, SectionUpdate

router = APIRouter(tags=["sections"])


@router.post("/boards/{board_id}/sections",
             response_model=SectionOut,
             status_code=status.HTTP_201_CREATED)
def create_section(board_id: int,
                   payload: SectionCreate,
                   db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Only the board owner can create sections."""
    require_board_owner(db, board_id, user)
    section = Section(name=payload.name,
                       description=payload.description,
                       board_id=board_id)
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


@router.get("/boards/{board_id}/sections",
            response_model=List[SectionOut])
def list_sections(board_id: int,
                  db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """Any board member can list sections."""
    get_board_for_user(db, board_id, user)
    return (
        db.query(Section)
        .filter(Section.board_id == board_id)
        .order_by(Section.id)
        .all()
    )


@router.get("/sections/{section_id}", response_model=SectionOut)
def get_section(section_id: int,
                db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    section = db.query(Section).filter(Section.id == section_id).first()
    if section is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Section not found")
    get_board_for_user(db, section.board_id, user)
    return section


@router.patch("/sections/{section_id}", response_model=SectionOut)
def update_section(section_id: int,
                   payload: SectionUpdate,
                   db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Only board owner can edit sections. Parent board cannot change."""
    section = db.query(Section).filter(Section.id == section_id).first()
    if section is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Section not found")
    require_board_owner(db, section.board_id, user)

    if payload.name is not None:
        section.name = payload.name
    if payload.description is not None:
        section.description = payload.description
    db.commit()
    db.refresh(section)
    return section


@router.delete("/sections/{section_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def delete_section(section_id: int,
                   db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Only board owner can delete a section. Cascades to its tickets."""
    section = db.query(Section).filter(Section.id == section_id).first()
    if section is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Section not found")
    require_board_owner(db, section.board_id, user)
    db.delete(section)
    db.commit()
    return None
