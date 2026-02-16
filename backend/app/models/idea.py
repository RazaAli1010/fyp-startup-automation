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

    # User-provided inputs (simplified)
    target_customer_type = Column(String, nullable=False)
    geography = Column(String, nullable=False)

    # Legacy columns — nullable with defaults for backward compatibility.
    # New ideas will have these set to defaults; old ideas retain original values.
    customer_size = Column(String, nullable=True, default="SMB")
    revenue_model = Column(String, nullable=True, default="Subscription")
    pricing_estimate = Column(Float, nullable=True, default=49.0)
    estimated_cac = Column(Float, nullable=True, default=0.0)
    estimated_ltv = Column(Float, nullable=True, default=0.0)
    team_size = Column(Integer, nullable=True, default=5)
    tech_complexity = Column(Float, nullable=True, default=0.5)
    regulatory_risk = Column(Float, nullable=True, default=0.5)

    # Inferred by OpenAI during evaluation (persisted so MR agent can reuse)
    inferred_revenue_model = Column(String, nullable=True, default=None)
    inferred_tech_level = Column(String, nullable=True, default=None)
    inferred_reg_level = Column(String, nullable=True, default=None)
    inferred_problem_keywords = Column(Text, nullable=True, default=None)
    inferred_market_keywords = Column(Text, nullable=True, default=None)

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Persisted after evaluation — NULL means "not evaluated yet"
    final_viability_score = Column(Float, nullable=True, default=None)
    evaluation_report_json = Column(Text, nullable=True, default=None)

    owner = relationship("User", back_populates="ideas")
