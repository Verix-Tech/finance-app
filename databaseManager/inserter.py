import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from dateutil.relativedelta import relativedelta
from pytz import timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

from errors.errors import SubscriptionError, ClientNotExistsError, TransactionNotExistsError


class DataInserter:
    """Handles database operations for client subscriptions and transactions."""
    
    def __init__(self, session: Session, client_id: str) -> None:
        """
        Initialize the DataInserter.
        
        Args:
            session: SQLAlchemy database session
            client_id: The client identifier
        """
        self.session = session
        self.timezone = timezone("America/Sao_Paulo")
        self.client_id = client_id
        self.client_id_encrypted = self._encrypt_data(client_id)
        self.customers_table = "clients"
        self.transactions_table = "transactions"
        
        # Configure logging
        self._configure_logging()
    
    @staticmethod
    def _configure_logging() -> None:
        """Configure logging settings."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("app.log"),
                logging.StreamHandler()
            ]
        )
        # Reduce noise from libraries
        logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
        logging.getLogger("psycopg2").setLevel(logging.ERROR)
    
    @staticmethod
    def _encrypt_data(data: str) -> str:
        """
        Encrypt data using SHA-1 hashing.
        
        Args:
            data: The data to encrypt
            
        Returns:
            The hexadecimal digest of the hashed data
        """
        hasher = hashlib.sha1()
        hasher.update(data.encode("utf-8"))
        return hasher.hexdigest()
    
    def _execute_update(self, table: str, set_values: dict, where_condition: str) -> None:
        """
        Execute a parameterized UPDATE query.
        
        Args:
            table: The table to update
            set_values: Dictionary of column-value pairs to set
            where_condition: The WHERE clause condition
        """
        set_clause = ", ".join(f"{k} = :{k}" for k in set_values.keys())
        query = text(
            f"UPDATE {table} "
            f"SET {set_clause} "
            f"WHERE {where_condition}"
        )
        self.session.execute(query, set_values)
        self.session.commit()
    
    def _execute_insert(self, table: str, values: dict) -> None:
        """
        Execute a parameterized INSERT query.
        
        Args:
            table: The table to insert into
            values: Dictionary of column-value pairs to insert
        """
        columns = ", ".join(values.keys())
        placeholders = ", ".join(f":{k}" for k in values.keys())
        query = text(
            f"INSERT INTO {table} ({columns}) "
            f"VALUES ({placeholders})"
        )
        self.session.execute(query, values)
        self.session.commit()

    def _execute_delete(self, table: str, values: dict) -> None:
        """
        Execute a parameterized DELETE query.
        
        Args:
            table: The table to insert into
            values: Dictionary of column-value pairs to insert
        """
        if "client_id" in values.keys():
            values["client_id"] = self.client_id_encrypted
        where_condition = "AND ".join(f"{k} = :{k} " for k in values.keys())

        query = text(
            f"DELETE FROM {table} "
            f"WHERE {where_condition}"
        )
        self.session.execute(query, values)
        self.session.commit()
    
    def _client_exists(self) -> bool:
        """
        Check if the client exists in the database.
        
        Returns:
            True if client exists, raises ClientNotExistsError otherwise
            
        Raises:
            ClientNotExistsError: If client doesn't exist
        """
        query = text(
            f"SELECT client_id FROM {self.customers_table} "
            f"WHERE client_id = :client_id"
        )
        result = self.session.execute(
            query,
            {"client_id": self.client_id_encrypted}
        ).first()
        
        if not result:
            raise ClientNotExistsError(f"Client '{self.client_id}' not found")
        return True
    
    def _has_active_subscription(self) -> bool:
        """
        Check if client has an active subscription.
        
        Returns:
            True if subscription is active, raises SubscriptionError otherwise
            
        Raises:
            SubscriptionError: If subscription is not active
        """
        query = text(
            f"SELECT subscribed FROM {self.customers_table} "
            f"WHERE client_id = :client_id"
        )
        result = self.session.execute(
            query,
            {"client_id": self.client_id_encrypted}
        ).first()
        
        if not result or not result[0]:
            raise SubscriptionError(f"Client '{self.client_id}' has no active subscription")
        return True
    
    def _transaction_exists(self, transaction_id) -> bool:
        """
        Check if the transaction exists in the database.
        
        Returns:
            True if transaction exists, raises TransactionNotExistsError otherwise
            
        Raises:
            TransactionNotExistsError: If transaction doesn't exist
        """
        query = text(
            f"SELECT client_id FROM {self.transactions_table} "
            f"WHERE client_id = :client_id AND transaction_id = :transaction_id"
        )
        result = self.session.execute(
            query,
            {"client_id": self.client_id_encrypted, "transaction_id": transaction_id}
        ).first()
        
        if not result:
            raise TransactionNotExistsError(f"transaction '{transaction_id}' for client '{self.client_id}' not found")
        return True
    
    def grant_subscription(self, subscription_months: int) -> None:
        """
        Grant or extend a client's subscription.
        
        Args:
            subscription_months: Number of months to extend subscription
            
        Raises:
            ClientNotExistsError: If client doesn't exist
        """
        self._client_exists()
        
        update_values = {
            "updated_at": datetime.now(self.timezone),
            "subs_start_timestamp": datetime.now(self.timezone),
            "subs_end_timestamp": datetime.now(self.timezone) + relativedelta(months=subscription_months),
            "subscribed": True
        }
        
        self._execute_update(
            table=self.customers_table,
            set_values=update_values,
            where_condition=f"client_id = '{self.client_id_encrypted}'"
        )
    
    def revoke_subscription(self) -> None:
        """
        Revoke a client's subscription.
        
        Raises:
            ClientNotExistsError: If client doesn't exist
        """
        self._client_exists()
        
        update_values = {
            "updated_at": datetime.now(self.timezone),
            "subscribed": False
        }
        
        self._execute_update(
            table=self.customers_table,
            set_values=update_values,
            where_condition=f"client_id = '{self.client_id_encrypted}'"
        )

    @property
    def get_transaction_id(self):
        query = text(f"""
            SELECT 
                MAX(transaction_id) 
            FROM {self.transactions_table}
            WHERE
                client_id = :client_id
        """)

        result = self.session.execute(
            query,
            {
                "client_id": self.client_id_encrypted
            }
        ).first()
        if not result or not result[0]:
            transaction_id = 1
        else:
            transaction_id = result[0] + 1
        
        return transaction_id

    def insert_transaction(
        self,
        transaction_revenue: float,
        payment_method_name: Optional[str],
        payment_location: Optional[str],
        payment_product: Optional[str]
    ) -> Dict:
        """
        Insert a transaction record for the client.
        
        Args:
            transaction_revenue: The transaction amount
            payment_method_name: Payment method used
            payment_location: Location of payment
            payment_product: Product purchased
            
        Raises:
            ClientNotExistsError: If client doesn't exist
            SubscriptionError: If client has no active subscription
        """
        self._client_exists()
        self._has_active_subscription()
        
        _internal_transaction_id = self._encrypt_data(
            f"{self.client_id}:{datetime.now(self.timezone)}:"
            f"{transaction_revenue}:{payment_method_name}:"
            f"{payment_location}"
        )
 
        transaction_data = {
            "transaction_timestamp": datetime.now(self.timezone),
            "client_id": self.client_id_encrypted,
            "internal_transaction_id": _internal_transaction_id,
            "transaction_id": self.get_transaction_id,
            "transaction_revenue": transaction_revenue,
            "payment_method_name": payment_method_name,
            "payment_location": payment_location,
            "payment_product": payment_product
        }
        
        self._execute_insert(
            table=self.transactions_table,
            values=transaction_data
        )

        return transaction_data
    
    def upsert_client(self, name: str, phone: str) -> None:
        """
        Insert or update client information.
        
        Args:
            name: Client name
            phone: Client phone number (defaults to client_id if None)
        Raises:
            SubscriptionError: If client has no active subscription
        """
        try: self._client_exists()
        except ClientNotExistsError as e: ...
        else: self._has_active_subscription()

        phone = phone if phone is not None else self.client_id
        
        query = text(
            f"INSERT INTO {self.customers_table} "
            "(client_id, name, phone, created_at, updated_at) "
            "VALUES (:client_id, :name, :phone, :created_at, :updated_at) "
            "ON CONFLICT (client_id) "
            "DO UPDATE SET "
            "name = EXCLUDED.name, "
            "phone = EXCLUDED.phone, "
            "updated_at = EXCLUDED.updated_at"
        )
        
        self.session.execute(
            query,
            {
                "client_id": self.client_id_encrypted,
                "name": name,
                "phone": phone,
                "created_at": datetime.now(self.timezone),
                "updated_at": datetime.now(self.timezone)
            }
        )
        self.session.commit()

    def update_transaction(
        self,
        transaction_id: int,
        data: Dict[str, Any]
    ) -> Dict:
        """
        Update a client transaction.
        
        Args:
            transaction_id: Client transaction id to update
            data: Information in dict format to update
        Raises:
            ClientNotExistsError: If client doesn't exist
            SubscriptionError: If client has no active subscription
            TransactionNotExistsError: If transaction not exists for the client
        """
        self._client_exists()
        self._transaction_exists(transaction_id)
        self._has_active_subscription()
        
        update_values = {k: v for k, v in data.items()}

        self._execute_update(
            table=self.transactions_table,
            set_values=update_values,
            where_condition=f"""
                client_id = '{self.client_id_encrypted}'
                AND transaction_id = {transaction_id}
            """
        )

        return update_values
    
    def delete_transaction(
        self,
        data: Dict[str, Any]
    ) -> None:
        """
        Delete a client transaction.
        
        Args:
            transaction_id: Client transaction id to delete
        Raises:
            ClientNotExistsError: If client doesn't exist
            SubscriptionError: If client has no active subscription
            TransactionNotExistsError: If transaction not exists for the client
        """
        self._client_exists()
        self._has_active_subscription()

        self._execute_delete(
            table=self.transactions_table,
            values=data
        )


if __name__ == "__main__":
    pass