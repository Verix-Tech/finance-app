from typing import Generator
from services.database_service import DatabaseService

# Global database service instance
db_service = DatabaseService()


def get_database_service() -> DatabaseService:
    """Dependency to get database service instance."""
    return db_service


def get_database_session() -> Generator:
    """Dependency to get database session."""
    session = db_service.get_session()
    try:
        yield session
    finally:
        session.close()
