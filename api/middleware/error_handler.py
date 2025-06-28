import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, ProgrammingError, StatementError
from errors.errors import (
    SubscriptionError,
    ClientNotExistsError,
    TransactionNotExistsError,
)

logger = logging.getLogger(__name__)


async def error_handler_middleware(request: Request, call_next):
    """Middleware for centralized error handling."""
    try:
        response = await call_next(request)
        return response
    except (DataError, ProgrammingError, StatementError) as e:
        logger.error(f"Database error: {e}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": "Database error", "detail": str(e)},
        )
    except SubscriptionError as e:
        logger.error(f"Subscription error: {e}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "Subscription error", "detail": str(e)},
        )
    except ClientNotExistsError as e:
        logger.error(f"Client not exists error: {e}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Client not found", "detail": str(e)},
        )
    except TransactionNotExistsError as e:
        logger.error(f"Transaction not exists error: {e}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Transaction not found", "detail": str(e)},
        )
    except ValueError as e:
        logger.error(f"Value error: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid value", "detail": str(e)},
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error", "detail": str(e)},
        )
