"""Pydantic schemas — define request/response shapes and validation."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- User ----------

class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)


class UserOut(UserBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordReset(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Board ----------

class BoardBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class BoardCreate(BoardBase):
    pass


class BoardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class BoardOut(BoardBase):
    id: int
    owner_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- Section ----------

class SectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class SectionCreate(SectionBase):
    pass


class SectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class SectionOut(SectionBase):
    id: int
    board_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- Ticket ----------

class TicketBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    assignee_id: Optional[int] = None


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    assignee_id: Optional[int] = None
    # Allow moving the ticket to a different section (must be on same board).
    section_id: Optional[int] = None


class TicketOut(TicketBase):
    id: int
    section_id: int
    creator_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- Invitation ----------

class InvitationOut(BaseModel):
    id: int
    board_id: int
    token: str
    created_at: datetime
    used_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class InvitationAccept(BaseModel):
    token: str


# ---------- Detailed board view (nested) ----------

class TicketDetail(TicketOut):
    pass


class SectionDetail(SectionOut):
    tickets: List[TicketDetail] = Field(default_factory=list)


class BoardMemberOut(BaseModel):
    user_id: int
    email: EmailStr
    name: str
    is_owner: bool


class BoardDetail(BoardOut):
    sections: List[SectionDetail] = Field(default_factory=list)
    members: List[BoardMemberOut] = Field(default_factory=list)
    invitations: List[InvitationOut] = Field(default_factory=list)
