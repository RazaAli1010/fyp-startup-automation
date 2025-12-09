from typing import Optional
from pydantic import BaseModel, Field


class ValidationRequest(BaseModel):
    """Request body for the /validate endpoint."""
    
    idea: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The startup idea to validate. Be descriptive for better results.",
        alias="idea_input",  # Accept both "idea" and "idea_input" from JSON
        examples=[
            "An AI-powered tool that helps small business owners automate their social media content creation and scheduling",
            "A marketplace connecting local farmers directly with restaurants, eliminating middlemen and ensuring fresh produce delivery within 24 hours"
        ]
    )
    
    class Config:
        # Allow field to be populated by either "idea" or "idea_input"
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "idea": "An AI-powered tool that helps small business owners automate their social media content creation and scheduling"
            }
        }


