import sys

from loguru import logger

from .settings import get_settings

settings = get_settings()


def setup_logger():
    """
    Configure Logger
    """
    logger.remove()

    log_level = settings.log_level

    logger.add(
        sys.stderr,
        level=log_level.upper(),
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>",
    )

    logger.add(
        settings.log_sink,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level="DEBUG",
    )

    logger.info("Logger has been configured successfully.")
