import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import logging
from datetime import datetime, timedelta
from os import getenv
from typing import Optional
from sqlalchemy import text
from celery import Celery, states
from celery.exceptions import Ignore, Reject
from sqlalchemy.exc import DataError, ProgrammingError, StatementError

from database_manager.connector import DatabaseManager
from database_manager.models.models import Transaction
from utils import get_start_end_date, make_where_string, make_aggr_logic, get_limits


# Configure logging
def configure_logging():
    """Configure application logging."""
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "workers.log"

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

# Get Redis configuration with fallback
redis_server = getenv("REDIS_SERVER", "redis://localhost:6379")
logger.info(f"Configuring Celery with Redis broker: {redis_server}")

try:
    app = Celery("tasks", broker=redis_server, backend=redis_server)
    logger.info("Celery app configured successfully")

    # Configure Celery settings for Docker environment
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
    )
    logger.info("Celery configuration applied successfully")
except Exception as e:
    logger.error(f"Failed to configure Celery app: {e}")
    raise

db_manager = DatabaseManager()


class AppConfig:
    """Handles application configuration and constants."""

    # Response messages
    DATABASE_ERROR = "erro ao inserir dados, verifique a consulta"
    SYNTAX_ERROR = "erro de sintaxe, verifique os valores"
    VALIDATION_ERROR = {
        "start_date_or_days_before_required": "start_date or days_before must be provided",
        "invalid_aggr_mode": "Invalid aggr mode",
        "Exception": "Unexpected error in generate_extract",
        "ValueError": "Validation error in generate_extract",
    }
    EMPTY_DATA_ERROR = "sem dados no período"


@app.task(bind=True)
def generate_extract(
    self,
    client_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days_before: Optional[str] = None,
    filter: Optional[dict] = None,
    aggr: Optional[dict] = None,
) -> str:
    """Generate extract for a client with proper error handling."""
    try:
        logger.info(f"Starting extract generation for client_id: {client_id}")

        columns = (
            [
                "client_id",
                "transaction_id",
                "transaction_timestamp",
                "transaction_revenue",
                "payment_description",
                "payment_categories.payment_category_id",
                "payment_categories.payment_category_name",
                "payment_methods.payment_method_id",
                "payment_methods.payment_method_name",
                "transaction_type",
            ]
            if aggr
            else ["client_id", "transaction_timestamp", "transaction_revenue"]
        )

        # Dicionário para renomear as colunas para nomes mais amigáveis
        column_rename_map = {
            "payment_categories.payment_category_id": "payment_category_id",
            "payment_categories.payment_category_name": "payment_category_name",
            "payment_methods.payment_method_id": "payment_method_id",
            "payment_methods.payment_method_name": "payment_method_name"
        }

        if not start_date and not days_before:
            error_msg = AppConfig.VALIDATION_ERROR["start_date_or_days_before_required"]
            logger.error(f"Validation error: {error_msg}")
            raise ValueError(error_msg)
        elif days_before:
            start_date, end_date = get_start_end_date(int(days_before))
        elif start_date and not end_date:
            end_date = start_date

        where_string = make_where_string(filter) if filter else "1=1"
        query = f"""
                SELECT 
                    {', '.join(columns)}
                FROM transactions
                LEFT JOIN payment_categories ON transactions.payment_category_id = payment_categories.payment_category_id
                LEFT JOIN payment_methods ON transactions.payment_method_id = payment_methods.payment_method_id
                WHERE
                    client_id = '{client_id}'
                    AND date(transaction_timestamp) BETWEEN '{start_date}' AND '{end_date}'
                    AND {where_string}
                """
        logger.info(f"Executing query:\n{query}")

        with db_manager.get_session() as session:
            dados = session.execute(text(query)).all()
            df = pd.DataFrame(dados, columns=columns)

            df.rename(columns={col: column_rename_map.get(col, col) for col in df.columns}, inplace=True)

            df["transaction_timestamp"] = pd.to_datetime(df["transaction_timestamp"])

            if aggr and aggr["activated"] == True:
                if aggr["mode"] is not None:
                    df = make_aggr_logic(aggr["mode"], df)
                else:
                    self.update_state(
                        state=states.FAILURE,
                        meta={
                            "exc_type": str(ValueError),
                            "exc_message": AppConfig.VALIDATION_ERROR[
                                "invalid_aggr_mode"
                            ],
                        },
                    )
                    raise ValueError(AppConfig.VALIDATION_ERROR["invalid_aggr_mode"])
            else:
                pass

            df["transaction_timestamp"] = df["transaction_timestamp"].dt.strftime("%Y-%m-%d")

            result = df.to_csv(index=True)
            logger.info(
                f"Extract generation completed successfully for client_id: {client_id}"
            )
            return result

    except pd.errors.EmptyDataError as e:
        error_msg = (
            AppConfig.EMPTY_DATA_ERROR
        )
        logger.error(error_msg)
        self.update_state(
            state=states.FAILURE,
            meta={"exc_type": type(e).__name__, "exc_message": str(e)}
        )
        raise Ignore()

    except (ValueError, Exception, DataError, ProgrammingError, StatementError) as e:
        error_msg = (
            AppConfig.VALIDATION_ERROR[type(e).__name__]
            if type(e).__name__ in AppConfig.VALIDATION_ERROR
            else AppConfig.DATABASE_ERROR
        )
        logger.error(error_msg)
        self.update_state(
            state=states.FAILURE,
            meta={"exc_type": type(e).__name__, "exc_message": str(e)},
        )
        raise Ignore()


