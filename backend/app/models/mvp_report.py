import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from ..database import Base
from .idea import GUID


class MVPReport(Base):
    __tablename__ = "mvp_reports"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    idea_id = Column(GUID(), ForeignKey("ideas.id"), nullable=False, unique=True)
    status = Column(String(32), nullable=False, default="pending")  # pending | generated | failed
    blueprint_json = Column(Text, nullable=True)  # JSON string (compatible with SQLite & PG)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", backref="mvp_reports")
    idea = relationship("Idea", backref="mvp_report")
