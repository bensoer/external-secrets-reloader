from dataclasses import dataclass
from enum import Enum
from os import environ



class EnvironmentVariables(Enum):
    SQS_QUEUE_ARN = "SQS_QUEUE_ARN"
    HEALTH_CHECK_PORT = "HEALTH_CHECK_PORT"
    LOG_LEVEL = "LOG_LEVEL"


@dataclass
class EnvironmentSettings():
    SQS_QUEUE_ARN: str
    HEALTH_CHECK_PORT: int
    LOG_LEVEL: str
    


class Settings():

    def __init__(self):
        
        self.environment_settings = EnvironmentSettings(
            SQS_QUEUE_ARN=environ.get(EnvironmentVariables.SQS_QUEUE_ARN),
            HEALTH_CHECK_PORT=int(environ.get(EnvironmentVariables.HEALTH_CHECK_PORT, '8080')),
            LOG_LEVEL = environ.get(EnvironmentVariables.LOG_LEVEL, "INFO")
        )

    def get_environment_settings(self) -> EnvironmentSettings:
        return self.environment_settings

