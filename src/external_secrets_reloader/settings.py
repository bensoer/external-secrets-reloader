from dataclasses import dataclass
from enum import Enum
from os import environ
from typing import Literal

from pydantic import (
    AliasChoices,
    AmqpDsn,
    BaseModel,
    Field,
    ImportString,
    PostgresDsn,
    RedisDsn,
)

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SQS_QUEUE_URL: str
    SQS_QUEUE_WAIT_TIME: int = Field(gt=0, le=60, default=10, description="Amount of Time SQS Client Will Wait For Events Before Timeout. App will check whether to continue between timeouts")

    HEALTH_CHECK_PORT: int = Field(ge=1024, lt=65535, default=8080, description="Port the Health Check Endpoints Are Served Over")
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARN", "ERROR"] = "INFO"
