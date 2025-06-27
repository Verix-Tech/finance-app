from sqlalchemy import Column, String, Boolean, Float, Integer, DateTime, UniqueConstraint, Index
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

    internal_transaction_id = Column(String, primary_key=True)
    transaction_id = Column(Integer, nullable=False)
    client_id = Column(String, nullable=False)
    transaction_type = Column(String, nullable=False)
    transaction_revenue = Column(Float)
    payment_method_id = Column(String)
    payment_description = Column(String)
    payment_category_id = Column(String)
    transaction_timestamp = Column(DateTime(timezone=True), nullable=False)

class Limits(Base):
    __tablename__ = 'limits'
    __table_args__ = (
        UniqueConstraint('client_id', 'category_id', name='unique_client_id_category_id'),
        {'schema': 'public'}
    )

    limit_id = Column(String, primary_key=True)
    client_id = Column(String, nullable=False)
    category_id = Column(String, nullable=False)
    limit_value = Column(Float)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

class PaymentMethod(Base):
    __tablename__ = 'payment_methods'
    __table_args__ = {'schema': 'public'}

    payment_method_id = Column(String, primary_key=True)
    payment_method_name = Column(String)

class PaymentCategory(Base):
    __tablename__ = 'payment_categories'
    __table_args__ = {'schema': 'public'}

    payment_category_id = Column(String, primary_key=True)
    payment_category_name = Column(String)

class Client(Base):
    __tablename__ = 'clients'
    __table_args__ = (
        UniqueConstraint('client_id', name='clients_unique'),
        {'schema': 'public'}
    )

    client_id = Column(String, primary_key=True)
    platform_id = Column(String)
    platform_name = Column(String)
    name = Column(String)
    phone = Column(String)
    created_at = Column(String)
    updated_at = Column(String)
    subscribed = Column(Boolean)
    subs_start_timestamp = Column(DateTime(timezone=True))
    subs_end_timestamp = Column(DateTime(timezone=True)) 
