import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ArgumentError
from sqlalchemy.orm import Session, sessionmaker, scoped_session


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

class DatabaseManager:
    def __init__(self, database_instance_endpoint: str, connection_string: str, username: str, password: str, port: str) -> None:
        self.database_instance_endpoint = database_instance_endpoint
        self.connection_string = connection_string
        self.port = port
        self.engine = create_engine(
            connection_string.format(username, password, database_instance_endpoint, port),
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
    
    def checkConnection(self) -> None:
        try:
            logging.info(f"Tentando conectar ao banco {self.database_instance_endpoint}:{self.port}")
            self.getSession().execute(text("SELECT 1"))
            logging.info(f"Conectado com sucesso ao banco {self.database_instance_endpoint}:{self.port}")
        except OperationalError as e:
            logging.error("Erro ao conectar no banco. Verifique as credenciais do banco.". e)
        except ArgumentError as e:
            logging.error("Erro ao conectar no banco. Verifique se a URL está correta.")
    
    def shutdown(self) -> None:
        self.session_factory.remove()
        self.engine.dispose()
