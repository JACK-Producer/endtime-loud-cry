from sqlalchemy import Column, Integer, String, DateTime, Text
from database import Base
from datetime import datetime
from sqlalchemy import Boolean

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    youtube_link = Column(String, nullable=False)
    youtube_id = Column(String, nullable=False)
    thumbnail_url = Column(String, nullable=False)

    published = Column(Boolean, default=False)  # NEW: track published status
    published_at = Column(DateTime, default=datetime.utcnow)

            

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)