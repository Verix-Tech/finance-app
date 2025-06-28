from fastapi import APIRouter
from schemas.responses import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Endpoint for health checks."""
    return {"status": "healthy"}
