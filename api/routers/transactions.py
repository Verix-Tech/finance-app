from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from auth.auth import User
from dependencies.auth import get_current_user
from dependencies.database import get_database_service
from services.database_service import DatabaseService
from services.celery_service import CeleryService
from schemas.requests import (
    CreateTransactionRequest,
    UpdateTransactionRequest,
    DeleteTransactionRequest,
)
from schemas.responses import SuccessResponse
from config.settings import settings
from errors.errors import (
    SubscriptionError,
    ClientNotExistsError,
    TransactionNotExistsError,
)
from sqlalchemy.exc import DataError, ProgrammingError, StatementError
from utils.utils import get_limits

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/create", response_model=SuccessResponse)
async def create_transaction(
    request: CreateTransactionRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Create a new transaction."""
    try:
        result = db_service.create_transaction(
            platform_id=request.platform_id,
            transaction_revenue=request.transaction_revenue,
            transaction_timestamp=request.transaction_timestamp,
            payment_method_id=request.payment_method_id,
            payment_description=request.payment_description,
            payment_category_id=request.payment_category_id,
            transaction_type=request.transaction_type,
        )

        # Get limit value if category is provided
        if request.payment_category_id:
            limit_value = CeleryService.get_limit_value(
                client_id=result["platform_id"], category_id=request.payment_category_id
            )
            if limit_value > 0:
                result["limit_value"] = limit_value

        return SuccessResponse(
            status=settings.RESPONSE_SUCCESS,
            data=result,
            message=f"Transaction created for client: {request.platform_id}!",
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


@router.post("/update", response_model=SuccessResponse)
async def update_transaction(
    request: UpdateTransactionRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Update a transaction."""
    try:
        # Filter out None values and special fields
        update_data = {
            k: v
            for k, v in request.dict().items()
            if k not in ["platform_id", "transactionId"] and v is not None
        }

        result = db_service.update_transaction(
            platform_id=request.platform_id,
            transaction_id=request.transactionId,
            **update_data,
        )

        return SuccessResponse(
            status=settings.RESPONSE_SUCCESS,
            data=result,
            message=f"Transaction updated for client: {request.platform_id}!",
        )

    except ClientNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=settings.CLIENT_NOT_EXISTS
        )
    except TransactionNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=settings.TRANSACTION_NOT_EXISTS,
        )
    except (ProgrammingError, StatementError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=settings.DATABASE_ERROR
        )
    except SubscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=settings.NO_SUBSCRIPTION
        )


@router.post("/delete", response_model=SuccessResponse)
async def delete_transaction(
    request: DeleteTransactionRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Delete a transaction."""
    try:
        # Filter out None values
        delete_data = {
            k: v
            for k, v in request.dict().items()
            if k != "platform_id" and v is not None
        }

        result = db_service.delete_transaction(
            platform_id=request.platform_id, **delete_data
        )

        return SuccessResponse(
            status=settings.RESPONSE_SUCCESS,
            data=result,
            message=f"Transaction deleted for client: {request.platform_id}!",
        )

    except ClientNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=settings.CLIENT_NOT_EXISTS
        )
    except TransactionNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=settings.TRANSACTION_NOT_EXISTS,
        )
    except (ProgrammingError, StatementError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=settings.DATABASE_ERROR
        )
    except SubscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=settings.NO_SUBSCRIPTION
        )
