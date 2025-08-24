"""
配置管理模块
使用 Pydantic Settings 进行配置管理，支持环境变量和.env文件
提供完美的IDE类型提示和自动补全
"""

from pydantic import Field
from pydantic_settings import BaseSettings





class Settings(BaseSettings):
    app_name: str = Field(default="grub-theme")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    environment: str = Field(default="development")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"  # 忽略额外字段
    }


# 全局配置实例
settings = Settings()

# 日志配置集成
def setup_app_logging():
    """初始化应用日志系统"""
    from logging_setup import setup_logging
    
    return setup_logging(
        debug=settings.debug,
        log_level=settings.log_level,
        app_name=settings.app_name
    )

# 使用示例：
# from config import settings, setup_app_logging
# from logging_setup import get_logger
#
# # 初始化日志
# setup_app_logging()
# logger = get_logger(__name__)
#
# # 使用配置
# logger.info(f"应用名称: {settings.app_name}")
# logger.debug(f"调试模式: {settings.debug}")  
# logger.info(f"数据库主机: {settings.database.host}")
# logger.info(f"数据库端口: {settings.database.port}")

# 环境变量覆盖示例：
# export DEBUG=true
# export DATABASE__HOST=192.168.1.100
# export DATABASE__PORT=3306