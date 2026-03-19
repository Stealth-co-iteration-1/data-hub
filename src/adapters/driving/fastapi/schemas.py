"""Pydantic schemas for FastAPI request/response models."""

from pydantic import BaseModel


class WebhookResponse(BaseModel):
    """Standard webhook response."""

    status: str


class ErrorResponse(BaseModel):
    """Error response for 4xx/5xx."""

    error: str
