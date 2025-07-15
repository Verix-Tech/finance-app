import hashlib
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Union

from dateutil.relativedelta import relativedelta
from pytz import timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

from utils.utils import validate_and_format_date

from errors.errors import (
    SubscriptionError,
    ClientNotExistsError,
    TransactionNotExistsError,
)


# Configure logging
def configure_logging():
    """Configure application logging."""
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "inserter.log"

    # Create file handler
    file_handler = logging.FileHandler(log_file.as_posix())
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    # Attach the handler to the root logger if not already present
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not any(
        isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == str(log_file)
        for h in root_logger.handlers
    ):
        root_logger.addHandler(file_handler)

    # Also ensure a stream handler exists for console output
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(logging.StreamHandler())

    # Reduce noise from verbose libraries
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
    logging.getLogger("psycopg2").setLevel(logging.ERROR)


configure_logging()
logger = logging.getLogger(__name__)


class DataInserter:
    """Handles database operations for client subscriptions and transactions."""

    def __init__(self, session: Session, platform_id: str) -> None:
        """
        Initialize the DataInserter.

        Args:
            session: SQLAlchemy database session
            platform_id: The client identifier
        """
        self.session = session
        self.timezone = timezone("America/Sao_Paulo")
        self.platform_id = platform_id
        self.customers_table = "clients"
        self.transactions_table = "transactions"
        self.limits_table = "limits"
        self.cards_table = "cards"
        client_id_result = self._get_client_id()
        self.client_id_uuid = (
            client_id_result if client_id_result is not None else str(uuid.uuid4())
        )

        # Configure logging
        self._configure_logging()

    @staticmethod
    def _configure_logging() -> None:
        """Configure logging settings."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("logs/inserter.log"),
                logging.StreamHandler(),
            ],
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

    def _get_client_id(self) -> Optional[str]:
        """
        Get the client ID.

        Returns:
            The client ID if found, None otherwise
        """
        query = text(
            f"SELECT client_id FROM {self.customers_table} WHERE platform_id = :platform_id"
        )
        result = self.session.execute(query, {"platform_id": self.platform_id}).first()

        if not result:
            return None
        return result[0]

    def _execute_update(
        self, table: str, set_values: dict, where_condition: str
    ) -> None:
        """
        Execute a parameterized UPDATE query.

        Args:
            table: The table to update
            set_values: Dictionary of column-value pairs to set
            where_condition: The WHERE clause condition
        """
        set_clause = ", ".join(f"{k} = :{k}" for k in set_values.keys())
        query = text(f"UPDATE {table} " f"SET {set_clause} " f"WHERE {where_condition}")
        logger.info(f"Executing query:\n{query}")
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
        query = text(f"INSERT INTO {table} ({columns}) " f"VALUES ({placeholders})")
        logger.info(f"Executing query:\n{query}")
        self.session.execute(query, values)
        self.session.commit()

    def _execute_delete(self, table: str, values: dict) -> None:
        """
        Execute a parameterized DELETE query.

        Args:
            table: The table to delete from
            values: Dictionary of column-value pairs to match for deletion
                   Values can be single values or lists of values
        """
        if "platform_id" in values.keys():
            values["client_id"] = self.client_id_uuid
            values.pop("platform_id")

        where_conditions = []
        query_params = {}

        for column, value in values.items():
            if isinstance(value, list):
                # Handle list of values with unique parameter names
                param_names = [f"{column}_{i}" for i in range(len(value))]
                where_conditions.append(
                    f"{column} IN ({', '.join(f':{param}' for param in param_names)})"
                )
                for param_name, val in zip(param_names, value):
                    query_params[param_name] = val
            else:
                # Handle single value
                where_conditions.append(f"{column} = :{column}")
                query_params[column] = value

        where_clause = " AND ".join(where_conditions)

        query = text(f"DELETE FROM {table} " f"WHERE {where_clause}")
        logger.info(f"Executing query:\n{query}")
        self.session.execute(query, query_params)
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
            f"WHERE platform_id = :platform_id"
        )
        logger.info(f"Executing query:\n{query}")
        result = self.session.execute(query, {"platform_id": self.platform_id}).first()

        if not result:
            raise ClientNotExistsError(f"Client '{self.platform_id}' not found")
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
        logger.info(f"Executing query:\n{query}")
        result = self.session.execute(query, {"client_id": self.client_id_uuid}).first()

        if not result or not result[0]:
            raise SubscriptionError(
                f"Client '{self.client_id_uuid}' has no active subscription"
            )
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
        logger.info(f"Executing query:\n{query}")
        result = self.session.execute(
            query, {"client_id": self.client_id_uuid, "transaction_id": transaction_id}
        ).first()

        if not result:
            raise TransactionNotExistsError(
                f"transaction '{transaction_id}' for client '{self.client_id_uuid}' not found"
            )
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
            "subs_end_timestamp": datetime.now(self.timezone)
            + relativedelta(months=subscription_months),
            "subscribed": True,
        }

        try:
            self._execute_update(
                table=self.customers_table,
                set_values=update_values,
                where_condition=f"client_id = '{self.client_id_uuid}'",
            )
        except Exception as e:
            self.session.rollback()
            raise e

    def revoke_subscription(self) -> None:
        """
        Revoke a client's subscription.

        Raises:
            ClientNotExistsError: If client doesn't exist
        """
        self._client_exists()

        update_values = {"updated_at": datetime.now(self.timezone), "subscribed": False}

        try:
            self._execute_update(
                table=self.customers_table,
                set_values=update_values,
                where_condition=f"client_id = '{self.client_id_uuid}'",
            )
        except Exception as e:
            self.session.rollback()
            raise e

    @property
    def get_transaction_id(self):
        query = text(
            f"""
            SELECT 
                MAX(transaction_id) 
            FROM {self.transactions_table}
            WHERE
                client_id = :client_id
        """
        )
        
        logger.info(f"Executing query:\n{query}")
        result = self.session.execute(query, {"client_id": self.client_id_uuid}).first()
        if not result or not result[0]:
            transaction_id = 1
        else:
            transaction_id = result[0] + 1

        return transaction_id

    def insert_transaction(
        self,
        transaction_revenue: float,
        transaction_type: str,
        transaction_timestamp: Optional[str] = None,
        payment_method_id: Optional[str] = None,
        card_id: Optional[int] = None,
        payment_description: Optional[str] = None,
        payment_category_id: Optional[str] = None,
        installment_payment: Optional[bool] = None,
        installment_number: Optional[int] = None,
    ) -> Dict:
        """
        Insert a transaction record for the client.

        Args:
            transaction_revenue: The transaction amount
            transaction_type: The transaction type
            transaction_timestamp: The transaction timestamp
            payment_method_name: Payment method used
            payment_description: Description of payment
            payment_category: The payment category
        Raises:
            ClientNotExistsError: If client doesn't exist
            SubscriptionError: If client has no active subscription
        """
        self._client_exists()
        self._has_active_subscription()

        _internal_transaction_id = self._encrypt_data(
            f"{self.client_id_uuid}:{datetime.now(self.timezone)}:"
            f"{transaction_revenue}:{payment_method_id}:"
            f"{payment_description}"
        )

        transaction_timestamp = (
            validate_and_format_date(transaction_timestamp)
            if transaction_timestamp
            else datetime.now(self.timezone).strftime("%Y-%m-%d")
        )

        # ------------------------------------------------------------------
        # Ajusta o timestamp de acordo com a data de pagamento do cartão, se
        # aplicável. Compras após o dia de pagamento pertencem à fatura do
        # mês seguinte.
        # ------------------------------------------------------------------
        if card_id is not None and payment_method_id == "2":
            payment_date = self._get_card_payment_date(card_id)
            if payment_date is not None:
                try:
                    date_obj = datetime.strptime(transaction_timestamp, "%Y-%m-%d")
                    # Se o dia da compra for maior que o dia de pagamento,
                    # empurra para o mês seguinte.
                    if date_obj.day > payment_date:
                        date_obj += relativedelta(months=1)
                    # Garante que o dia permaneça consistente caso o novo
                    # mês não possua o mesmo número de dias.
                    transaction_timestamp = date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    # Caso a data seja inválida, mantemos como está e deixamos
                    # o fluxo normal tratar o erro posteriormente.
                    pass

        transaction_data = {
            "transaction_timestamp": transaction_timestamp,
            "client_id": self.client_id_uuid,
            "internal_transaction_id": _internal_transaction_id,
            "transaction_id": self.get_transaction_id,
            "transaction_revenue": transaction_revenue,
            "transaction_type": transaction_type,
            "payment_method_id": payment_method_id,
            "card_id": card_id,
            "payment_description": payment_description,
            "payment_category_id": payment_category_id,
            "installment_payment": installment_payment,
            "installment_number": installment_number
        }

        try:
            if installment_payment:
                transaction_data["transaction_revenue"] = (
                    transaction_revenue / float(installment_number or 1)
                )
                for i in range(installment_number or 0):
                    transaction_data["installment_number"] = (i + 1) or 1
                    transaction_data["transaction_timestamp"] = (
                        datetime.strptime(transaction_timestamp, "%Y-%m-%d")
                        + relativedelta(months=i)
                    ).strftime("%Y-%m-%d")
                    transaction_data["internal_transaction_id"] = (
                        _internal_transaction_id + f"{i + 1}"
                    )
                    self._execute_insert(
                        table=self.transactions_table, values=transaction_data
                    )

                return transaction_data
            else:
                transaction_data["installment_payment"] = False
                transaction_data["installment_number"] = 0
            self._execute_insert(table=self.transactions_table, values=transaction_data)
        except Exception as e:
            self.session.rollback()
            raise e

        return transaction_data

    def upsert_limit(self, category_id: str, limit_value: float) -> None:
        """
        Insert a limit record for the client.

        Args:
            limit_category: The limit category
            limit_value: The limit value
        Raises:
            ClientNotExistsError: If client doesn't exist
        """
        self._client_exists()

        limit_data = {
            "limit_id": str(uuid.uuid4()),
            "client_id": self.client_id_uuid,
            "category_id": category_id,
            "limit_value": limit_value,
            "created_at": datetime.now(self.timezone),
            "updated_at": datetime.now(self.timezone),
        }

        query = text(
            f"INSERT INTO {self.limits_table} "
            "VALUES (:limit_id, :client_id, :category_id, :limit_value, :created_at, :updated_at) "
            "ON CONFLICT (client_id, category_id) "
            "DO UPDATE SET "
            "limit_value = EXCLUDED.limit_value, "
            "updated_at = EXCLUDED.updated_at"
        )

        try:
            self.session.execute(query, limit_data)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e

    def upsert_client(self, platform_name: str, name: str, phone: str) -> None:
        """
        Insert or update client information.

        Args:
            name: Client name
            phone: Client phone number (defaults to client_id if None)
        Raises:
            SubscriptionError: If client has no active subscription
        """
        try:
            self._client_exists()
        except ClientNotExistsError as e:
            ...
        else:
            self._has_active_subscription()

        query = text(
            f"INSERT INTO {self.customers_table} "
            "(client_id, platform_id, platform_name, name, phone, created_at, updated_at) "
            "VALUES (:client_id, :platform_id, :platform_name, :name, :phone, :created_at, :updated_at) "
            "ON CONFLICT (client_id) "
            "DO UPDATE SET "
            "name = EXCLUDED.name, "
            "platform_name = EXCLUDED.platform_name, "
            "phone = EXCLUDED.phone, "
            "updated_at = EXCLUDED.updated_at"
        )

        try:
            self.session.execute(
                query,
                {
                    "client_id": self.client_id_uuid,
                    "platform_id": self.platform_id,
                    "platform_name": platform_name,
                    "name": name,
                    "phone": phone,
                    "created_at": datetime.now(self.timezone),
                    "updated_at": datetime.now(self.timezone),
                },
            )
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e

    def update_transaction(self, transaction_id: int, data: Dict[str, Any]) -> Dict:
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
            
        update_values = {
            k: v
            for k, v in data.items()
            if k not in ["client_id", "transaction_id", "platform_id"]
        }

        if self._transaction_has_installment(transaction_id):
            raise Exception("Transaction with installment cannot be updated")

        try:
            self._execute_update(
                table=self.transactions_table,
                set_values=update_values,
                where_condition=f"""
                client_id = '{self.client_id_uuid}'
                AND transaction_id = {transaction_id}
                """,
            )
        except Exception as e:
            self.session.rollback()
            raise e

        return update_values

    def delete_transaction(self, data: Dict[str, Any]) -> None:
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

        try:
            self._execute_delete(table=self.transactions_table, values=data)
        except Exception as e:
            self.session.rollback()
            raise e
        
    @property
    def get_card_id(self):
        query = text(
            f"""
            SELECT 
                MAX(card_id) 
            FROM {self.cards_table}
            WHERE
                client_id = :client_id
        """
        )
        
        logger.info(f"Executing query:\n{query}")
        result = self.session.execute(query, {"client_id": self.client_id_uuid}).first()
        if not result or not result[0]:
            card_id = 1
        else:
            card_id = result[0] + 1

        return card_id
    
    def insert_card(self, data: Dict[str, Any]) -> None:
        """
        Insert a card record for the client.
        """
        self._client_exists()
        self._has_active_subscription()

        data["internal_card_id"] = str(uuid.uuid4())
        data["card_id"] = self.get_card_id
        data["client_id"] = self.client_id_uuid
        data.pop("platform_id")
        
        try:
            self._execute_insert(table=self.cards_table, values=data)
        except Exception as e:
            self.session.rollback()
            raise e

    def _get_card_payment_date(self, card_id: int) -> Optional[int]:
        """Obter a data de pagamento (dia do mês) do cartão informado.

        Args:
            card_id: Identificador do cartão (sequencial por cliente)

        Returns:
            Um inteiro representando o dia de pagamento se encontrado, ou None caso
            o cartão não exista para o cliente.
        """
        query = text(
            f"SELECT payment_date FROM {self.cards_table} "
            "WHERE client_id = :client_id AND card_id = :card_id"
        )
        logger.info(f"Executing query:\n{query}")
        result = self.session.execute(
            query, {"client_id": self.client_id_uuid, "card_id": card_id}
        ).first()

        return result[0] if result else None
    
    def _transaction_has_installment(self, transaction_id: int) -> bool:
        """
        Check if the transaction has installment.
        """
        query = text(
            f"SELECT installment_payment FROM {self.transactions_table} "
            "WHERE transaction_id = :transaction_id"
        )
        logger.info(f"Executing query:\n{query}")
        result = self.session.execute(query, {"transaction_id": transaction_id}).first()
        return True if result and result[0] else False


if __name__ == "__main__":
    pass
