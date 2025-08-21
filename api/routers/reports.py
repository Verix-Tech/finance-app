from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from auth.auth import User
from dependencies.auth import get_current_user
from dependencies.database import get_database_service
from services.database_service import DatabaseService
from services.celery_service import CeleryService
from schemas.requests import GenerateReportRequest, CheckTransactionRequest
from schemas.responses import ListTransactionResponse, SuccessResponse
from config.settings import settings

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/generate")
async def generate_report(
    request: GenerateReportRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Generate extract for a client."""
    try:
        # Get client_id from database service
        inserter = db_service.get_inserter(request.platform_id)
        client_id = inserter.client_id_uuid

        # Generate report using Celery service
        result_stream = CeleryService.generate_report(
            client_id=client_id,
            start_date=request.start_date,
            end_date=request.end_date,
            days_before=request.days_before,
            aggr=request.aggr,
            filter=request.filter,
        )

        # Return streaming response
        return StreamingResponse(
            iter([result_stream.getvalue()]),
            headers={"Content-Disposition": f"attachment; filename=extract.json"},
            media_type="application/json",
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
    
@router.post("/check", response_model=SuccessResponse)
async def check_transaction(
    request: CheckTransactionRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Check transaction."""
    try:
        # Get client_id from database service
        inserter = db_service.get_inserter(request.platform_id)
        client_id = inserter.client_id_uuid

        # Generate report using Celery service
        result = CeleryService.check_transaction(
            client_id=client_id,
            transaction_id=str(request.transaction_id),
        )

        # Return streaming response
        return SuccessResponse(
            status=settings.RESPONSE_SUCCESS,
            data=result,
            message=f"Transaction checked for client: {request.platform_id}!",
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

