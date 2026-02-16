import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from ..database import Base
from .idea import GUID


class LegalDocument(Base):
    __tablename__ = "legal_documents"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    idea_id = Column(GUID(), ForeignKey("ideas.id"), nullable=False)
    document_type = Column(String(64), nullable=False)  # nda | founder_agreement | privacy_policy | terms_of_service
    jurisdiction = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="pending")  # pending | generated | failed
    document_json = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", backref="legal_documents")
    idea = relationship("Idea", backref="legal_documents")
