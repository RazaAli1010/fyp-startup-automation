import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, CHAR


from ..database import Base


class GUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses CHAR(36) to store UUIDs as strings, compatible with all backends
    including SQLite.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value


class Idea(Base):
    __tablename__ = "ideas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    startup_name = Column(String, nullable=False)
    one_line_description = Column(Text, nullable=False)
    industry = Column(String, nullable=False)

    target_customer_type = Column(String, nullable=False)
    geography = Column(String, nullable=False)
    customer_size = Column(String, nullable=False)

    revenue_model = Column(String, nullable=False)
    pricing_estimate = Column(Float, nullable=False)

    estimated_cac = Column(Float, nullable=False)
    estimated_ltv = Column(Float, nullable=False)
    team_size = Column(Integer, nullable=False)
    tech_complexity = Column(Float, nullable=False)
    regulatory_risk = Column(Float, nullable=False)

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Persisted after evaluation — NULL means "not evaluated yet"
    final_viability_score = Column(Float, nullable=True, default=None)
    evaluation_report_json = Column(Text, nullable=True, default=None)

    owner = relationship("User", back_populates="ideas")
