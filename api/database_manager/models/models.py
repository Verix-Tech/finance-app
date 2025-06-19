from sqlalchemy import Column, String, Boolean, Float, Integer, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'schema': 'public'}

    username = Column(String, primary_key=True)
    email = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    disabled = Column(Boolean, nullable=False)
    hashed_password = Column(String, nullable=False)

class Transaction(Base):
    __tablename__ = 'transactions'
    __table_args__ = {'schema': 'public'}

    __all__ = ['internal_transaction_id', 'transaction_id', 'client_id', 'transaction_revenue', 'payment_method_name', 'payment_location', 'payment_product', 'transaction_timestamp']

    internal_transaction_id = Column(String, primary_key=True)
    transaction_id = Column(Integer, nullable=False)
    client_id = Column(String, nullable=False)
    transaction_revenue = Column(Float)
    payment_method_name = Column(String)
    payment_location = Column(String)
    payment_product = Column(String)
    transaction_timestamp = Column(DateTime(timezone=True), nullable=False)

class Client(Base):
    __tablename__ = 'clients'
    __table_args__ = (
        UniqueConstraint('client_id', name='clients_unique'),
        {'schema': 'public'}
    )

    client_id = Column(String, primary_key=True)
    name = Column(String)
    phone = Column(String)
    created_at = Column(String)
    updated_at = Column(String)
    subscribed = Column(Boolean)
    subs_start_timestamp = Column(DateTime(timezone=True))
    subs_end_timestamp = Column(DateTime(timezone=True)) 
