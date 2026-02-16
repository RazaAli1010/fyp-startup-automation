import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship

from ..database import Base
from .idea import GUID


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # nullable for Google users
    is_email_verified = Column(Boolean, default=False, nullable=False)
    auth_provider = Column(String, default="local", nullable=False)  # "local" | "google"
    created_at = Column(DateTime, default=datetime.utcnow)

    ideas = relationship("Idea", back_populates="owner", lazy="selectin")
