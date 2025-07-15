from fastapi import APIRouter, Depends, HTTPException, status
from schemas.requests import CreateCardRequest, ListAllCardsRequest
from schemas.responses import ListAllCardsResponse
from services.database_service import DatabaseService
from services.celery_service import CeleryService
from dependencies.auth import get_current_user
from dependencies.database import get_database_service
from auth.auth import User
from schemas.responses import SuccessResponse
from config.settings import settings

router = APIRouter(prefix="/cards", tags=["Cards"])


@router.post("/create", response_model=SuccessResponse)
async def create_card(
    request: CreateCardRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Endpoint for creating a card."""
    try:
        db_service.create_card(platform_id=request.platform_id, data=request.model_dump())

        return SuccessResponse(
            status=settings.RESPONSE_SUCCESS,
            data=request.model_dump(),
                message=f"Card created for client: {request.platform_id}!",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=settings.DATABASE_ERROR,
        )
    
@router.post("/list-all", response_model=SuccessResponse)
async def list_all_cards(
    request: ListAllCardsRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Endpoint for listing all cards."""
    inserter = db_service.get_inserter(request.platform_id)
    client_id = inserter.client_id_uuid

    try:
        cards = CeleryService.list_all_cards(client_id=client_id, date=request.date)
        return SuccessResponse(
            status=settings.RESPONSE_SUCCESS,
            data=cards,
            message=f"Cards list retrieved for client: {request.platform_id}!",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=settings.DATABASE_ERROR,
        )
        
