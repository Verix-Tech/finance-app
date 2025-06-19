import logging
import os
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError, ArgumentError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker, scoped_session


# Configure logging
def configure_logging() -> None:
    """Configure the logging settings for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/connector.log"),
            logging.StreamHandler()
        ]
    )
    # Set lower log levels for noisy libraries
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
    logging.getLogger("psycopg2").setLevel(logging.ERROR)


configure_logging()
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Handles database configuration and connection string creation."""
    
    def __init__(self) -> None:
        self.username = self._get_env_var("DATABASE_USERNAME")
        self.password = self._get_password()
        self.endpoint = self._get_env_var("DATABASE_ENDPOINT")
        self.port = self._get_env_var("DATABASE_PORT")
        self.database = self._get_env_var("DATABASE")
    
    @staticmethod
    def _get_env_var(name: str) -> str:
        """Get required environment variable or raise error if missing."""
        value = os.getenv(name)
        if not value:
            raise ValueError(f"Missing required environment variable: {name}")
        return value
    
    def _get_password(self) -> str:
        """Read database password from file specified in environment variable."""
        password_file = self._get_env_var("DATABASE_PASSWORD")
        try:
            with open(password_file) as file:
                return quote_plus(str(file.read()))
        except IOError as e:
            raise ValueError(f"Failed to read password file: {password_file}") from e
    
    @property
    def connection_string(self) -> str:
        """Generate the database connection string."""
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.endpoint}:{self.port}/{self.database}"
        )


class DatabaseManager:
    """Manages database connections and provides health monitoring."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None) -> None:
        """
        Initialize the database manager.
        
        Args:
            config: Optional DatabaseConfig instance. If None, will create one.
        """
        self.config = config if config else DatabaseConfig()
        self.engine = self._create_engine()
        self.session_factory = self._create_session_factory()
    
    def _create_engine(self):
        """Create and configure the SQLAlchemy engine."""
        return create_engine(
            self.config.connection_string,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600
        )
    
    def _create_session_factory(self):
        """Create a scoped session factory."""
        return scoped_session(
            sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        )
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.session_factory()
    
    def check_connection(self) -> bool:
        """Check if the database is accessible."""
        try:
            logger.info(
                f"Attempting to connect to database {self.config.endpoint}:{self.config.port}"
                
            )
            self.get_session().execute(text("SELECT 1"))
            logger.info(
                f"Successfully connected to database {self.config.endpoint}:{self.config.port}"
            )
            return True
        except OperationalError as e:
            logger.error(f"Database connection error. Please check credentials: {e}")
            return False
        except ArgumentError as e:
            logger.error(f"Database connection error. Please check connection URL: {e}")
            return False
    
    def is_healthy(self, timeout: int = 5) -> bool:
        """Perform a basic health check of the database."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception:
            return False
    
    def detailed_health_check(self, timeout: int = 5) -> Dict[str, Any]:
        """Perform a detailed health check with response time measurement."""
        try:
            with self.engine.connect() as conn:
                start = time.time()
                conn.execute(text("SELECT 1"))
                response_time = time.time() - start
                
                return {
                    "status": "healthy",
                    "response_time": response_time
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_connection_pool(self) -> Dict[str, Any]:
        """Check the status of the SQLAlchemy connection pool."""
        pool_info = {
            'status': 'unknown',
            'pool_size': 0,
            'checked_in': 0,
            'checked_out': 0,
            'overflow': 0,
            'timeout': 0,
            'recycle': -1,
            'connections': [],
            'last_checked': datetime.now().isoformat(),
            'error': None
        }
        
        try:
            pool = self.engine.pool
            inspector = inspect(self.engine)
            
            pool_info.update({
                'status': 'healthy',
                'pool_size': getattr(pool, '_pool_size', 0),
                'checked_in': getattr(pool, '_checkedin', 0),
                'checked_out': getattr(pool, '_checkedout', 0),
                'overflow': getattr(pool, '_max_overflow', 0),
                'timeout': getattr(pool, '_timeout', 0),
                'recycle': getattr(pool, '_recycle', -1),
            })
            
            # Check active connections if supported
            if hasattr(pool, '_conn'):
                pool_info['connections'] = [
                    {
                        'in_use': conn.is_valid if hasattr(conn, 'is_valid') else None,
                        'created_at': getattr(conn, 'create_time', None)
                    }
                    for conn in getattr(pool, '_conn', [])
                ]
            
            # Check database sessions if inspector is available
            if inspector:
                try:
                    pool_info['active_sessions'] = len(getattr(inspector, 'get_active_connections()', []))
                except Exception:
                    pass
            
        except SQLAlchemyError as e:
            pool_info.update({
                'status': 'error',
                'error': str(e)
            })
        
        return pool_info
    
    def shutdown(self) -> None:
        """Clean up resources and close connections."""
        self.session_factory.remove()
        self.engine.dispose()


class DatabaseMonitor:
    """Monitors database health at regular intervals."""
    
    def __init__(
        self,
        connector: DatabaseManager,
        interval: int = 300,
        timeout: int = 5
    ) -> None:
        """
        Initialize the database monitor.
        
        Args:
            connector: DatabaseManager instance to monitor
            interval: Check interval in seconds (default 5 minutes)
            timeout: Health check timeout in seconds
        """
        self.connector = connector
        self.interval = interval
        self.timeout = timeout
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self.logger = self._configure_monitor_logging()
    
    @staticmethod
    def _configure_monitor_logging() -> logging.Logger:
        """Configure logging for the monitor."""
        logger = logging.getLogger('db_monitor')
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler('logs/database_health.log')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    def start(self) -> None:
        """Start the monitoring thread."""
        if self._running:
            self.logger.warning("Monitor is already running")
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._monitor_thread.start()
        self.logger.info("Starting database health monitoring")
    
    def stop(self) -> None:
        """Stop the monitoring thread."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join()
        self.logger.info("Stopped database health monitoring")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop that runs checks at intervals."""
        while self._running:
            try:
                self._perform_health_check()
                self._log_hourly_metrics_if_needed()
            except Exception as e:
                self.logger.error(f"Monitoring error: {str(e)}")
            
            time.sleep(self.interval)
    
    def _perform_health_check(self) -> None:
        """Perform and log the health check."""
        health_status = self.connector.detailed_health_check(timeout=self.timeout)
        
        if health_status["status"] == "healthy":
            self.logger.info(
                f"Database healthy. Response time: {health_status['response_time']:.4f}s",
            )
        else:
            self.logger.error(
                f"Database problem: {health_status.get('error', 'Unknown error')}",
            )
    
    def _log_hourly_metrics_if_needed(self) -> None:
        """Log detailed metrics at the top of each hour."""
        if datetime.now().minute == 0:
            try:
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "basic_health": self.connector.is_healthy(),
                    "connection_pool": self.connector.check_connection_pool(),
                }
                self.logger.info(f"Detailed metrics: {metrics}")
            except Exception:
                self.logger.error("Failed to collect detailed metrics")
