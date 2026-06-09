"""Application entrypoint. Run with: uvicorn app.main:app --reload"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import auth, boards, invitations, sections, tickets

# In production switch to Alembic migrations. For dev, this is convenient.
init_db()

app = FastAPI(
    title="Trello Clone REST API",
    description="A FastAPI implementation of a Trello-style board/section/ticket service.",
    version="1.0.0",
)

# CORS — broad in dev. Tighten for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(boards.router)
app.include_router(sections.router)
app.include_router(tickets.router)
app.include_router(invitations.router)

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/frontend", StaticFiles(directory=frontend_dist, html=True),
              name="frontend")


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "docs": "/docs"}
