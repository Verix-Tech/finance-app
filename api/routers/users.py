from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from auth.auth import User
from dependencies.auth import get_current_user
from dependencies.database import get_database_service
from services.celery_service import CeleryService
from services.database_service import DatabaseService
from schemas.requests import CreateUserRequest, ClientExistsRequest, GetUserInfoRequest
from schemas.responses import SuccessResponse, ErrorResponse
from config.settings import settings
from errors.errors import SubscriptionError, ClientNotExistsError
from sqlalchemy.exc import DataError, ProgrammingError, StatementError
import logging

router = APIRouter(prefix="/users", tags=["Users"])

logger = logging.getLogger(__name__)


@router.post("/create", response_model=SuccessResponse)
async def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Create or update a user."""
    try:
        result = db_service.create_user(
            platform_id=request.platform_id,
            platform_name=request.platform_name,
            name=request.name,
            phone=request.phone,
        )

        return SuccessResponse(
            status=settings.RESPONSE_SUCCESS,
            data=result,
            message=f"Client '{request.platform_id}' updated!",
        )

    except DataError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=settings.SYNTAX_ERROR
        )
    except (ProgrammingError, StatementError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=settings.DATABASE_ERROR
        )
    except SubscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=settings.NO_SUBSCRIPTION
        )


@router.post("/exists", response_model=SuccessResponse)
async def client_exists(
    request: ClientExistsRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Check if a client exists."""
    try:
        exists = db_service.check_client_exists(request.platform_id)

        if exists:
            return SuccessResponse(
                status=settings.RESPONSE_SUCCESS,
                data={"platform_id": request.platform_id},
                message=f"Client '{request.platform_id}' exists!",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=settings.CLIENT_NOT_EXISTS
            )

    except ClientNotExistsError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=settings.CLIENT_NOT_EXISTS
        )
    except DataError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=settings.SYNTAX_ERROR
        )
    except (ProgrammingError, StatementError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=settings.DATABASE_ERROR
        )
    except SubscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=settings.NO_SUBSCRIPTION
        )


@router.post("/get-user-info", response_model=SuccessResponse)
async def get_user_info(
    request: GetUserInfoRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Get user info."""
    try:
        inserter = db_service.get_inserter(request.platform_id)
        client_id = inserter.client_id_uuid
        
        result = CeleryService.get_user_info(client_id=client_id)

        if result["status"] == "success":
            return SuccessResponse(
                status=settings.RESPONSE_SUCCESS,
                data=result["data"],
                message=result["message"],
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )