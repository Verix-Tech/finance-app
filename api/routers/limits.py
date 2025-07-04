from fastapi import APIRouter, Depends, HTTPException, status

from auth.auth import User
from dependencies.auth import get_current_user
from dependencies.database import get_database_service
from services.database_service import DatabaseService
from services.celery_service import CeleryService
from schemas.requests import CreateLimitRequest, LimitCheckRequest, LimitCheckAllRequest
from schemas.responses import SuccessResponse
from config.settings import settings
from errors.errors import SubscriptionError, ClientNotExistsError
from sqlalchemy.exc import DataError, ProgrammingError, StatementError

router = APIRouter(prefix="/limits", tags=["Limits"])


@router.post("/create", response_model=SuccessResponse)
async def create_limit(
    request: CreateLimitRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Create a new limit."""
    try:
        result = db_service.create_limit(
            platform_id=request.platform_id,
            category_id=request.category_id,
            limit_value=request.limit_value,
        )

        return SuccessResponse(
            status=settings.RESPONSE_SUCCESS,
            data=result,
            message=f"Limit created for client: {request.platform_id}!",
        )

    except ClientNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=settings.CLIENT_NOT_EXISTS
        )
    except (ProgrammingError, StatementError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=settings.DATABASE_ERROR
        )
    except SubscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=settings.NO_SUBSCRIPTION
        )


@router.post("/check", response_model=SuccessResponse)
async def limit_check_task(
    request: LimitCheckRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Check if the limit is exceeded."""
    try:
        # Get client_id from database service
        inserter = db_service.get_inserter(request.platform_id)
        client_id = inserter.client_id_uuid

        # Execute Celery task
        result = CeleryService.check_limit(
            client_id=client_id, category_id=request.category_id
        )

        return SuccessResponse(
            status=settings.RESPONSE_SUCCESS,
            data=result,
            message="Limit check completed",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=settings.SYNTAX_ERROR
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

@router.post("/check-all", response_model=SuccessResponse)
async def limit_check_all_task(
    request: LimitCheckAllRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Check if the limit is exceeded for all categories."""
    try:
        # Get client_id from database service
        inserter = db_service.get_inserter(request.platform_id)
        client_id = inserter.client_id_uuid

        # Execute Celery task
        result = CeleryService.check_limit_all(
            client_id=client_id, filter=request.filter
        )

        return SuccessResponse(
            status=settings.RESPONSE_SUCCESS,
            data=result,
            message="Limit check completed",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=settings.SYNTAX_ERROR
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
