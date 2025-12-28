from pydantic import BaseModel
from datetime import datetime


# Input from the frontend
class VideoCreate(BaseModel):
    title: str
    youtube_link: str

# Response to the frontend
class VideoResponse(BaseModel):
    id: int
    title: str
    youtube_link: str
    youtube_id: str
    thumbnail_url: str
    published: bool  # New field
    published_at: datetime  # New field

    class Config:
        orm_mode = True

class ContactMessageCreate(BaseModel):
    name: str
    email: str
    message: str