# logger.py
import logging
import time
import structlog
import ecs_logging
from config import settings
from datetime import datetime

# Configure structlog with ECS
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        ecs_logging.StructlogFormatter(),  # ECS format
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Get loggers
app_logger = structlog.get_logger("app")
db_logger = structlog.get_logger("database")
extraction_logger = structlog.get_logger("extraction")
http_logger = structlog.get_logger("http")