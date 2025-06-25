import logging
import io
from os import getenv
from typing import Dict, Union
from datetime import timedelta

from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.exc import DataError, ProgrammingError, StatementError

from workers.main import generate_extract

from database_manager.connector import DatabaseManager, DatabaseMonitor
from database_manager.inserter import DataInserter
from errors.errors import SubscriptionError, ClientNotExistsError, TransactionNotExistsError
from auth.auth import (
    Token, User, authenticate_user, create_access_token,
    get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES
)


class AppConfig:
    """Handles application configuration and constants."""
    
    # Response messages
    RESPONSE_SUCCESS = "Sucesso"
    DATABASE_ERROR = "erro ao inserir dados, verifique a consulta"
    SYNTAX_ERROR = "erro de sintaxe, verifique os valores"
    NO_SUBSCRIPTION = "cliente sem assinatura"
    CLIENT_NOT_EXISTS = "cliente não está cadastrado"
    TRANSACTION_NOT_EXISTS = "transação não existente"
    
    # Environment variables
    DB_ENDPOINT = getenv("DATABASE_ENDPOINT")
    DB_URL = getenv("DATABASE_URL")
    DB_USERNAME = getenv("DATABASE_USERNAME")
    DB_PASSWORD = getenv("DATABASE_PASSWORD") 
    DB_PORT = getenv("DATABASE_PORT")


class ResponseHandler:
    """Handles API response formatting."""
    
    @staticmethod
    def create_error(
        message: str,
        error_detail: Union[DataError, ProgrammingError, StatementError, 
                           SubscriptionError, ClientNotExistsError, TransactionNotExistsError, ValueError, Exception, str],
        status_code: int = status.HTTP_502_BAD_GATEWAY
    ) -> JSONResponse:
        """Create a standardized error response."""
        content = {"error": message}
        if error_detail:
            content["detail"] = str(error_detail)
        return JSONResponse(content=content, status_code=status_code)
    
    @staticmethod
    def create_success(
        data: Dict,
        message: str,
        status_code: int = status.HTTP_201_CREATED
    ) -> JSONResponse:
        """Create a standardized success response."""
        return JSONResponse(
            content={
                "status": AppConfig.RESPONSE_SUCCESS,
                "data": data,
                "message": message
            },
            status_code=status_code
        )
    
    @staticmethod
    def create_csv_response(
        data: io.StringIO
    ) -> StreamingResponse:
        return StreamingResponse(
            iter([data.getvalue()]),
            headers={
                "Content-Disposition": f"attachment; filename=extract.json"
            },
            media_type="application/json"
        )


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
    
    def inserter(self, platform_id: str):
        return DataInserter(self.get_session(), platform_id)
    
    def shutdown(self):
        """Clean up database resources."""
        self.manager.shutdown()


def configure_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/app.log"),
            logging.StreamHandler()
        ]
    )
    # Reduce noise from libraries
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
    logging.getLogger("psycopg2").setLevel(logging.ERROR)


# Application setup
configure_logging()
logger = logging.getLogger(__name__)
app = FastAPI()
db_service = DatabaseService()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    db_service.shutdown()


@app.get("/health")
async def health_check():
    """Endpoint for health checks."""
    return {"status": "healthy"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Generate token for authentication."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/generate-report")
