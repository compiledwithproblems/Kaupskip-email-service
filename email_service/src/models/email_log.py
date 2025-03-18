from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from ..database import Base

class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email_to = Column(String, nullable=False)
    email_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)