import os
import re
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, status, Form, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import desc
from fastapi import BackgroundTasks
import smtplib
from email.message import EmailMessage

from database import Base, engine, get_db
from models import Video, Admin, ContactMessage
from schemas import VideoCreate, VideoResponse, ContactMessageCreate

# ---------------------------
# APP INITIALIZATION
# ---------------------------
app = FastAPI(title="Evangelist Ministry Website")

# Create required folders
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# ---------------------------
# SECURITY
# ---------------------------
SECRET_KEY = "YOUR_SECRET_KEY"  # Replace with a secure random string
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def get_password_hash(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_admin_cookie(access_token: str = Cookie(None), db: Session = Depends(get_db)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        token = access_token.split(" ")[1]  # Bearer <token>
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")
    return admin

# ---------------------------
# DATABASE
# ---------------------------
Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def create_initial_admin():
    db = next(get_db())
    if not db.query(Admin).filter(Admin.username == "admin").first():
        hashed_password = get_password_hash("StrongPassword123")
        admin = Admin(username="admin", hashed_password=hashed_password)
        db.add(admin)
        db.commit()

# ---------------------------
# HELPERS
# ---------------------------
def extract_youtube_id(url: str):
    """Extracts YouTube video ID from URL"""
    match = re.search(r"(?:v=|youtu\.be/)([\w-]+)", url)
    return match.group(1) if match else None

# ---------------------------
# PUBLIC ROUTES
# ---------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    videos = db.query(Video).all()
    return templates.TemplateResponse("index.html", {"request": request, "videos": videos})

@app.get("/watch", include_in_schema=False)
def watch_latest(request: Request, db: Session = Depends(get_db)):
    latest_video = (
        db.query(Video)
        .order_by(Video.published_at.desc())
        .first()
    )

    if not latest_video:
        return RedirectResponse(url="/", status_code=302)

    return RedirectResponse(
        url=f"/watch/{latest_video.id}",
        status_code=302
    )

@app.get("/watch/{video_id}", response_class=HTMLResponse)
def watch_video(video_id: int, request: Request, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return templates.TemplateResponse(
        "watch.html",
        {"request": request, "video": video}
    )

@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse(
        "about.html",
        {"request": request}
    )


@app.get('/donate', response_class=HTMLResponse)
def donate(request: Request):
    return templates. TemplateResponse(
        "donate.html",
        {"request": request}
    )

@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates. TemplateResponse(
        "contact.html",
        {"request": request}
    )
# ---------------------------
# ADMIN AUTH ROUTES
# ---------------------------
@app.get("/admin/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})


@app.post("/admin/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = next(get_db())
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin or not verify_password(password, admin.hashed_password):
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Invalid credentials"}
        )

    token = create_access_token({"sub": admin.username})
    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, path="/")
    return response


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, admin: Admin = Depends(get_current_admin_cookie)):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "admin": admin})

from sqlalchemy.orm import Session
from fastapi import Depends

@app.get("/create-admin-once")
def create_admin_once(db: Session = Depends(get_db)):
    existing = db.query(Admin).filter(Admin.username == "admin").first()
    if existing:
        return {"message": "Admin already exists"}

    hashed_password = get_password_hash("StrongPassword123")
    admin = Admin(username="admin", hashed_password=hashed_password)
    db.add(admin)
    db.commit()
    return {"message": "Admin created successfully"}



# ---------------------------
# ADMIN VIDEO MANAGEMENT
# ---------------------------
@app.post("/admin/video", response_model=VideoResponse, status_code=201)
def create_video(request: VideoCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_cookie)):
    youtube_id = extract_youtube_id(request.youtube_link)
    if not youtube_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube link")
    thumbnail_url = f"https://img.youtube.com/vi/{youtube_id}/hqdefault.jpg"
    new_video = Video(
        title=request.title,
        youtube_link=request.youtube_link,
        youtube_id=youtube_id,
        thumbnail_url=thumbnail_url
    )
    db.add(new_video)
    db.commit()
    db.refresh(new_video)
    return new_video


@app.get("/admin/videos/all", response_model=list[VideoResponse])
def get_all_videos(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_cookie)):
    return db.query(Video).order_by(desc(Video.published_at)).all()

# Fetch only published videos
@app.get("/videos", response_model=list[VideoResponse])
def get_published_videos(db: Session = Depends(get_db)):
    videos = (
        db.query(Video)
        .order_by(desc(Video.published_at))  # Sort newest first
        .all()
    )
    return videos

