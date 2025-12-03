from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Simple health check to verify the API is running.
    Useful for load balancers and container orchestration.
    """
    return {"status": "healthy", "service": "meeting-notes-api"}
