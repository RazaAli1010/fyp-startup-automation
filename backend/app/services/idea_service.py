from typing import Optional

from sqlalchemy.orm import Session

from ..models.idea import Idea
from ..schemas.idea_schema import StartupIdeaInput


def create_idea(db: Session, payload: StartupIdeaInput, user_id: Optional[object] = None) -> Idea:
    """Persist a validated startup idea and return the ORM instance."""
    idea = Idea(
        startup_name=payload.startup_name,
        one_line_description=payload.one_line_description,
        industry=payload.industry,
        target_customer_type=payload.target_customer_type,
        geography=payload.geography,
        customer_size=payload.customer_size,
        revenue_model=payload.revenue_model,
        pricing_estimate=payload.pricing_estimate,
        estimated_cac=payload.estimated_cac,
        estimated_ltv=payload.estimated_ltv,
        team_size=payload.team_size,
        tech_complexity=payload.tech_complexity,
        regulatory_risk=payload.regulatory_risk,
        user_id=user_id,
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea
