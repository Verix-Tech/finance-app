import logging
from databaseManager.connector import DatabaseManager
from databaseManager.inserter import Inserter
from errors.errors import SubscriptionError, ClientNotExistsError

from os import getenv
from sqlalchemy.exc import DataError, ProgrammingError, StatementError

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


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

app = FastAPI()

connection_string = getenv("DATABASE_URL")
db_manager = DatabaseManager(getenv("DATABASE_ENDPOINT"), connection_string, getenv("DATABASE_USERNAME"), getenv("DATABASE_PASSWORD"), getenv("DATABASE_PORT"))
db_manager.checkConnection() 

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/create-user")
async def createUser(request: Request):
    try:
        data = await request.json()

        inserter = Inserter(db_manager.getSession(), clientId=data["clientId"])
        inserter.upsertClientData(name=data["name"])
    except DataError as e:
        logging.error(f"Erro de sintaxe, verifique se os valores estão de acordo com o schema da tabela.")

        return JSONResponse(
            content={"error": "erro de sintaxe, verifique se os valores estão de acordo com o schema da tabela.", "message": e},
            status_code=502
        )
    except (ProgrammingError, StatementError) as e:
        logging.error(f"Erro ao inserir dados, verifique a consulta.")

        return JSONResponse(
            content={"error": "erro ao inserir dados, verifique a consulta", "message": e},
            status_code=502
        )
    except SubscriptionError as e:
        logging.error("Erro: cliente sem assinatura.")

        return JSONResponse(
            content={"error": "cliente sem assinatura"},
            status_code=403
        )
    else:
        logging.info(f"Dados inseridos no banco com sucesso na tabela {inserter.customersTableId}.")
        
        resposta = {
            "status": "Sucesso",
            "data": data,
            "message": f"Cliente '{inserter.clientId}' atualizado!"
        }
        return JSONResponse(content=resposta, status_code=201)

@app.post("/create-transaction")
async def createTransaction(request: Request):
    try:
        data = await request.json()

        inserter = Inserter(db_manager.getSession(), clientId=data["clientId"])
        inserter.insertTransactionData(transaction_revenue=data["transactionRevenue"], payment_method_name=data["paymentMethodName"], payment_location=data["paymentLocation"], payment_product=data["paymentProduct"])
    except ClientNotExistsError as e:
        logging.error(f"Cliente não está cadastrado.")

        return JSONResponse(
            content={"error": "cliente não está cadastrado."},
            status_code=502
        )
    except (ProgrammingError, StatementError) as e:
        logging.error(f"Erro ao inserir dados, verifique a consulta.")

        return JSONResponse(
            content={"error": "erro ao inserir dados, verifique a consulta.", "message": e},
            status_code=502
        )
    except SubscriptionError as e:
        logging.error("Erro: cliente sem assinatura.")

        return JSONResponse(
            content={"error": "cliente sem assinatura."},
            status_code=403
        )
    else:
        logging.info(f"Dados inseridos no banco com sucesso na tabela {inserter.transactionsTableId}.")

        resposta = {
            "status": "Sucesso",
            "data": data,
            "message": f"Transação criada para o cliente: {inserter.clientId}!"
        }
        return JSONResponse(content=resposta, status_code=201)
    
@app.post("/grant-subscription")
async def grantSubscription(request: Request):
    try:
        data = await request.json()

        inserter = Inserter(db_manager.getSession(), clientId=data["clientId"])
        inserter.grantSubscription(subscription_months=data["subscriptionMonths"])
    except ClientNotExistsError as e:
        logging.error(f"Cliente não está cadastrado.")

        return JSONResponse(
            content={"error": "cliente não está cadastrado."},
            status_code=502
        )
    except DataError as e:
        logging.error(f"Erro de sintaxe, verifique se os valores estão de acordo com o schema da tabela.")

        return JSONResponse(
            content={"error": "erro de sintaxe, verifique se os valores estão de acordo com o schema da tabela.", "message": e},
            status_code=502
        )
    except (ProgrammingError, StatementError) as e:
        logging.error(f"Erro ao inserir dados, verifique a consulta.")

        return JSONResponse(
            content={"error": "erro ao inserir dados, verifique a consulta.", "message": e},
            status_code=502
        )
    except SubscriptionError as e:
        logging.error("Erro: cliente sem assinatura.")

        return JSONResponse(
            content={"error": "cliente sem assinatura."},
            status_code=403
        )
    else:
        resposta = {
            "status": "Sucesso",
            "data": data,
            "message": f"Assinatura criada para o cliente: {inserter.clientId}!"
        }
        return JSONResponse(content=resposta, status_code=201)
    
@app.post("/revoge-subscription")
async def revogeSubscription(request: Request):
    try:
        data = await request.json()

        inserter = Inserter(db_manager.getSession(), clientId=data["clientId"])
        inserter.revogeSubscription()
    except ClientNotExistsError as e:
        logging.error(f"Cliente não está cadastrado.")

        return JSONResponse(
            content={"error": "cliente não está cadastrado."},
            status_code=502
        )
    except DataError as e:
        logging.error(f"Erro de sintaxe, verifique se os valores estão de acordo com o schema da tabela.")

        return JSONResponse(
            content={"error": "erro de sintaxe, verifique se os valores estão de acordo com o schema da tabela.", "message": e},
            status_code=502
        )
    except (ProgrammingError, StatementError) as e:
        logging.error(f"Erro ao inserir dados, verifique a consulta.")

        return JSONResponse(
            content={"error": "erro ao inserir dados, verifique a consulta.", "message": e},
            status_code=502
        )
    except SubscriptionError as e:
        logging.error("Erro: cliente sem assinatura.")

        return JSONResponse(
            content={"error": "cliente sem assinatura."},
            status_code=403
        )
    else:
        resposta = {
            "status": "Sucesso",
            "data": data,
            "message": f"Assinatura revogada para o cliente: {inserter.clientId}!"
        }
        return JSONResponse(content=resposta, status_code=201)
