from typing import Optional

from sqlalchemy.orm import Session

from ..models.idea import Idea
from ..schemas.idea_schema import StartupIdeaInput
from ..constants import CUSTOMER_TYPE_TO_SIZE, DEFAULT_TEAM_SIZE


def create_idea(db: Session, payload: StartupIdeaInput, user_id: Optional[object] = None) -> Idea:
    """Persist a validated startup idea and return the ORM instance.

    Only the 5 user-provided fields are set from the payload.
    Legacy columns get sensible defaults. Inferred columns (tech_complexity,
    regulatory_risk, revenue_model) are populated later during evaluation.
    """
    idea = Idea(
        startup_name=payload.startup_name,
        one_line_description=payload.one_line_description,
        industry=payload.industry,
        target_customer_type=payload.target_customer_type,
        geography=payload.geography,
        # Defaults for legacy columns
        customer_size=CUSTOMER_TYPE_TO_SIZE.get(payload.target_customer_type, "SMB"),
        revenue_model="Subscription",       # placeholder — overwritten by inference
        pricing_estimate=49.0,              # placeholder — overwritten by inference
        estimated_cac=0.0,
        estimated_ltv=0.0,
        team_size=DEFAULT_TEAM_SIZE,
        tech_complexity=0.5,                # placeholder — overwritten by inference
        regulatory_risk=0.5,                # placeholder — overwritten by inference
        user_id=user_id,
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea
