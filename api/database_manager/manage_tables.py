import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

import logging
import os
from os import getenv
from urllib.parse import quote_plus
from sqlalchemy import text
from database_manager.connector import DatabaseManager
from database_manager.models.models import (
    Base,
    Transaction,
    Client,
    PaymentMethod,
    PaymentCategory,
)
from auth.auth import create_user, UserCreate


def configure_logging():
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/manage_tables.log"),
            logging.StreamHandler(),
        ],
    )
    logging.getLogger(__file__).setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
    logging.getLogger("psycopg2").setLevel(logging.ERROR)


configure_logging()
logger = logging.getLogger(__name__)

# Getting a postgresql session
db_manager = DatabaseManager()
db_manager.check_connection()
db_session = db_manager.get_session()


def _get_password() -> str:
    password_file = getenv("ADMIN_PASSWORD")
    try:
        if not password_file:
            raise ValueError("ADMIN_PASSWORD environment variable is not set")
        with open(password_file, encoding="utf-8") as file:
            return quote_plus(str(file.read()))
    except FileNotFoundError:
        raise ValueError(f"Password file not found: {password_file}")


def create_tables():
    try:
        Base.metadata.create_all(db_session.get_bind())
        logger.info("All tables created successfully!")
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        db_session.rollback()


def drop_tables():
    try:
        Base.metadata.drop_all(db_session.get_bind())
        logger.info("All tables dropped successfully!")
    except Exception as e:
        logger.error(f"Error dropping tables: {str(e)}")
        db_session.rollback()


def create_users():
    try:
        create_user(
            UserCreate(
                username=getenv("ADMIN_USERNAME") or "",
                email=getenv("ADMIN_EMAIL") or "",
                full_name=getenv("ADMIN_FULL_NAME") or "",
                phone=getenv("ADMIN_PHONE") or "",
                disabled=False,
                password=_get_password(),
            )
        )
        logger.info("Admin user created successfully!")
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        db_session.rollback()


def create_payment_methods():
    try:
        db_session.execute(
            text(
                "INSERT INTO payment_methods (payment_method_id, payment_method_name) VALUES ('1', 'Pix'), ('2', 'Crédito'), ('3', 'Débito'), ('4', 'Dinheiro')"
            )
        )
        db_session.commit()
        logger.info("Payment methods created successfully!")
    except Exception as e:
        logger.error(f"Error creating payment methods: {str(e)}")
        db_session.rollback()


def create_payment_categories():
    try:
        db_session.execute(
            text(
                "INSERT INTO payment_categories (payment_category_id, payment_category_name) VALUES ('1', 'Alimentação'), ('2', 'Saúde'), ('3', 'Salário'), ('4', 'Investimentos'), ('5', 'Pet'), ('6', 'Contas'), ('7', 'Educação'), ('8', 'Lazer'), ('0', 'Outros')"
            )
        )
        db_session.commit()
        logger.info("Payment categories created successfully!")
    except Exception as e:
        logger.error(f"Error creating payment categories: {str(e)}")
        db_session.rollback()


# Calling functions
args = sys.argv
globals()[args[1]]()
