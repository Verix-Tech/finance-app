from typing import Optional, Dict, Any, Union, List
from pydantic import BaseModel, Field
from datetime import datetime


class CreateUserRequest(BaseModel):
    platform_id: str = Field(..., description="Platform identifier")
    platform_name: str = Field(..., description="Platform name")
    name: str = Field(..., description="User name")
    phone: str = Field(..., description="User phone number")


class CreateTransactionRequest(BaseModel):
    platform_id: str = Field(..., description="Platform identifier")
    transaction_revenue: float = Field(..., description="Transaction amount")
    transaction_type: str = Field(..., description="Transaction type")
    transaction_timestamp: Optional[str] = Field(
        None, description="Transaction timestamp"
    )
    payment_method_id: Optional[str] = Field(None, description="Payment method ID")
    payment_description: Optional[str] = Field(None, description="Payment description")
    payment_category_id: Optional[str] = Field(None, description="Payment category ID")


class UpdateTransactionRequest(BaseModel):
    platform_id: str = Field(..., description="Platform identifier")
    transactionId: int = Field(..., description="Transaction ID to update")
    transaction_revenue: Optional[float] = Field(None, description="Transaction amount")
    transaction_type: Optional[str] = Field(None, description="Transaction type")
    transaction_timestamp: Optional[str] = Field(
        None, description="Transaction timestamp"
    )
    payment_method_id: Optional[str] = Field(None, description="Payment method ID")
    payment_description: Optional[str] = Field(None, description="Payment description")
    payment_category_id: Optional[str] = Field(None, description="Payment category ID")


class DeleteTransactionRequest(BaseModel):
    platform_id: str = Field(..., description="Platform identifier")
    transaction_id: Optional[Union[int, List[int]]] = Field(
        None, description="Transaction ID to delete"
    )
    transaction_timestamp: Optional[str] = Field(
        None, description="Transaction timestamp filter"
    )
    payment_method_id: Optional[str] = Field(
        None, description="Payment method ID filter"
    )
    payment_category_id: Optional[str] = Field(
        None, description="Payment category ID filter"
    )


class CreateLimitRequest(BaseModel):
    platform_id: str = Field(..., description="Platform identifier")
    category_id: str = Field(..., description="Category ID")
    limit_value: float = Field(..., description="Limit value")


class LimitCheckRequest(BaseModel):
    platform_id: str = Field(..., description="Platform identifier")
    category_id: str = Field(..., description="Category ID")

class LimitCheckAllRequest(BaseModel):
    platform_id: str = Field(..., description="Platform identifier")
    filter: Optional[dict] = Field(None, description="Filter criteria")

class GrantSubscriptionRequest(BaseModel):
    platform_id: str = Field(..., description="Platform identifier")
    subscriptionMonths: int = Field(..., description="Number of subscription months")


class RevokeSubscriptionRequest(BaseModel):
    platform_id: str = Field(..., description="Platform identifier")


class GenerateReportRequest(BaseModel):
    platform_id: str = Field(..., description="Platform identifier")
    start_date: Optional[str] = Field(None, description="Start date for report")
    end_date: Optional[str] = Field(None, description="End date for report")
    days_before: Optional[int] = Field(None, description="Days before current date")
    aggr: Optional[dict] = Field(None, description="Aggregation type")
    filter: Optional[dict] = Field(None, description="Filter criteria")


class ClientExistsRequest(BaseModel):
    platform_id: str = Field(..., description="Platform identifier")