@app.put("/admin/video/{id}", response_model=VideoResponse)
def update_video(id: int, request: VideoCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_cookie)):
    video = db.query(Video).filter(Video.id == id)
    if not video.first():
        raise HTTPException(status_code=404, detail="Video not found")

    youtube_id = extract_youtube_id(request.youtube_link)
    thumbnail_url = f"https://img.youtube.com/vi/{youtube_id}/hqdefault.jpg"

    video.update(
        {
            "title": request.title,
            "youtube_link": request.youtube_link,
            "youtube_id": youtube_id,
            "thumbnail_url": thumbnail_url
        },
        synchronize_session=False
    )
    db.commit()
    return video.first()


@app.delete("/admin/video/{id}", status_code=204)
def delete_video(id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_cookie)):
    video = db.query(Video).filter(Video.id == id)
    if not video.first():
        raise HTTPException(status_code=404, detail="Video not found")
    video.delete(synchronize_session=False)
    db.commit()
    return None


# ---------------------------
# ADMIN LOGIN 
# ---------------------------

@app.get("/admin/change-password", response_class=HTMLResponse)
def change_password_form(request: Request, admin: Admin = Depends(get_current_admin_cookie)):
    return templates.TemplateResponse("admin/change_password.html", {"request": request, "admin": admin})


@app.post("/admin/change-password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin_cookie)
):
    if not verify_password(current_password, admin.hashed_password):
        return templates.TemplateResponse(
            "admin/change_password.html",
            {"request": request, "error": "Current password is incorrect", "admin": admin}
        )

    if new_password != confirm_password:
        return templates.TemplateResponse(
            "admin/change_password.html",
            {"request": request, "error": "New passwords do not match", "admin": admin}
        )

    admin.hashed_password = get_password_hash(new_password)
    db.commit()

    return templates.TemplateResponse(
        "admin/change_password.html",
        {"request": request, "success": "Password updated successfully!", "admin": admin}
    )

from fastapi import Form

# GET: Show the change password form
@app.get("/admin/change-password", response_class=HTMLResponse)
def change_password_form(request: Request, admin: Admin = Depends(get_current_admin_cookie)):
    return templates.TemplateResponse("admin/change_password.html", {"request": request, "admin": admin})


# POST: Handle password update
@app.post("/admin/change-password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin_cookie)
):
    # Verify current password
    if not verify_password(current_password, admin.hashed_password):
        return templates.TemplateResponse(
            "admin/change_password.html",
            {"request": request, "error": "Current password is incorrect", "admin": admin}
        )

    # Check new password match
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "admin/change_password.html",
            {"request": request, "error": "New passwords do not match", "admin": admin}
        )

    # Update password
    admin.hashed_password = get_password_hash(new_password)
    db.commit()

    return templates.TemplateResponse(
        "admin/change_password.html",
        {"request": request, "success": "Password updated successfully!", "admin": admin}
    )

@app.get("/admin/logout")
def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("access_token")
    return response

# ---------------------------
# CONTACT US
# ---------------------------
@app.post("/contact")
def submit_contact(
    contact: ContactMessageCreate,
    db: Session = Depends(get_db)
):
    new_message = ContactMessage(
        name=contact.name,
        email=contact.email,
        message=contact.message
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return {"detail": "Message submitted successfully"}

# Serve the HTML page
@app.get("/admin/contact-messages", response_class=HTMLResponse)
def admin_contact_messages(request: Request, admin: Admin = Depends(get_current_admin_cookie)):
    return templates.TemplateResponse("admin/contact_messages.html", {"request": request})

# Serve JSON data for JS
@app.get("/admin/contact-messages-data")
def get_messages_data(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_cookie)):
    return db.query(ContactMessage).order_by(desc(ContactMessage.created_at)).all()

# Optional: delete a message
@app.delete("/admin/contact-messages/{message_id}")
def delete_message(message_id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_cookie)):
    msg = db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    db.delete(msg)
    db.commit()
    return {"detail": "Message deleted successfully"}



def send_email(to_email: str, subject: str, body: str):
    # Configure your SMTP settings here
    SMTP_SERVER = "smtp.gmail.com"  # e.g., smtp.gmail.com
    SMTP_PORT = 587
    SMTP_USERNAME = "gichobijackson@gmail.com"
    SMTP_PASSWORD = "zfml inny spgm awtt "

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USERNAME
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()  # secure the connection
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        print(f"Email sent to {to_email}")

# Route to send reply
@app.post("/admin/contact-messages/reply")
def reply_message(
    background_tasks: BackgroundTasks,
    admin: Admin = Depends(get_current_admin_cookie),
    email: str = Form(...),
    message: str = Form(...)
):
    subject = "Reply from End Time Ministry"
    background_tasks.add_task(send_email, email, subject, message)
    return {"detail": "Reply sent successfully"}
