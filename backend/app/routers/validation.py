
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from ..agents.idea_validation import validation_graph, ValidationState
from ..schemas.validation import ValidationRequest, ValidationResponse


router = APIRouter(
    prefix="/validate",
    tags=["Validation"],
    responses={
        500: {"description": "Internal server error during validation"}
    }
)


@router.post(
    "",
    response_model=ValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a Startup Idea",
    
    response_description="Validation results including score, analysis, and recommendations"
)
async def validate_idea(request: ValidationRequest) -> ValidationResponse:
    
    try:
        # Prepare initial state for the graph
        initial_state: ValidationState = {
            "idea_input": request.idea,
            "reddit_sentiment": None,
            "trends_data": None,
            "competitor_analysis": None,
            "final_verdict": None,
            "processing_errors": [],
        }
        
    
        result = await validation_graph.ainvoke(initial_state)
        
        # Build response from graph result
        response = ValidationResponse(
            success=True,
            idea_input=result["idea_input"],
            reddit_sentiment=result.get("reddit_sentiment"),
            trends_data=result.get("trends_data"),
            competitor_analysis=result.get("competitor_analysis"),
            final_verdict=result.get("final_verdict"),
            processing_errors=result.get("processing_errors", []),
        )
        
        return response
        
    except Exception as e:
        print(f"Validation error: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health Check",
    description="Check if the validation service is running",
    response_description="Health status"
)
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "idea-validation"}