@app.task(bind=True)
def limit_check(self, client_id: str, category_id: str) -> dict:
    """Check if the limit is exceeded."""
    try:
        logger.info(
            f"Starting limit check for client_id: {client_id}, category_id: {category_id}"
        )

        query = f"""
            SELECT 
                SUM(transaction_revenue) as total_revenue
            FROM transactions 
            WHERE 
                client_id = '{client_id}' 
                AND payment_category_id = '{category_id}'
                AND date_trunc('month', transaction_timestamp) = date_trunc('month', CURRENT_DATE)
        """
        logger.info(f"Executing query:\n{query}")

        with db_manager.get_session() as session:
            dados = session.execute(text(query)).all()
            df = pd.DataFrame(dados)
            total_revenue = df["total_revenue"].values[0]

            limit_value = get_limits(client_id=client_id, category_id=category_id)
            limit_exceeded = True if total_revenue >= limit_value else False

            return {
                "status": "success",
                "message": "Limit check completed",
                "category_id": category_id,
                "total_revenue": total_revenue,
                "limit_value": limit_value,
                "limit_exceeded": limit_exceeded,
            }
    except (ValueError, Exception, DataError, ProgrammingError, StatementError) as e:
        error_msg = (
            AppConfig.VALIDATION_ERROR[type(e).__name__]
            if type(e).__name__ in AppConfig.VALIDATION_ERROR
            else AppConfig.DATABASE_ERROR
        )
        logger.error(error_msg)
        self.update_state(
            state=states.FAILURE,
            meta={"exc_type": type(e).__name__, "exc_message": str(e)},
        )
        raise Ignore()
    
