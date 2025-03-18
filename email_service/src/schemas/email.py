from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class EmailVerificationRequest(BaseModel):
    user_id: str
    email: EmailStr

class EmailVerificationResponse(BaseModel):
    success: bool
    message: str

class EmailLogResponse(BaseModel):
    id: str
    email_to: str
    email_type: str
    status: str
    created_at: datetime
    sent_at: Optional[datetime]