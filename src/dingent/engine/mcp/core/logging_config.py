import sys

from loguru import logger

from .settings import get_settings  # 从你的设置文件中读取配置

settings = get_settings()


def setup_logger():
    """
    配置全局唯一的 logger
    """
    logger.remove()

    # 从 settings.py 读取配置，这让配置更加灵活
    log_level = settings.log_level

    # 添加控制台输出
    logger.add(
        sys.stderr,
        level=log_level.upper(),
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>",
    )

    # 添加文件输出
    logger.add(
        settings.log_sink,  # 日志文件路径也从配置读取
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level="DEBUG",  # 文件总是记录 DEBUG 级别，方便排查问题
    )

    logger.info("Logger has been configured successfully.")
