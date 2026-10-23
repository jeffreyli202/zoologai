from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return a simple status payload so clients can verify the API is up."""
    return {"status": "ok"}
