"""SQLAlchemy ORM models for the Trello API."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # A user can own many boards (Board.owner_id).
    owned_boards = relationship("Board", back_populates="owner",
                                cascade="all, delete-orphan",
                                foreign_keys="Board.owner_id")
    # A user can be a member of many boards (via BoardMember).
    memberships = relationship("BoardMember", back_populates="user",
                                cascade="all, delete-orphan")
    # Tickets created by this user.
    created_tickets = relationship("Ticket", back_populates="creator",
                                    foreign_keys="Ticket.creator_id")
    # Tickets assigned to this user.
    assigned_tickets = relationship("Ticket", back_populates="assignee",
                                     foreign_keys="Ticket.assignee_id")


class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="owned_boards",
                          foreign_keys=[owner_id])
    members = relationship("BoardMember", back_populates="board",
                            cascade="all, delete-orphan")
    sections = relationship("Section", back_populates="board",
                             cascade="all, delete-orphan",
                             order_by="Section.id")
    invitations = relationship("Invitation", back_populates="board",
                                cascade="all, delete-orphan")


class BoardMember(Base):
    """Join table: who has access to which board."""
    __tablename__ = "board_members"
    __table_args__ = (UniqueConstraint("board_id", "user_id",
                                       name="uq_board_user"),)

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_owner = Column(Boolean, default=False, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    board = relationship("Board", back_populates="members")
    user = relationship("User", back_populates="memberships")


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    # Parent board CANNOT be changed — enforced in routers, not at DB level.
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    board = relationship("Board", back_populates="sections")
    tickets = relationship("Ticket", back_populates="section",
                            cascade="all, delete-orphan",
                            order_by="Ticket.id")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    section = relationship("Section", back_populates="tickets")
    creator = relationship("User", back_populates="created_tickets",
                            foreign_keys=[creator_id])
    assignee = relationship("User", back_populates="assigned_tickets",
                             foreign_keys=[assignee_id])


class Invitation(Base):
    """An invite token that can be redeemed to join a board as a member."""
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)

    board = relationship("Board", back_populates="invitations")