async def generate_report(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Generate extract for a client."""
    data = await request.json()

    try:
        start_date = data.get("start_date") or None
        end_date = data.get("end_date") or None
        days_before = data.get("days_before") or None
        aggr = data.get("aggr") or None
        filter = data.get("filter") or None

        client_id = db_service.inserter(data["platform_id"]).client_id_uuid
        
        # Check if Redis server is configured
        redis_server = getenv('REDIS_SERVER')
        if not redis_server:
            logger.error("REDIS_SERVER environment variable not set")
            return ResponseHandler.create_error(
                "Internal server error",
                "Redis server not configured",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        logger.info(f"Starting Celery task with Redis broker: {redis_server}")
        
        # Start the Celery task
        try:
            task = generate_extract.delay(
                client_id=client_id, 
                start_date=start_date, 
                end_date=end_date, 
                days_before=days_before, 
                aggr=aggr,
                filter=filter
            )
            logger.info(f"Celery task started successfully with ID: {task.id}")
        except Exception as celery_error:
            logger.error(f"Failed to start Celery task: {celery_error}")
            return ResponseHandler.create_error(
                "Internal server error",
                f"Failed to start background task: {str(celery_error)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return ResponseHandler.create_success(
            data={"task_id": task.id, "status": "task_started"},
            message="Data generation task started"
        )
        
    except ValueError as e:
        logger.error(f"Error generating data: {e}")
        return ResponseHandler.create_error(
            AppConfig.SYNTAX_ERROR,
            e,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Unexpected error in generate_data: {e}")
        return ResponseHandler.create_error(
            "Internal server error",
            e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/task-status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get the status of a Celery task."""
    try:
        # Check if Redis server is configured
        redis_server = getenv('REDIS_SERVER')
        if not redis_server:
            logger.error("REDIS_SERVER environment variable not set")
            return ResponseHandler.create_error(
                "Internal server error",
                "Redis server not configured",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        logger.info(f"Checking task status with Redis broker: {redis_server}")
        
        try:
            from workers.main import app as celery_app
            task_result = celery_app.AsyncResult(task_id)
        except Exception as import_error:
            logger.error(f"Failed to import Celery app: {import_error}")
            return ResponseHandler.create_error(
                "Internal server error",
                f"Failed to connect to task broker: {str(import_error)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Check if the task is ready
        if task_result.ready():
            if task_result.successful():
                result = task_result.result
                stream = io.StringIO(result)
                    
                return ResponseHandler.create_csv_response(
                    data=stream
                )
            else:
                error_info = task_result.info
                if isinstance(error_info, dict) and "exc_message" in error_info:
                    error_message = error_info["exc_message"]
                    error_type = error_info["exc_type"]
                else:
                    error_message = str(error_info) if error_info else "Unknown error"
                    error_type = type(error_info).__name__

                return ResponseHandler.create_error(
                    f"Task execution failed: {error_type}",
                    error_message,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return ResponseHandler.create_success(
                data={
                    "task_id": task_id,
                    "status": "running",
                    "state": task_result.state
                },
                message="Task is still running"
            )
            
    except Exception as e:
        logger.error(f"Error checking task status: {e}")
        return ResponseHandler.create_error(
            "Error checking task status",
            e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.post("/create-user")
async def create_user(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Create or update a user."""
    try:
        data = await request.json()
        inserter = db_service.inserter(data["platform_id"])
        inserter.upsert_client(platform_name=data["platform_name"], name=data["name"], phone=data["phone"])
        
        logger.info("User data inserted successfully")
        return ResponseHandler.create_success(
            data=data,
            message=f"Client '{inserter.platform_id}' updated!"
        )
    
    except DataError as e:
        logger.error(AppConfig.SYNTAX_ERROR)
        return ResponseHandler.create_error(AppConfig.SYNTAX_ERROR, e)
    except (ProgrammingError, StatementError) as e:
        logger.error(AppConfig.DATABASE_ERROR)
        return ResponseHandler.create_error(AppConfig.DATABASE_ERROR, e)
    except SubscriptionError as e:
        logger.error(AppConfig.NO_SUBSCRIPTION)
        return ResponseHandler.create_error(
            AppConfig.NO_SUBSCRIPTION, 
            e, 
            status_code=status.HTTP_403_FORBIDDEN
        )
    
@app.get("/client-exists")
async def client_exists(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Check if a client exists."""
    try:
        data = await request.json()
        inserter = db_service.inserter(data["platform_id"])
        if inserter._client_exists():
            return ResponseHandler.create_success(
                data=data,
                message=f"Client '{inserter.client_id_uuid}' exists!"
            )
        else:
            return ResponseHandler.create_error(
                AppConfig.CLIENT_NOT_EXISTS, 
                f"Client '{inserter.client_id_uuid}' does not exist!",
                status_code=status.HTTP_404_NOT_FOUND
            )
    
    except ClientNotExistsError as e:
        logger.error(AppConfig.CLIENT_NOT_EXISTS)
        return ResponseHandler.create_error(AppConfig.CLIENT_NOT_EXISTS, e)
    except DataError as e:
        logger.error(AppConfig.SYNTAX_ERROR)
        return ResponseHandler.create_error(AppConfig.SYNTAX_ERROR, e)
    except (ProgrammingError, StatementError) as e:
        logger.error(AppConfig.DATABASE_ERROR)
        return ResponseHandler.create_error(AppConfig.DATABASE_ERROR, e)
    except SubscriptionError as e:
        logger.error(AppConfig.NO_SUBSCRIPTION)
        return ResponseHandler.create_error(
            AppConfig.NO_SUBSCRIPTION, 
            e, 
            status_code=status.HTTP_403_FORBIDDEN
        )

@app.post("/create-transaction")
async def create_transaction(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new transaction."""
    try:
        data = await request.json()
        inserter = DataInserter(db_service.get_session(), data["platform_id"])
        
        transaction_data = inserter.insert_transaction(
            transaction_revenue=data.get("transaction_revenue"), 
            transaction_timestamp=data.get("transaction_timestamp"),
            payment_method_id=data.get("payment_method_id"),
            payment_description=data.get("payment_description"),
            payment_category_id=data.get("payment_category_id"),
            transaction_type=data.get("transaction_type")
        )

        data["transaction_id"] = transaction_data["transaction_id"]
        
        logger.info("Transaction created successfully")
        return ResponseHandler.create_success(
            data=data,
            message=f"Transaction created for client: {inserter.platform_id}!"
        )
    
    except ClientNotExistsError as e:
        logger.error(AppConfig.CLIENT_NOT_EXISTS)
        return ResponseHandler.create_error(AppConfig.CLIENT_NOT_EXISTS, e)
    except (ProgrammingError, StatementError) as e:
        logger.error(AppConfig.DATABASE_ERROR)
        return ResponseHandler.create_error(AppConfig.DATABASE_ERROR, e)
    except SubscriptionError as e:
        logger.error(AppConfig.NO_SUBSCRIPTION)
        return ResponseHandler.create_error(
            AppConfig.NO_SUBSCRIPTION,
            e,
            status_code=status.HTTP_403_FORBIDDEN
        )

@app.post("/update-transaction")
async def update_transaction(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """update a new transaction."""
    try:
        data = await request.json()
        inserter = DataInserter(db_service.get_session(), data["platform_id"])
        
        update_data = {k:v for k,v in data.items() if k not in ["client_id", "transactionId"]}

        transaction_data = inserter.update_transaction(
            transaction_id=data["transactionId"],
            data=update_data
        )
        
        logger.info("Transaction updated successfully")
        return ResponseHandler.create_success(
            data=data,
            message=f"Transaction updated for client: {inserter.platform_id}!"
        )
    
    except ClientNotExistsError as e:
        logger.error(AppConfig.CLIENT_NOT_EXISTS)
        return ResponseHandler.create_error(AppConfig.CLIENT_NOT_EXISTS, e)
    except TransactionNotExistsError as e:
        logger.error(AppConfig.TRANSACTION_NOT_EXISTS)
        return ResponseHandler.create_error(AppConfig.TRANSACTION_NOT_EXISTS, e)
    except (ProgrammingError, StatementError) as e:
        logger.error(AppConfig.DATABASE_ERROR)
        return ResponseHandler.create_error(AppConfig.DATABASE_ERROR, e)
    except SubscriptionError as e:
        logger.error(AppConfig.NO_SUBSCRIPTION)
        return ResponseHandler.create_error(
            AppConfig.NO_SUBSCRIPTION,
            e,
            status_code=status.HTTP_403_FORBIDDEN
        )
    
@app.post("/delete-transaction")
async def delete_transaction(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """delete a new transaction."""
    try:
        data = await request.json()
        inserter = DataInserter(db_service.get_session(), data["platform_id"])

        transaction_data = inserter.delete_transaction(
            data=data
        )
        
        logger.info("Transaction deleted successfully")
        return ResponseHandler.create_success(
            data=data,
            message=f"Transaction deleted for client: {inserter.platform_id}!"
        )
    
    except ClientNotExistsError as e:
        logger.error(AppConfig.CLIENT_NOT_EXISTS)
        return ResponseHandler.create_error(AppConfig.CLIENT_NOT_EXISTS, e)
    except TransactionNotExistsError as e:
        logger.error(AppConfig.TRANSACTION_NOT_EXISTS)
        return ResponseHandler.create_error(AppConfig.TRANSACTION_NOT_EXISTS, e)
    except (ProgrammingError, StatementError) as e:
        logger.error(AppConfig.DATABASE_ERROR)
        return ResponseHandler.create_error(AppConfig.DATABASE_ERROR, e)
    except SubscriptionError as e:
        logger.error(AppConfig.NO_SUBSCRIPTION)
        return ResponseHandler.create_error(
            AppConfig.NO_SUBSCRIPTION,
            e,
            status_code=status.HTTP_403_FORBIDDEN
        )


@app.post("/grant-subscription")
async def grant_subscription(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Grant a subscription to a user."""
    try:
        data = await request.json()
        inserter = DataInserter(db_service.get_session(), data["platform_id"])
        inserter.grant_subscription(subscription_months=data["subscriptionMonths"])
        
        return ResponseHandler.create_success(
            data=data,
            message=f"Subscription created for client: {inserter.platform_id}!"
        )
    
    except ClientNotExistsError as e:
        logger.error(AppConfig.CLIENT_NOT_EXISTS)
        return ResponseHandler.create_error(AppConfig.CLIENT_NOT_EXISTS, e)
    except DataError as e:
        logger.error(AppConfig.SYNTAX_ERROR)
        return ResponseHandler.create_error(AppConfig.SYNTAX_ERROR, e)
    except (ProgrammingError, StatementError) as e:
        logger.error(AppConfig.DATABASE_ERROR)
        return ResponseHandler.create_error(AppConfig.DATABASE_ERROR, e)
    except SubscriptionError as e:
        logger.error(AppConfig.NO_SUBSCRIPTION)
        return ResponseHandler.create_error(
            AppConfig.NO_SUBSCRIPTION,
            e,
            status_code=status.HTTP_403_FORBIDDEN
        )


@app.post("/revoke-subscription")
async def revoke_subscription(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Revoke a user's subscription."""
    try:
        data = await request.json()
        inserter = DataInserter(db_service.get_session(), data["platform_id"])
        inserter.revoke_subscription()
        
        return ResponseHandler.create_success(
            data=data,
            message=f"Subscription revoked for client: {inserter.platform_id}!"
        )
    
    except ClientNotExistsError as e:
        logger.error(AppConfig.CLIENT_NOT_EXISTS)
        return ResponseHandler.create_error(AppConfig.CLIENT_NOT_EXISTS, e)
    except DataError as e:
        logger.error(AppConfig.SYNTAX_ERROR)
        return ResponseHandler.create_error(AppConfig.SYNTAX_ERROR, e)
    except (ProgrammingError, StatementError) as e:
        logger.error(AppConfig.DATABASE_ERROR)
        return ResponseHandler.create_error(AppConfig.DATABASE_ERROR, e)
    except SubscriptionError as e:
        logger.error(AppConfig.NO_SUBSCRIPTION)
        return ResponseHandler.create_error(
            AppConfig.NO_SUBSCRIPTION,
            e,
            status_code=status.HTTP_403_FORBIDDEN
        )
