from typing import Optional, Dict, Any, Union, List
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")


class SuccessResponse(BaseModel):
    status: str = Field(..., description="Response status")
    data: Dict[str, Any] = Field(..., description="Response data")
    message: str = Field(..., description="Success message")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type")


class LimitCheckResponse(BaseModel):
    limit_value: float = Field(..., description="Limit value")
    current_spent: float = Field(..., description="Current amount spent")
    remaining: float = Field(..., description="Remaining amount")
    is_exceeded: bool = Field(..., description="Whether limit is exceeded")


class ListAllCardsResponse(BaseModel):
    cards: List[Dict[str, Any]] = Field(..., description="List of cards")
