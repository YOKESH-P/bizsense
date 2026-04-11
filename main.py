from io import BytesIO
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, hash_password, verify_password
from database import Base, engine, get_db
from graph import build_bizsense_graph
from models import Report, User

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="BizSense API", version="1.0.0")
graph = build_bizsense_graph()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://[::1]:5500",
    ],
    # Keep local development flexible for different localhost ports.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=2)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AnalyzeRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=255)


class ReportResponse(BaseModel):
    id: int
    topic: str
    report_content: str
    created_at: str


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered")

    user = User(
        email=payload.email,
        password=hash_password(payload.password),
        name=payload.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User registered successfully"}


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token)


@app.post("/analyze")
def analyze_business(
    payload: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = graph.invoke({"topic": payload.topic})
        report_text = result.get("final_report", "No report generated.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}") from exc

    report = Report(user_id=current_user.id, topic=payload.topic, report_content=report_text)
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "message": "Analysis complete",
        "report_id": report.id,
        "current_agent": result.get("current_agent", "report"),
        "report_content": report_text,
    }


@app.get("/reports", response_model=List[ReportResponse])
def get_reports(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reports = (
        db.query(Report)
        .filter(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return [
        ReportResponse(
            id=report.id,
            topic=report.topic,
            report_content=report.report_content,
            created_at=report.created_at.isoformat(),
        )
        for report in reports
    ]


@app.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == current_user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResponse(
        id=report.id,
        topic=report.topic,
        report_content=report.report_content,
        created_at=report.created_at.isoformat(),
    )


@app.get("/reports/{report_id}/pdf")
def download_report_pdf(
    report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == current_user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        title=f"BizSense Report - {report.topic}",
        author="BizSense",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("BizSense Business Intelligence Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"<b>Topic:</b> {report.topic}", styles["Normal"]),
        Paragraph(f"<b>Generated:</b> {report.created_at.isoformat()}", styles["Normal"]),
        Spacer(1, 16),
    ]

    for block in report.report_content.split("\n\n"):
        text = block.strip().replace("\n", "<br/>")
        if not text:
            continue
        story.append(Paragraph(text, styles["BodyText"]))
        story.append(Spacer(1, 10))

    doc.build(story)
    buffer.seek(0)
    safe_topic = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in report.topic)[:80]
    filename = f"bizsense_report_{report.id}_{safe_topic or 'report'}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.delete("/reports/{report_id}")
def delete_report(
    report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == current_user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)
    db.commit()
    return {"message": "Report deleted successfully"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_frontend_root():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


# Serve any other files in `frontend/` (e.g. favicon, local assets) at /static/...
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend_static")
