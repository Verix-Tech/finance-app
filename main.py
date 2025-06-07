import logging
import asyncio
from os import getenv
from sqlalchemy.exc import DataError, ProgrammingError, StatementError
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from typing import Union
from functools import partial

from databaseManager.connector import DatabaseManager
from databaseManager.inserter import Inserter
from errors.errors import SubscriptionError, ClientNotExistsError


# Constants
RESPONSE_SUCCESS = "Sucesso"
DATABASE_ERROR_MESSAGE = "erro ao inserir dados, verifique a consulta"
SYNTAX_ERROR_MESSAGE = "erro de sintaxe, verifique se os valores estão de acordo com o schema da tabela"
NO_SUBSCRIPTION_MESSAGE = "cliente sem assinatura"
CLIENT_NOT_EXISTS_MESSAGE = "cliente não está cadastrado"
DATABASE_ENDPOINT = getenv("DATABASE_ENDPOINT")
DATABASE_URL= getenv("DATABASE_URL")
DATABASE_USERNAME = getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = getenv("DATABASE_PASSWORD") 
DATABASE_PORT= getenv("DATABASE_PORT")

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    )
    logging.getLogger(__file__).setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
    logging.getLogger("psycopg2").setLevel(logging.ERROR)

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI()
db_manager = DatabaseManager()
db_manager.checkConnection()

# Implementar depois
# async def async_check_connection(db_manager):
#     loop = asyncio.get_event_loop()

#     return await loop.run_in_executor(None, db_manager.checkConnection)

# async def test_connection():
#     while True:
#         is_connected = await async_check_connection(db_manager)
#         if is_connected:
#             logging.info("Conexão com o banco estabelecida com sucesso!")
#             break
        
#         logging.info("Aguardando conexão com o banco...")
#         await asyncio.sleep(10)

# asyncio.run(test_connection())

# Helper functions to resume code
def create_error_response(
    message: str,
    error_detail: Union[DataError, ProgrammingError, StatementError, SubscriptionError, ClientNotExistsError], 
    status_code: int = status.HTTP_502_BAD_GATEWAY):
    content = {"error": message}
    if error_detail:
        content["message"] = str(error_detail)
    return JSONResponse(content=content, status_code=status_code)

def create_success_response(data: dict, message: str, status_code: int = status.HTTP_201_CREATED):
    return JSONResponse(
        content={
            "status": RESPONSE_SUCCESS,
            "data": data,
            "message": message
        },
        status_code=status_code
    )

# Endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/create-user")
async def createUser(request: Request):
    try:
        data = await request.json()

        inserter = Inserter(db_manager.getSession(), clientId=data["clientId"])
        inserter.upsertClientData(name=data["name"])

        logging.info(f"Dados inseridos com sucesso na tabela {inserter.customersTableId}.")

        return create_success_response(
            data=data,
            message=f"Cliente '{inserter.clientId}' atualizado!"
        )

    except DataError as e:
        logger.error(SYNTAX_ERROR_MESSAGE)
        return create_error_response(SYNTAX_ERROR_MESSAGE, e)
    except (ProgrammingError, StatementError) as e:
        logger.error(DATABASE_ERROR_MESSAGE)
        return create_error_response(DATABASE_ERROR_MESSAGE, e)
    except SubscriptionError as e:
        logger.error(NO_SUBSCRIPTION_MESSAGE)
        return create_error_response(NO_SUBSCRIPTION_MESSAGE, e, status_code=status.HTTP_403_FORBIDDEN)

@app.post("/create-transaction")
async def createTransaction(request: Request):
    try:
        data = await request.json()
        inserter = Inserter(db_manager.getSession(), clientId=data["clientId"])
        inserter.insertTransactionData(
            transaction_revenue=data["transactionRevenue"],
            payment_method_name=data["paymentMethodName"],
            payment_location=data["paymentLocation"],
            payment_product=data["paymentProduct"]
        )
        
        logger.info(f"Dados inseridos com sucesso na tabela {inserter.transactionsTableId}.")
        return create_success_response(
            data=data,
            message=f"Transação criada para o cliente: {inserter.clientId}!"
        )
    
    except ClientNotExistsError as e:
        logger.error(CLIENT_NOT_EXISTS_MESSAGE)
        return create_error_response(CLIENT_NOT_EXISTS_MESSAGE, e)
    except (ProgrammingError, StatementError) as e:
        logger.error(DATABASE_ERROR_MESSAGE)
        return create_error_response(DATABASE_ERROR_MESSAGE, e)
    except SubscriptionError as e:
        logger.error(NO_SUBSCRIPTION_MESSAGE)
        return create_error_response(NO_SUBSCRIPTION_MESSAGE, e, status_code=status.HTTP_403_FORBIDDEN)
    
@app.post("/grant-subscription")
async def grantSubscription(request: Request):
    try:
        data = await request.json()
        inserter = Inserter(db_manager.getSession(), clientId=data["clientId"])
        inserter.grantSubscription(subscription_months=data["subscriptionMonths"])
        
        return create_success_response(
            data=data,
            message=f"Assinatura criada para o cliente: {inserter.clientId}!"
        )
    
    except ClientNotExistsError as e:
        logger.error(CLIENT_NOT_EXISTS_MESSAGE)
        return create_error_response(CLIENT_NOT_EXISTS_MESSAGE, e)
    except DataError as e:
        logger.error(SYNTAX_ERROR_MESSAGE)
        return create_error_response(SYNTAX_ERROR_MESSAGE, e)
    except (ProgrammingError, StatementError) as e:
        logger.error(DATABASE_ERROR_MESSAGE)
        return create_error_response(DATABASE_ERROR_MESSAGE, e)
    except SubscriptionError as e:
        logger.error(NO_SUBSCRIPTION_MESSAGE)
        return create_error_response(NO_SUBSCRIPTION_MESSAGE, e, status_code=status.HTTP_403_FORBIDDEN)
    
@app.post("/revoke-subscription")
async def revoke_subscription(request: Request):
    try:
        data = await request.json()
        inserter = Inserter(db_manager.getSession(), clientId=data["clientId"])
        inserter.revogeSubscription()
        
        return create_success_response(
            data=data,
            message=f"Assinatura revogada para o cliente: {inserter.clientId}!"
        )
    
    except ClientNotExistsError as e:
        logger.error(CLIENT_NOT_EXISTS_MESSAGE)
        return create_error_response(CLIENT_NOT_EXISTS_MESSAGE, e)
    except DataError as e:
        logger.error(SYNTAX_ERROR_MESSAGE)
        return create_error_response(SYNTAX_ERROR_MESSAGE, e)
    except (ProgrammingError, StatementError) as e:
        logger.error(DATABASE_ERROR_MESSAGE)
        return create_error_response(DATABASE_ERROR_MESSAGE, e)
    except SubscriptionError as e:
        logger.error(NO_SUBSCRIPTION_MESSAGE)
        return create_error_response(NO_SUBSCRIPTION_MESSAGE, e, status_code=status.HTTP_403_FORBIDDEN)
