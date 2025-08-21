import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import logging
import os
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.exc import DataError, ProgrammingError, StatementError
from database_manager.connector import DatabaseManager


def configure_logging():
    """Configure application logging."""
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("logs/utils.log"), logging.StreamHandler()],
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
    start_date = (
        (
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            - timedelta(days=days_before)
        ).strftime("%Y-%m-%d")
        if days_before > 0
        else datetime.now()
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .strftime("%Y-%m-%d")
    )
    end_date = datetime.now().strftime("%Y-%m-%d")
    return start_date, end_date


def make_where_string(filter: dict) -> str:
    """
    Make the where string for the query.
    """
    conditions = []
    for key, value in filter.items():
        conditions.append(f"{key} {value['operator']} {repr(value['value'])}")

    return " and ".join(conditions)


def make_aggr_logic(mode: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Make the aggr logic for the query.
    """
    modes = {"day": "D", "week": "W", "month": "ME", "year": "YE"}
    df = (
        df.set_index("transaction_timestamp")
        .resample(modes[mode])
        .agg({"transaction_revenue": "sum"})
        .reset_index()
    )

    return df


def get_limits(client_id: str, category_id: str) -> float:
    """Get limits for a client."""
    query = text(
        """
        SELECT * FROM limits WHERE client_id = :client_id AND category_id = :category_id
    """
    )

    with db_manager.get_session() as session:
        dados = session.execute(
            query, {"client_id": client_id, "category_id": category_id}
        ).all()

        # If no data is returned, return 0.0 (no limit)
        if not dados:
            logger.info(
                f"No limit found for client_id: {client_id}, category: {category_id}"
            )
            return 0

        df = pd.DataFrame(dados)

        return df["limit_value"].values[0]


def validate_and_format_date(date_str: str) -> str:
    """
    Validate and standardize a date string.

    Supported input formats:
        1. "%Y-%m-%d"  (ISO / database default)
        2. "%d/%m/%Y"  (common BR format)

    If the input comes in the second format it will be converted to the
    canonical "%Y-%m-%d" format used by the API/database layer.

    Args:
        date_str: Date string received in the request body/query-params.

    Returns:
        A string with the date represented as "%Y-%m-%d".

    Raises:
        ValueError: When the supplied string is not a valid date or does not
                     match any of the supported formats.
    """
    if not isinstance(date_str, str):
        raise ValueError("`date_str` must be a string in 'YYYY-MM-DD' or 'DD/MM/YYYY' format.")

    logger.debug("Validating incoming date: %s", date_str)

    # 1. Try ISO format first – already in the desired layout
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        logger.debug("Date is already in ISO format.")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        pass  # not ISO – try BR format next

    # 2. Try Brazilian format (DD/MM/YYYY) and convert
    try:
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        logger.debug("Date converted from BR format to ISO.")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        logger.error("Invalid date format received: %s", date_str)
        raise ValueError(
            "Invalid date format. Expected 'YYYY-MM-DD' or 'DD/MM/YYYY'."
        ) from None
