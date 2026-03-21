import uuid
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.db import get_db, init_db
from backend.database.models import Run

app = FastAPI(title="gitFixr API")

# Allow Chrome extension to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ── Request / Response models ──────────────────────────────────────────────────

class FixIssueRequest(BaseModel):
    issue_url:   str
    issue_title: str
    issue_body:  str

class FixIssueResponse(BaseModel):
    run_id: str
    status: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.post("/fix-issue", response_model=FixIssueResponse)
def fix_issue(payload: FixIssueRequest, db: Session = Depends(get_db)):
    run_id = str(uuid.uuid4())

    run = Run(
        run_id    = run_id,
        issue_url = payload.issue_url,
        status    = "running",
    )
    db.add(run)
    db.commit()

    return FixIssueResponse(run_id=run_id, status="running")


@app.get("/health")
def health():
    return {"status": "ok"}