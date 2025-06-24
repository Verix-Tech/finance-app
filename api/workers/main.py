import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import logging
from os import getenv
from typing import Optional
from sqlalchemy import text
from celery import Celery, states
from celery.exceptions import Ignore, Reject
from sqlalchemy.exc import DataError, ProgrammingError, StatementError

from database_manager.connector import DatabaseManager
from database_manager.models.models import Transaction
from utils import get_start_end_date


# Configure logging
logger = logging.getLogger(__name__)

# Get Redis configuration with fallback
redis_server = getenv('REDIS_SERVER', 'redis://localhost:6379')
logger.info(f"Configuring Celery with Redis broker: {redis_server}")

try:
    app = Celery('tasks', broker=redis_server, backend=redis_server)
    logger.info("Celery app configured successfully")
    
    # Configure Celery settings for Docker environment
    app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
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
        "invalid_detailed_mode": "Invalid detailed mode",
        "generate_extract_error": "Unexpected error in generate_extract",
        "unexpected_error": "Unexpected error in generate_extract"
    }


@app.task(bind=True)
def generate_extract(
        self,
        client_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days_before: Optional[str] = None,
        aggr: Optional[dict] = None
    ) -> str:
    """Generate extract for a client with proper error handling."""
    try:
        logger.info(f"Starting extract generation for client_id: {client_id}")
        
        columns = ['client_id', 'transaction_timestamp', 'transaction_revenue', 'payment_description', 'payment_category', 'transaction_type'] if aggr else ['client_id', 'transaction_timestamp', 'transaction_revenue']

        if not start_date and not days_before:
            error_msg = AppConfig.VALIDATION_ERROR["start_date_or_days_before_required"]
            logger.error(f"Validation error: {error_msg}")
            raise ValueError(error_msg)
        elif days_before:
            start_date, end_date = get_start_end_date(int(days_before))
        elif start_date and not end_date:
            end_date = start_date

        query = f"""
                SELECT 
                    {', '.join(columns)}
                FROM transactions
                WHERE
                    client_id = '{client_id}'
                    AND date(transaction_timestamp) BETWEEN '{start_date}' AND '{end_date}'
                """
        
        with db_manager.get_session() as session:
            dados = session.execute(text(query)).all()
            df = pd.DataFrame(dados, columns=columns)

            df['transaction_timestamp'] = pd.to_datetime(df['transaction_timestamp'])

            if aggr and aggr["activated"] == True:
                if aggr["mode"] == "day":
                    df = df.set_index('transaction_timestamp').resample('D').agg({'transaction_revenue': 'sum'}).reset_index()
                elif aggr["mode"] == "week":
                    df = df.set_index('transaction_timestamp').resample('W').agg({'transaction_revenue': 'sum'}).reset_index()
                elif aggr["mode"] == "month":
                    df = df.set_index('transaction_timestamp').resample('ME').agg({'transaction_revenue': 'sum'}).reset_index()
                elif aggr["mode"] == "year":
                    df = df.set_index('transaction_timestamp').resample('YE').agg({'transaction_revenue': 'sum'}).reset_index()
                else:
                    error_msg = AppConfig.VALIDATION_ERROR["invalid_aggr_mode"]
                    logger.error(f"Validation error: {error_msg}")
                    self.update_state(state=states.FAILURE, meta={
                        'exc_type': str(ValueError),
                        'exc_message': error_msg
                    })
                    raise ValueError(error_msg)

            else: pass
            
            df["transaction_timestamp"] = df["transaction_timestamp"].dt.strftime('%Y-%m-%d')
            result = df.to_csv(index=True)
            logger.info(f"Extract generation completed successfully for client_id: {client_id}")
            return result
            
    except ValueError as e:
        error_msg = f"Validation error in generate_extract: {str(e)}"
        logger.error(error_msg)
        self.update_state(state=states.FAILURE, meta={
            'exc_type': type(e).__name__,
            'exc_message': str(e)
        })
        raise Ignore()
    except (DataError, ProgrammingError, StatementError) as e:
        error_msg = f"Database error in generate_extract: {str(e)}"
        logger.error(error_msg)
        self.update_state(state=states.FAILURE, meta={
            'exc_type': type(e).__name__,
            'exc_message': str(e)
        })
        raise Ignore()
    except Exception as e:
        error_msg = AppConfig.VALIDATION_ERROR["unexpected_error"]
        logger.error(error_msg)
        self.update_state(state=states.FAILURE, meta={
            'exc_type': type(e).__name__,
            'exc_message': str(e)
        })
        raise Ignore()


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
