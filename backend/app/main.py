import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers.validation import router as validation_router


# Load environment variables from .env file
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    
    # Startup
    print("Starting Multi-Agent AI System")
    print(f"   OpenAI Key:  {' Configured' if os.getenv('OPENAI_API_KEY') else ' Not set (using mock data)'}")
    print(f"   Tavily Key:  {' Configured' if os.getenv('TAVILY_API_KEY') else ' Not set (using mock data)'}")
    print(f"   Exa.ai Key:  {' Configured' if os.getenv('EXA_API_KEY') else ' Not set (using mock data)'}")
    print("   Ready to validate startup ideas!")
    
    yield  
    
    print("Shutting down Multi-Agent AI System")


app = FastAPI(
    title="Multi-Agent AI System for Automating Startup Workflows",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Next.js dev server
        "http://127.0.0.1:3000",      # Alternative localhost
        "http://localhost:3001",      # Alternative port
    
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

app.include_router(validation_router)

@app.get(
    "/",
    summary="API Root",
    description="Welcome endpoint with API information",
    tags=["General"]
)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Startup AI Validator",
        "version": "0.1.0",
        "description": "AI-powered startup idea validation",
        "docs": "/docs",
        "endpoints": {
            "validate": "POST /validate - Validate a startup idea",
            "health": "GET /validate/health - Service health check"
        }
    }


@app.get(
    "/health",
    summary="Global Health Check",
    description="Check if the API server is running",
    tags=["General"]
)
async def health():
    """Global health check endpoint."""
    return {
        "status": "healthy",
        "service": "startup-ai-validator",
        "version": "0.1.0"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("DEBUG", "true").lower() == "true",
    )