@app.task(bind=True)
def limit_check_all(self, client_id: str, filter: Optional[dict] = {}) -> dict:
    """Check if the limit is exceeded for all categories."""
    try:
        logger.info(f"Starting limit check for all categories for client_id: {client_id}")

        start_date = filter.get("start_date", None) if filter else datetime.now().replace(day=1).strftime("%Y-%m-%d")
        end_date = filter.get("end_date", None) if filter else ((datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")

        query = f"""
                with aggr_transactions_by_category as (
                    select
                        sum(transaction_revenue) as total_revenue,  
                        payment_category_id
                    from transactions
                    where
                        client_id = '{client_id}'
                        and transaction_type = 'Despesa'
                        and date(transaction_timestamp) between '{start_date}' and '{end_date}'
                    group by
                        payment_category_id
                )
                select
                    pc.payment_category_name,
                    pc.payment_category_id,
                    l.limit_value,
                    t.total_revenue
                from limits l
                    left join aggr_transactions_by_category t
                        on l.category_id = t.payment_category_id
                    left join payment_categories pc
                        on l.category_id = pc.payment_category_id
        """
        logger.info(f"Executing query:\n{query}")

        with db_manager.get_session() as session:
            dados = session.execute(text(query)).all()
            df = pd.DataFrame(dados)

            return {
                "status": "success",
                "message": "Limit check completed",
                "data": df.to_dict(orient="records"),
            }
    except (ValueError, Exception, DataError, ProgrammingError, StatementError) as e:
        error_msg = (
            AppConfig.VALIDATION_ERROR[type(e).__name__]
            if type(e).__name__ in AppConfig.VALIDATION_ERROR
            else AppConfig.DATABASE_ERROR
        )
        logger.error(error_msg)
        self.update_state(
            state=states.FAILURE,
            meta={"exc_type": type(e).__name__, "exc_message": str(e)},
        )
        raise Ignore()
    
@app.task(bind=True)
def get_user_info(self, client_id: str) -> dict:
    """Get user info."""
    try:
        logger.info(f"Starting user info retrieval for client_id: {client_id}")

        query = f"""
            select
                *
            from clients
            where
                client_id = '{client_id}'
        """
        logger.info(f"Executing query:\n{query}")

        with db_manager.get_session() as session:
            dados = session.execute(text(query)).all()
            df = pd.DataFrame(dados)

            return {
                "status": "success",
                "message": "User info retrieved successfully",
                "data": df.to_dict(orient="records")[0],
            }
    except (ValueError, Exception, DataError, ProgrammingError, StatementError) as e:
        error_msg = (
            AppConfig.VALIDATION_ERROR[type(e).__name__]
            if type(e).__name__ in AppConfig.VALIDATION_ERROR
            else AppConfig.DATABASE_ERROR
        )
        logger.error(error_msg)
        self.update_state(
            state=states.FAILURE,
            meta={"exc_type": type(e).__name__, "exc_message": str(e)},
        )
        raise Ignore()
    
@app.task(bind=True)
def list_all_cards(self, client_id: str, date: str) -> dict:
    """List all cards for a client."""
    try:
        logger.info(f"Starting list all cards for client_id: {client_id}")

        query = f"""
            select
                *
            from cards
            where
                client_id = '{client_id}'
        """
        logger.info(f"Executing query:\n{query}")

        detailed_query = f"""
            with transactions_by_card as (
                select
                    transaction_id,
                    card_id,
                    transaction_type,
                    transaction_revenue,
                    payment_description,
                    payment_categories.payment_category_name,
                    payment_methods.payment_method_name,
                    date(transaction_timestamp) as transaction_date,
                    installment_payment,
                    installment_number
                from transactions
                    left join payment_categories 
                        on transactions.payment_category_id = payment_categories.payment_category_id
                    left join payment_methods 
                        on transactions.payment_method_id = payment_methods.payment_method_id
                where
                    client_id = '{client_id}'
                    and card_id is not null
                    and date_trunc('month', transaction_timestamp) = date_trunc('month', '{date}'::timestamp)
            )
            select
                c.card_id,
                c.card_name,
                c.payment_date,
                t.transaction_date,
                t.transaction_id,
                t.transaction_type,
                t.transaction_revenue,
                t.payment_description,
                t.payment_category_name,
                t.payment_method_name,
                t.installment_payment,
                t.installment_number
            from cards c
                left join transactions_by_card t
                    on c.card_id = t.card_id
        """
        logger.info(f"Executing query:\n{detailed_query}")

        with db_manager.get_session() as session:
            detailed_dados = session.execute(text(detailed_query)).all()
            detailed_df = pd.DataFrame(detailed_dados)

            dados = session.execute(text(query)).all()
            df = pd.DataFrame(dados)

            # Constrói lista de cartões e mapeia detalhes por card_id
            cards_list = df.to_dict(orient="records")
            detailed_records = detailed_df.to_dict(orient="records")

            credit_by_card = {}
            debit_by_card = {}
            for record in detailed_records:
                card_id = record.get("card_id")
                payment_method_name = record.get("payment_method_name")
                if card_id is None:
                    continue
                if payment_method_name == "Crédito":
                    credit_by_card.setdefault(card_id, []).append(record)
                elif payment_method_name == "Débito":
                    debit_by_card.setdefault(card_id, []).append(record)
                else:
                    continue

            # Adiciona os detalhes correspondentes a cada cartão
            for card in cards_list:
                card_id = card.get("card_id")
                card["credit"] = credit_by_card.get(card_id, [])
                card["debit"] = debit_by_card.get(card_id, [])

            data = {
                "cards": cards_list,
            }

            return {
                "status": "success",
                "message": "Cards list retrieved successfully",
                "data": data,
            }
    except (ValueError, Exception, DataError, ProgrammingError, StatementError) as e:
        error_msg = (
            AppConfig.VALIDATION_ERROR[type(e).__name__]
            if type(e).__name__ in AppConfig.VALIDATION_ERROR
            else AppConfig.DATABASE_ERROR
        )
        logger.error(error_msg)
        self.update_state(
            state=states.FAILURE,
            meta={"exc_type": type(e).__name__, "exc_message": str(e)},
        )
        raise Ignore()
    
# @app.task(bind=True)
# def get_card_extract(self, client_id: str, card_id: str) -> dict:
#     """Get card extract."""
#     try:
#         logger.info(f"Starting card extract for client_id: {client_id}, card_id: {card_id}")
        
#         query = f"""
#             select
#                 *
#             from transactions
#             where
#                 client_id = '{client_id}'
#                 and card_id = '{card_id}'
#     except (ValueError, Exception, DataError, ProgrammingError, StatementError) as e:

# def limit_check_debug(
#         client_id: str,
#         category_id: str
#     ):
#     """Check if the limit is exceeded."""
#     try:
#         logger.info(f"Starting limit check for client_id: {client_id}, category_id: {category_id}")

#         query = f"""
#             SELECT
#                 SUM(transaction_revenue) as total_revenue
#             FROM transactions
#             WHERE
#                 client_id = '{client_id}'
#                 AND payment_category_id = '{category_id}'
#                 AND date_trunc('month', transaction_timestamp) = date_trunc('month', CURRENT_DATE)
#         """

#         with db_manager.get_session() as session:
#             dados = session.execute(text(query)).all()
#             df = pd.DataFrame(dados)
#             total_revenue = df['total_revenue'].values[0]

#             limit_value = get_limits(client_id=client_id, category_id=category_id)

#             if total_revenue >= limit_value:
#                 return True
#             else: return False
#     except (ValueError, Exception, DataError, ProgrammingError, StatementError) as e:
#         error_msg = AppConfig.VALIDATION_ERROR[type(e).__name__] if type(e).__name__ in AppConfig.VALIDATION_ERROR else AppConfig.DATABASE_ERROR
#         logger.error(error_msg)
#         raise Ignore()

# print(limit_check_debug(client_id='4dfd378d-5782-44e4-8872-35778552abed', category_id='1'))
# def get_limits_debug(client_id: str, limit_category: str):
#     """Get limits for a client."""
#     try:
#         logger.info(f"Starting limits retrieval for client_id: {client_id}")

#         query = f"""
#             SELECT * FROM limits WHERE client_id = '{client_id}' AND limit_category = '{limit_category}'
#         """

#         with db_manager.get_session() as session:
#             dados = session.execute(text(query)).all()
#             df = pd.DataFrame(dados)
#             logger.info(f"Limits retrieval completed successfully for client_id: {client_id}")
#             return df
#     except (ValueError, Exception, DataError, ProgrammingError, StatementError) as e:
#         error_msg = AppConfig.VALIDATION_ERROR[type(e).__name__] if type(e).__name__ in AppConfig.VALIDATION_ERROR else AppConfig.DATABASE_ERROR
#         logger.error(error_msg)
#         raise Ignore()

# print(get_limits_debug(client_id='4dfd378d-5782-44e4-8872-35778552abed', limit_category='Alimentação'))

# def generate_extrato(
#         client_id: str,
#         start_date: Optional[str] = None,
#         end_date: Optional[str] = None,
#         days_before: Optional[int] = None,
#         detailed: Optional[dict] = None
#     ):
#     # try:
#     logger.info(f"Starting extract generation for client_id: {client_id}")

#     columns = ['client_id', 'transaction_timestamp', 'transaction_revenue', 'payment_location', 'payment_method_name', 'payment_product'] if detailed else ['client_id', 'transaction_timestamp', 'transaction_revenue']

#     if not start_date and not days_before:
#         error_msg = AppConfig.VALIDATION_ERROR["start_date_or_days_before_required"]
#         logger.error(f"Validation error: {error_msg}")
#         raise ValueError(error_msg)
#     elif days_before:
#         start_date = (datetime.now() - timedelta(days=days_before)).strftime('%Y-%m-%d')
#         end_date = datetime.now().strftime('%Y-%m-%d')
#     elif start_date and not end_date:
#         end_date = start_date

#     query = f"""
#             SELECT
#                 {', '.join(columns)}
#             FROM transactions
#             -- WHERE
#                 -- client_id = '{client_id}'
#                 -- AND date(transaction_timestamp) BETWEEN '{start_date}' AND '{end_date}'
#             """

#     with db_manager.get_session() as session:
#         dados = session.execute(text(query)).all()
#         df = pd.DataFrame(dados, columns=columns)

#         df['transaction_timestamp'] = pd.to_datetime(df['transaction_timestamp'])

#         if detailed:
#             if detailed["mode"] == "day":
#                 df['transaction_timestamp'] = df['transaction_timestamp'].dt.strftime('%Y-%m-%d')
#             elif detailed["mode"] == "week":
#                 df['transaction_timestamp'] = df['transaction_timestamp'].dt.strftime('%Y-%m-%W')
#             elif detailed["mode"] == "month":
#                 df['transaction_timestamp'] = df['transaction_timestamp'].dt.strftime('%Y-%m')
#             elif detailed["mode"] == "year":
#                 df['transaction_timestamp'] = df['transaction_timestamp'].dt.strftime('%Y')
#             else:
#                 pass
#                 # error_msg = AppConfig.VALIDATION_ERROR["invalid_detailed_mode"]
#                 # logger.error(f"Validation error: {error_msg}")
#                 # self.update_state(state=states.FAILURE, meta={
#                 #     'exc_type': str(ValueError),
#                 #     'exc_message': error_msg
#                 # })
#                 # raise ValueError(error_msg)

#         if not detailed or detailed["activated"] == False:
#             extrato = df.groupby(['transaction_timestamp'])['transaction_revenue'].sum()
#         else:
#             extrato = df

#         result = extrato.to_csv('data/data.csv', index=True)
#         logger.info(f"Extract generation completed successfully for client_id: {client_id}")
#         return {"status": "success", "message": "Extract generated successfully", "data": result}

# except ValueError as e:
#     error_msg = f"Validation error in generate_extract: {str(e)}"
#     logger.error(error_msg)
#     self.update_state(state=states.FAILURE, meta={
#         'exc_type': type(e).__name__,
#         'exc_message': str(e)
#     })
#     raise Ignore()
# except (DataError, ProgrammingError, StatementError) as e:
#     error_msg = f"Database error in generate_extract: {str(e)}"
#     logger.error(error_msg)
#     self.update_state(state=states.FAILURE, meta={
#         'exc_type': type(e).__name__,
#         'exc_message': str(e)
#     })
#     raise Ignore()
# except Exception as e:
#     error_msg = AppConfig.VALIDATION_ERROR["unexpected_error"]
#     logger.error(error_msg)
#     self.update_state(state=states.FAILURE, meta={
#         'exc_type': type(e).__name__,
#         'exc_message': str(e)
#     })
#     raise Ignore()

# print(generate_extrato(client_id='e1b043b5-0d52-4883-8fe9-1de12f755b2d', start_date='2025-04-01', end_date='2025-04-30', detailed={"mode": "day", "activated": False}))
