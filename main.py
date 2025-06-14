import logging
from os import getenv
from typing import Dict, Union
from datetime import timedelta

from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, ProgrammingError, StatementError

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
                           SubscriptionError, ClientNotExistsError, TransactionNotExistsError],
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
    
    def shutdown(self):
        """Clean up database resources."""
        self.manager.shutdown()


def configure_logging():
    """Configure application logging."""
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

@app.post("/create-user")
async def create_user(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Create or update a user."""
    try:
        data = await request.json()
        inserter = DataInserter(db_service.get_session(), data["client_id"])
        inserter.upsert_client(name=data["name"], phone=data["client_id"])
        
        logger.info("User data inserted successfully")
        return ResponseHandler.create_success(
            data=data,
            message=f"Client '{inserter.client_id}' updated!"
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


@app.post("/create-transaction")
async def create_transaction(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new transaction."""
    try:
        data = await request.json()
        inserter = DataInserter(db_service.get_session(), data["client_id"])
        
        transaction_data = inserter.insert_transaction(
            transaction_revenue=data["transaction_revenue"],
            payment_method_name=data["payment_method_name"],
            payment_location=data["payment_location"],
            payment_product=data["payment_product"]
        )

        data["transaction_id"] = transaction_data["transaction_id"]
        
        logger.info("Transaction created successfully")
        return ResponseHandler.create_success(
            data=data,
            message=f"Transaction created for client: {inserter.client_id}!"
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
        inserter = DataInserter(db_service.get_session(), data["client_id"])
        
        update_data = {k:v for k,v in data.items() if k not in ["client_id", "transactionId"]}

        transaction_data = inserter.update_transaction(
            transaction_id=data["transactionId"],
            data=update_data
        )
        
        logger.info("Transaction updated successfully")
        return ResponseHandler.create_success(
            data=data,
            message=f"Transaction updated for client: {inserter.client_id}!"
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
        inserter = DataInserter(db_service.get_session(), data["client_id"])

        transaction_data = inserter.delete_transaction(
            data=data
        )
        
        logger.info("Transaction deleted successfully")
        return ResponseHandler.create_success(
            data=data,
            message=f"Transaction deleted for client: {inserter.client_id}!"
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
        inserter = DataInserter(db_service.get_session(), data["client_id"])
        inserter.grant_subscription(subscription_months=data["subscriptionMonths"])
        
        return ResponseHandler.create_success(
            data=data,
            message=f"Subscription created for client: {inserter.client_id}!"
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
        inserter = DataInserter(db_service.get_session(), data["client_id"])
        inserter.revoke_subscription()
        
        return ResponseHandler.create_success(
            data=data,
            message=f"Subscription revoked for client: {inserter.client_id}!"
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
