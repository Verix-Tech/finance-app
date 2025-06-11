import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

import logging
import os
from databaseManager.connector import DatabaseManager
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, InternalError, OperationalError, ArgumentError


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

# SQL DDL
sql_dir = 'sql/'
sql_content = os.listdir(sql_dir)

sql_files = [os.path.join(sql_dir, file) for file in sql_content if os.path.isfile(os.path.join(sql_dir, file)) and file != "privileges.sql"]

# Getting a postgresql session
db_manager = DatabaseManager()
db_manager.check_connection()
db_session = db_manager.get_session()

def create_tables():
    for file in sql_files:
        table = file.replace("sql/", "").replace(".sql", "")
        try:
            with open(file, 'r') as sql_script:
                query = sql_script.read()
                
            db_session.execute(text(query))
            db_session.commit()
            logger.info(f"Tabela '{table}' criada com sucesso!")
        except (ProgrammingError, InternalError):
            logger.error(f"Tabela '{table}' já existente.")

def drop_tables():
    for file in sql_files:
        table = file.replace("sql/", "").replace(".sql", "")
        try:
            query = f"""
                DROP TABLE {table};
            """
                
            db_session.execute(text(query))
            db_session.commit()
            logger.info(f"Tabela '{table}' deletada com sucesso!")
        except (ProgrammingError, InternalError):
            logger.error(f"Tabela '{table}' não existe.")



# Calling functions
args = sys.argv
globals()[args[1]]()
