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
    SQS_QUEUE_ARN: str
    HEALTH_CHECK_PORT: int = Field(ge=1024, lt=65535)
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARN", "ERROR"] = "INFO"
