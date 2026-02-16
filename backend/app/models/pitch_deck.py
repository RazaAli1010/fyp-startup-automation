import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from ..database import Base
from .idea import GUID


class PitchDeck(Base):
    __tablename__ = "pitch_decks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    idea_id = Column(GUID(), ForeignKey("ideas.id"), nullable=False, unique=True)
    title = Column(String(512), nullable=False, default="Pitch Deck")
    status = Column(String(32), nullable=False, default="pending")  # pending | completed | failed
    provider = Column(String(32), nullable=False, default="alai")
    deck_json = Column(Text, nullable=True)  # JSON string (compatible with SQLite & PG)
    generation_id = Column(String(256), nullable=True)  # Alai generation ID
    view_url = Column(String(1024), nullable=True)  # Shareable presentation link
    pdf_url = Column(String(1024), nullable=True)  # PDF export link
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", backref="pitch_decks")
    idea = relationship("Idea", backref="pitch_deck")
