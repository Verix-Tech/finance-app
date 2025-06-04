import hashlib
import logging
from errors.errors import SubscriptionError, ClientNotExistsError
from databaseManager.connector import DatabaseManager
from datetime import datetime
from os import getenv
from sqlalchemy import text
from sqlalchemy.orm import Session
from pytz import timezone
from dateutil.relativedelta import relativedelta


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__file__).setLevel(logging.ERROR)
logger = logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
logger = logging.getLogger("psycopg2").setLevel(logging.ERROR)

class Inserter:
    def __init__(self, session: Session, clientId: str) -> None:
        self.session = session
        self.timezone = timezone("America/Sao_Paulo")
        self.clientId = clientId
        self.clientIdEncrypted = self.encryptData(clientId)
        self.test_type = type(self.encryptData(clientId))
        self.customersTableId = "clients"
        self.transactionsTableId = "transactions"

    def encryptData(self, data) -> str:
        encryptedData = hashlib.sha1()
        encryptedData.update(data.encode("utf-8"))

        return encryptedData.hexdigest()
    
    def grantSubscription(self, subscription_months: int) -> None:
        try:
            self.checkIfClientExists()
        except TypeError:
            raise ClientNotExistsError

        self.session.execute(text(f"""
                UPDATE {self.customersTableId}
                SET subscription_start_timestamp = :subscription_start_timestamp, subscription_end_timestamp = :subscription_end_timestamp, subscribed = :subscribed, updated_at = :updated_at
                WHERE client_id='{self.clientIdEncrypted}'
            """),
            {
                "updated_at": datetime.now(self.timezone),
                "subscription_start_timestamp": datetime.now(self.timezone),
                "subscription_end_timestamp": datetime.now(self.timezone) + relativedelta(months=subscription_months),
                "subscribed": True
            })
        self.session.commit()

    def revogeSubscription(self) -> None:
        try:
            self.checkIfClientExists()
        except TypeError:
            raise ClientNotExistsError

        self.session.execute(text(f"""
                UPDATE {self.customersTableId}
                SET subscribed = :subscribed, updated_at = :updated_at
                WHERE client_id='{self.clientIdEncrypted}'
            """),
            {
                "updated_at": datetime.now(self.timezone),
                "subscribed": False
            })
        self.session.commit()

    def checkIfClientExists(self) -> bool:
        result = self.session.execute(text(f"""
            SELECT
                client_id
            FROM {self.customersTableId}
            WHERE
                client_id = '{self.clientIdEncrypted}'
        """)).first()[0]

        return True
    
    def checkClientSubscription(self) -> None:
        result = self.session.execute(text(f"""
            SELECT
                subscribed
            FROM {self.customersTableId}
            WHERE
                client_id = '{self.clientIdEncrypted}'
        """)).first()[0]
        
        if result == True:
            return
        raise SubscriptionError

    def insertTransactionData(self, transaction_revenue: str, payment_method_name: str, payment_location: str, payment_product: str) -> None:
        try:
            self.checkIfClientExists()
        except TypeError:
            raise ClientNotExistsError
        else:
            self.checkClientSubscription()

        _transaction_id = self.encryptData(data=f"{self.clientId}:{datetime.now(self.timezone)}:{transaction_revenue}:{payment_method_name}")

        self.session.execute(text(f"""
            INSERT INTO {self.transactionsTableId} (transaction_timestamp, client_id, transaction_id, transaction_revenue, payment_method_name, payment_location, payment_product)
            VALUES (:transaction_timestamp, :client_id, :transaction_id, :transaction_revenue, :payment_method_name, :payment_location, :payment_product)
        """),
        {
            "transaction_timestamp": datetime.now(self.timezone),
            "client_id": self.clientIdEncrypted,
            "transaction_id": _transaction_id,
            "transaction_revenue": transaction_revenue,
            "payment_method_name": payment_method_name,
            "payment_location": payment_location,
            "payment_product": payment_product
        })
        self.session.commit()
    
    def upsertClientData(self, name: str) -> None:
        try:
            self.checkIfClientExists()
        except TypeError:
            ...
        else:
            self.checkClientSubscription()

        self.session.execute(text(f"""
            INSERT INTO {self.customersTableId} (client_id, name, phone, created_at, updated_at)
            VALUES (:client_id, :name, :phone, :created_at, :updated_at)
            ON CONFLICT (client_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                phone = EXCLUDED.phone,
                updated_at = EXCLUDED.updated_at
        """),
        {
            "client_id": self.clientIdEncrypted,
            "name": name,
            "phone": self.clientId,
            "created_at": datetime.now(self.timezone),
            "updated_at": datetime.now(self.timezone)
        })
        self.session.commit()


if __name__ == "__main__":
    connection_string = getenv("DATABASE_URL")
    db_manager = DatabaseManager(connection_string, getenv("DATABASE_USERNAME"), getenv("DATABASE_PASSWORD"), getenv("DATABASE_PORT"))
    db_manager.checkConnection()

    _timezone = timezone("America/Sao_Paulo")

    inserter = Inserter(db_manager.getSession(), clientId="3")
    # print(inserter.checkClientSubscription())
    inserter.upsertClientData("jonatan", datetime.now(_timezone), True)
    # inserter.insertTransactionData(10, 1, "americanas")

    db_manager.shutdown()
