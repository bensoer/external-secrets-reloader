from dataclasses import dataclass
from enum import Enum
from os import environ
from typing import Literal

from pydantic_settings import BaseSettings

from pydantic import (
    AliasChoices,
    AmqpDsn,
    BaseModel,
    Field,
    ImportString,
    PostgresDsn,
    RedisDsn,
    model_validator
)

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SQS_QUEUE_URL: str | None = None
    SQS_QUEUE_WAIT_TIME: int | None = Field(gt=0, le=60, default=10, description="Amount of Time SQS Client Will Wait For Events Before Timeout. App will check whether to continue between timeouts")

        
    EVENT_SOURCE: Literal["AWS"]
    EVENT_SERVICE: Literal["ParameterStore", "SecretsManager"]



    HEALTH_CHECK_PORT: int = Field(ge=1024, lt=65535, default=8080, description="Port the Health Check Endpoints Are Served Over")
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARN", "ERROR"] = "INFO"


    @model_validator(mode='after')
    def validate_cloud_dependencies(self) -> 'Settings':
        
        if self.EVENT_SOURCE == "AWS":
            valid_aws_services = ["ParameterStore", "SecretsManager"]
            
            # 1. EVENT_SOURCE Check: Must be a valid AWS source
            if self.EVENT_SERVICE not in valid_aws_services:
                raise ValueError(
                    f"EVENT_SERVICE '{self.EVENT_SERVICE}' is invalid for EVENT_SOURCE='AWS'. "
                    f"Must be one of: {valid_aws_services}"
                )
            
            # 2. Required Fields Check: SQS settings are mandatory for AWS
            if self.SQS_QUEUE_URL is None:
                raise ValueError("SQS_QUEUE_URL is required when EVENT_CLOUD='AWS'.")