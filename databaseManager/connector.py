import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ArgumentError
from sqlalchemy.orm import Session, sessionmaker, scoped_session
from urllib.parse import quote_plus


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__file__)
logger = logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
logger = logging.getLogger("psycopg2").setLevel(logging.ERROR)

USERNAME = os.getenv("DATABASE_USERNAME")
PASSWORD = quote_plus(str(os.getenv("DATABASE_PASSWORD")))
ENDPOINT = os.getenv("DATABASE_ENDPOINT")
PORT = os.getenv("DATABASE_PORT")

connection_string = f"postgresql://{USERNAME}:{PASSWORD}@{ENDPOINT}:{PORT}/postgres"

class DatabaseManager:
    def __init__(self) -> None:
        self.database_instance_endpoint = ENDPOINT
        self.connection_string = connection_string
        self.port = PORT
        self.password = PASSWORD
        self.engine = create_engine(
            connection_string,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600
        )
        self.session_factory = scoped_session(
            sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        )
    
    def getSession(self) -> Session:
        return self.session_factory()
    
    def checkConnection(self) -> bool:
        try:
            logging.info(f"Tentando conectar ao banco {self.database_instance_endpoint}:{self.port}")
            self.getSession().execute(text("SELECT 1"))
            logging.info(f"Conectado com sucesso ao banco {self.database_instance_endpoint}:{self.port}")

            return True
        except OperationalError as e:
            logging.error("Erro ao conectar no banco. Verifique as credenciais do banco.", e)
            return False
        except ArgumentError as e:
            logging.error("Erro ao conectar no banco. Verifique se a URL está correta.")
            return False
    
    def shutdown(self) -> None:
        self.session_factory.remove()
        self.engine.dispose()
