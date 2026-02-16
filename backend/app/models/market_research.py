import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from ..database import Base
from .idea import GUID


class MarketResearch(Base):
    __tablename__ = "market_research"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    idea_id = Column(GUID(), ForeignKey("ideas.id"), nullable=False, unique=True)
    status = Column(String(32), nullable=False, default="pending")  # pending | completed | failed

    tam_min = Column(Float, nullable=True)
    tam_max = Column(Float, nullable=True)
    sam_min = Column(Float, nullable=True)
    sam_max = Column(Float, nullable=True)
    som_min = Column(Float, nullable=True)
    som_max = Column(Float, nullable=True)

    arpu_annual = Column(Float, nullable=True)
    growth_rate_estimate = Column(Float, nullable=True)
    demand_strength = Column(Float, nullable=True)

    assumptions_json = Column(Text, nullable=True)
    confidence_json = Column(Text, nullable=True)
    sources_json = Column(Text, nullable=True)
    competitors_json = Column(Text, nullable=True)
    competitor_count = Column(Float, nullable=True, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", backref="market_research")
    idea = relationship("Idea", backref="market_research")
