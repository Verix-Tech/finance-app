from fastapi import APIRouter, Depends, HTTPException, status

from auth.auth import User
from dependencies.auth import get_current_user
from dependencies.database import get_database_service
from services.database_service import DatabaseService
from schemas.requests import GrantSubscriptionRequest, RevokeSubscriptionRequest
from schemas.responses import SuccessResponse
from config.settings import settings
from errors.errors import SubscriptionError, ClientNotExistsError
from sqlalchemy.exc import DataError, ProgrammingError, StatementError

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post("/grant", response_model=SuccessResponse)
async def grant_subscription(
    request: GrantSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service)
):
    """Grant a subscription to a user."""
    try:
        result = db_service.grant_subscription(
            platform_id=request.platform_id,
            subscription_months=request.subscriptionMonths
        )
        
        return SuccessResponse(
            status=settings.RESPONSE_SUCCESS,
            data=result,
            message=f"Subscription created for client: {request.platform_id}!"
        )
    
    except ClientNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=settings.CLIENT_NOT_EXISTS
        )
    except DataError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=settings.SYNTAX_ERROR
        )
    except (ProgrammingError, StatementError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=settings.DATABASE_ERROR
        )
    except SubscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=settings.NO_SUBSCRIPTION
        )


@router.post("/revoke", response_model=SuccessResponse)
async def revoke_subscription(
    request: RevokeSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service)
):
    """Revoke a user's subscription."""
    try:
        result = db_service.revoke_subscription(
            platform_id=request.platform_id
        )
        
        return SuccessResponse(
            status=settings.RESPONSE_SUCCESS,
            data=result,
            message=f"Subscription revoked for client: {request.platform_id}!"
        )
    
    except ClientNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=settings.CLIENT_NOT_EXISTS
        )
    except DataError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=settings.SYNTAX_ERROR
        )
    except (ProgrammingError, StatementError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=settings.DATABASE_ERROR
        )
    except SubscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=settings.NO_SUBSCRIPTION
        ) 