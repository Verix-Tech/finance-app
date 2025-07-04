import io
import logging
from typing import Dict, Any, Optional
from workers.main import generate_extract, limit_check, limit_check_all
from utils.utils import get_limits
from config.settings import settings

logger = logging.getLogger(__name__)


class CeleryService:
    """Manages Celery task operations."""

    @staticmethod
    def generate_report(
        client_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days_before: Optional[int] = None,
        aggr: Optional[str] = None,
        filter: Optional[str] = None,
    ) -> io.StringIO:
        """Generate extract for a client."""
        try:
            # Check if Redis server is configured
            if not settings.REDIS_SERVER:
                logger.error("REDIS_SERVER environment variable not set")
                raise ValueError("Redis server not configured")

            logger.info(
                f"Executing Celery task with Redis broker: {settings.REDIS_SERVER}"
            )

            # Execute the Celery task synchronously
            result = generate_extract.apply(
                kwargs={
                    "client_id": client_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "days_before": days_before,
                    "aggr": aggr,
                    "filter": filter,
                }
            ).get()  # This will wait for the task to complete

            logger.info("Celery task completed successfully")

            # Create streaming response with the result
            return io.StringIO(result)

        except Exception as e:
            logger.error(f"Failed to execute Celery task: {e}")
            raise e

    @staticmethod
    def check_limit(client_id: str, category_id: str) -> Dict[str, Any]:
        """Check if the limit is exceeded."""
        try:
            # Check if Redis server is configured
            if not settings.REDIS_SERVER:
                logger.error("REDIS_SERVER environment variable not set")
                raise ValueError("Redis server not configured")

            logger.info(
                f"Executing Celery task with Redis broker: {settings.REDIS_SERVER}"
            )

            # Execute the Celery task synchronously
            result = limit_check.apply(
                kwargs={"client_id": client_id, "category_id": category_id}
            ).get()  # This will wait for the task to complete

            logger.info("Celery task completed successfully")

            return result

        except Exception as e:
            logger.error(f"Failed to execute Celery task: {e}")
            raise e
        
    @staticmethod
    def check_limit_all(client_id: str, filter: Optional[dict] = {}) -> Dict[str, Any]:
        """Check if the limit is exceeded for all categories."""
        try:
            # Check if Redis server is configured
            if not settings.REDIS_SERVER:
                logger.error("REDIS_SERVER environment variable not set")
                raise ValueError("Redis server not configured")
            
            logger.info(
                f"Executing Celery task with Redis broker: {settings.REDIS_SERVER}"
            )

            # Execute the Celery task synchronously
            result = limit_check_all.apply(
                kwargs={"client_id": client_id, "filter": filter}
            ).get()  # This will wait for the task to complete

            logger.info("Celery task completed successfully")

            return result

        except Exception as e:
            logger.error(f"Failed to execute Celery task: {e}")
            raise e

    @staticmethod
    def get_limit_value(client_id: str, category_id: str) -> float:
        """Get limit value for a client and category."""
        try:
            return get_limits(client_id=client_id, category_id=category_id)
        except Exception as e:
            logger.error(f"Failed to get limit value: {e}")
            raise e
