"""Common Pydantic v2 base models used across contexts."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    """Base for every response model that maps from an ORM object."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Timestamped(ORMModel):
    created_at: datetime
    updated_at: datetime


class IDModel(ORMModel):
    id: uuid.UUID


class Message(ORMModel):
    message: str


class Health(ORMModel):
    status: str = "ok"
    version: str
    env: str
