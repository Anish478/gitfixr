import uuid
import asyncio
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import get_db, init_db, SessionLocal
from database.models import Run

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
    issue_url:      str
    issue_title:    str
    issue_body:     str
    issue_comments: list[str] = []
    issue_images:   list[str] = []

class FixIssueResponse(BaseModel):
    run_id: str
    status: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.post("/fix-issue", response_model=FixIssueResponse)
async def fix_issue(payload: FixIssueRequest, db: Session = Depends(get_db)):
    run_id = str(uuid.uuid4())

    # Parse repo owner and name from the GitHub issue URL
    # URL format: https://github.com/{owner}/{repo}/issues/{number}
    parts = payload.issue_url.replace("https://github.com/", "").split("/")
    repo_owner = parts[0]
    repo_name  = parts[1]

    # Save the run as "running" immediately so the sidebar can poll it
    run = Run(
        run_id    = run_id,
        issue_url = payload.issue_url,
        status    = "running",
    )
    db.add(run)
    db.commit()

    # Build the initial pipeline state
    initial_state = {
        "issue_url":          payload.issue_url,
        "issue_title":        payload.issue_title,
        "issue_body":         payload.issue_body,
        "issue_comments":     payload.issue_comments,
        "issue_images":       payload.issue_images,
        "repo_owner":         repo_owner,
        "repo_name":          repo_name,
        "memory_lessons":     [],
        "memory_matches":     [],
        "relevant_files":     [],
        "plan":               "",
        "patch":              "",
        "retry_strategy":     "standard",
        "sandbox_result":     {},
        "critic_scores":      {},
        "retry_count":        0,
        "memory_attempt_used": False,
        "pr_url":             None,
        "status":             "running",
        "error":              None,
    }

    # Fire and forget — pipeline runs in background, HTTP response returns immediately
    asyncio.create_task(_run_pipeline(run_id, initial_state))

    return FixIssueResponse(run_id=run_id, status="running")


@app.get("/status/{run_id}")
def get_status(run_id: str, db: Session = Depends(get_db)):
    """Sidebar polls this every 3 seconds to check progress."""
    run = db.query(Run).filter(Run.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": run.status, "pr_url": run.pr_url, "error": run.error}


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Background pipeline runner ─────────────────────────────────────────────────

async def _run_pipeline(run_id: str, state: dict):
    """
    Runs the LangGraph pipeline and writes the outcome to the DB.
    Errors are caught so a failure never crashes the server.
    """
    from pipeline.graph import build_graph   # imported here to avoid circular imports at startup

    graph = build_graph()
    db = SessionLocal()
    try:
        result = await graph.ainvoke(state)
        db.query(Run).filter(Run.run_id == run_id).update({
            "status": "success",
            "pr_url": result.get("pr_url"),
        })
    except Exception as exc:
        db.query(Run).filter(Run.run_id == run_id).update({
            "status": "failed",
            "error":  str(exc),
        })
        print(f"[gitFixr] Pipeline error for {run_id}: {exc}")
    finally:
        db.commit()
        db.close()