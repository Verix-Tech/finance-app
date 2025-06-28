#!/usr/bin/env python3
"""
Test script to verify Redis connection and Celery configuration.
Run this script to debug connection issues between API and Celery.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import os
import logging
from celery import Celery

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_redis_connection():
    """Test Redis connection and Celery configuration."""

    # Get Redis configuration
    redis_server = os.getenv("REDIS_SERVER", "redis://localhost:6379")
    logger.info(f"Testing Redis connection with: {redis_server}")

    try:
        # Test basic Redis connection
        import redis

        r = redis.from_url(redis_server)
        if r is None:
            logger.error("❌ Failed to create Redis connection")
            return False
        r.ping()
        logger.info("✅ Redis connection successful")

        # Import the existing Celery app from workers.main
        try:
            from workers.main import app

            logger.info("✅ Successfully imported Celery app from workers.main")
        except ImportError as e:
            logger.error(f"❌ Failed to import Celery app from workers.main: {e}")
            return False

        # Check if any workers are active
        try:
            active_workers = app.control.inspect().active()
            if active_workers:
                logger.info(f"✅ Found {len(active_workers)} active worker(s)")
            else:
                logger.warning(
                    "⚠️  No active workers found. Task will timeout unless a worker is started."
                )
                logger.info("💡 To start a worker, run: make start_celery")
        except Exception as e:
            logger.warning(f"⚠️  Could not check worker status: {e}")

        # Test with a simple test task
        try:
            from tests.test_tasks import simple_test_task

            logger.info("✅ Successfully imported simple_test_task")

            # Send a simple test task
            result = simple_test_task.delay()
            logger.info(f"✅ Task sent successfully with ID: {result.id}")

            # Try to get result (this will timeout if no worker is running)
            try:
                task_result = result.get(timeout=10)
                logger.info(f"✅ Task result received: {task_result}")
            except Exception as e:
                logger.error(
                    f"❌ Task execution failed (likely no worker running): {e}"
                )
                logger.info(
                    "💡 To fix this, start a Celery worker with: make start_celery"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Failed to test with simple_test_task: {e}")
            return False

        return True

    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_redis_connection()
    sys.exit(0 if success else 1)
