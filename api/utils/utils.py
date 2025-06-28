import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import logging
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.exc import DataError, ProgrammingError, StatementError
from database_manager.connector import DatabaseManager


def configure_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/utils.log"),
            logging.StreamHandler()
        ]
    )
    # Reduce noise from libraries
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
    logging.getLogger("psycopg2").setLevel(logging.ERROR)

configure_logging()
logger = logging.getLogger(__name__)

db_manager = DatabaseManager()

def get_start_end_date(days_before: int) -> tuple[str, str]:
    """
    Get the start date for the extract.
    """
    start_date = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_before)).strftime('%Y-%m-%d') if days_before > 0 else datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    return start_date, end_date

def make_where_string(filter: dict) -> str:
    """
    Make the where string for the query.
    """
    conditions = []
    for key, value in filter.items():
        conditions.append(f"{key} {value["operator"]} '{value["value"]}'")

    return " and ".join(conditions)

def make_aggr_logic(mode: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Make the aggr logic for the query.
    """
    modes = {
        "day": "D",
        "week": "W",
        "month": "ME",
        "year": "YE"
    }
    df = df.set_index('transaction_timestamp').resample(modes[mode]).agg({'transaction_revenue': 'sum'}).reset_index()

    return df

def get_limits(client_id: str, category_id: str) -> float:
    """Get limits for a client."""
    query = text("""
        SELECT * FROM limits WHERE client_id = :client_id AND category_id = :category_id
    """)

    with db_manager.get_session() as session:
        dados = session.execute(query, {"client_id": client_id, "category_id": category_id}).all()
        
        # If no data is returned, return 0.0 (no limit)
        if not dados:
            logger.info(f"No limit found for client_id: {client_id}, category: {category_id}")
            return 0
        
        df = pd.DataFrame(dados)
        
        return df['limit_value'].values[0]
