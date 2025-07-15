from typing import Dict, Any
from database_manager.connector import DatabaseManager, DatabaseMonitor
from database_manager.inserter import DataInserter
from errors.errors import (
    SubscriptionError,
    ClientNotExistsError,
    TransactionNotExistsError,
)
from sqlalchemy.exc import DataError, ProgrammingError, StatementError
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    """Manages database operations and session handling."""

    def __init__(self):
        self.manager = DatabaseManager()
        self.manager.check_connection()
        self.monitor = DatabaseMonitor(self.manager)
        self.monitor.start()

    def get_session(self):
        """Get a new database session."""
        return self.manager.get_session()

    def get_inserter(self, platform_id: str) -> DataInserter:
        """Get a DataInserter instance for the given platform_id."""
        return DataInserter(self.get_session(), platform_id)

    def shutdown(self):
        """Clean up database resources."""
        self.manager.shutdown()

    def create_user(
        self, platform_id: str, platform_name: str, name: str, phone: str
    ) -> Dict[str, Any]:
        """Create or update a user."""
        try:
            inserter = self.get_inserter(platform_id)
            inserter.upsert_client(platform_name=platform_name, name=name, phone=phone)

            logger.info(
                f"User data inserted successfully for platform_id: {platform_id}"
            )
            return {
                "platform_id": platform_id,
                "platform_name": platform_name,
                "name": name,
                "phone": phone,
            }
        except (DataError, ProgrammingError, StatementError) as e:
            logger.error(f"Database error creating user: {e}")
            raise e
        except SubscriptionError as e:
            logger.error(f"Subscription error creating user: {e}")
            raise e

    def check_client_exists(self, platform_id: str) -> bool:
        """Check if a client exists."""
        try:
            inserter = self.get_inserter(platform_id)
            return inserter._client_exists()
        except ClientNotExistsError:
            return False
        except (DataError, ProgrammingError, StatementError) as e:
            logger.error(f"Database error checking client: {e}")
            raise e

    def create_transaction(
        self, platform_id: str, **transaction_data
    ) -> Dict[str, Any]:
        """Create a new transaction."""
        try:
            inserter = self.get_inserter(platform_id)
            transaction_result = inserter.insert_transaction(**transaction_data)

            logger.info(
                f"Transaction created successfully for platform_id: {platform_id}"
            )
            return {
                "platform_id": platform_id,
                "transaction_id": transaction_result["transaction_id"],
                **transaction_data,
            }
        except ClientNotExistsError as e:
            logger.error(f"Client not exists error: {e}")
            raise e
        except (ProgrammingError, StatementError) as e:
            logger.error(f"Database error creating transaction: {e}")
            raise e
        except SubscriptionError as e:
            logger.error(f"Subscription error creating transaction: {e}")
            raise e

    def create_limit(
        self, platform_id: str, category_id: str, limit_value: float
    ) -> Dict[str, Any]:
        """Create a new limit."""
        try:
            inserter = self.get_inserter(platform_id)
            inserter.upsert_limit(category_id=category_id, limit_value=limit_value)

            logger.info(f"Limit created successfully for platform_id: {platform_id}")
            return {
                "platform_id": platform_id,
                "category_id": category_id,
                "limit_value": limit_value,
            }
        except ClientNotExistsError as e:
            logger.error(f"Client not exists error: {e}")
            raise e
        except (ProgrammingError, StatementError) as e:
            logger.error(f"Database error creating limit: {e}")
            raise e
        except SubscriptionError as e:
            logger.error(f"Subscription error creating limit: {e}")
            raise e

    def update_transaction(
        self, platform_id: str, transaction_id: int, **update_data
    ) -> Dict[str, Any]:
        """Update a transaction."""
        try:
            inserter = self.get_inserter(platform_id)
            inserter.update_transaction(transaction_id=transaction_id, data=update_data)

            logger.info(
                f"Transaction updated successfully for platform_id: {platform_id}"
            )
            return {
                "platform_id": platform_id,
                "transaction_id": transaction_id,
                **update_data,
            }
        except ClientNotExistsError as e:
            logger.error(f"Client not exists error: {e}")
            raise e
        except TransactionNotExistsError as e:
            logger.error(f"Transaction not exists error: {e}")
            raise e
        except (ProgrammingError, StatementError) as e:
            logger.error(f"Database error updating transaction: {e}")
            raise e
        except SubscriptionError as e:
            logger.error(f"Subscription error updating transaction: {e}")
            raise e

    def delete_transaction(self, platform_id: str, **delete_data) -> Dict[str, Any]:
        """Delete a transaction."""
        try:
            inserter = self.get_inserter(platform_id)
            inserter.delete_transaction(data=delete_data)

            logger.info(
                f"Transaction(s) deleted successfully for platform_id: {platform_id}"
            )
            return {"platform_id": platform_id, **delete_data}
        except ClientNotExistsError as e:
            logger.error(f"Client not exists error: {e}")
            raise e
        except TransactionNotExistsError as e:
            logger.error(f"Transaction not exists error: {e}")
            raise e
        except (ProgrammingError, StatementError) as e:
            logger.error(f"Database error deleting transaction: {e}")
            raise e
        except SubscriptionError as e:
            logger.error(f"Subscription error deleting transaction: {e}")
            raise e

    def grant_subscription(
        self, platform_id: str, subscription_months: int
    ) -> Dict[str, Any]:
        """Grant a subscription to a user."""
        try:
            inserter = self.get_inserter(platform_id)
            inserter.grant_subscription(subscription_months=subscription_months)

            logger.info(
                f"Subscription granted successfully for platform_id: {platform_id}"
            )
            return {
                "platform_id": platform_id,
                "subscription_months": subscription_months,
            }
        except ClientNotExistsError as e:
            logger.error(f"Client not exists error: {e}")
            raise e
        except (DataError, ProgrammingError, StatementError) as e:
            logger.error(f"Database error granting subscription: {e}")
            raise e
        except SubscriptionError as e:
            logger.error(f"Subscription error: {e}")
            raise e

    def revoke_subscription(self, platform_id: str) -> Dict[str, Any]:
        """Revoke a user's subscription."""
        try:
            inserter = self.get_inserter(platform_id)
            inserter.revoke_subscription()

            logger.info(
                f"Subscription revoked successfully for platform_id: {platform_id}"
            )
            return {"platform_id": platform_id}
        except ClientNotExistsError as e:
            logger.error(f"Client not exists error: {e}")
            raise e
        except (DataError, ProgrammingError, StatementError) as e:
            logger.error(f"Database error revoking subscription: {e}")
            raise e
        except SubscriptionError as e:
            logger.error(f"Subscription error: {e}")
            raise e
        
    def create_card(self, platform_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new card."""
        try:
            inserter = self.get_inserter(platform_id)
            inserter.insert_card(data=data)

            logger.info(f"Card created successfully for platform_id: {platform_id}")
            return {"platform_id": platform_id, **data}
        except ClientNotExistsError as e:
            logger.error(f"Client not exists error: {e}")
            raise e
        except (DataError, ProgrammingError, StatementError) as e:
            logger.error(f"Database error revoking subscription: {e}")
            raise e
        except SubscriptionError as e:
            logger.error(f"Subscription error: {e}")
            raise e
