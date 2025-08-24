"""
日志配置模块
使用 loguru 进行日志管理，提供简单而强大的日志功能
"""

import sys
import os
from pathlib import Path
from loguru import logger


def setup_logging(
    debug: bool = False,
    log_level: str = "INFO",
    app_name: str = "grub-theme",
    log_dir: str = "logs"
) -> logger:
    """
    一键配置日志系统
    
    Args:
        debug: 是否为调试模式
        log_level: 日志级别
        app_name: 应用名称，用于日志文件命名
        log_dir: 日志目录
        
    Returns:
        配置好的logger实例
    """
    
    # 清除所有默认配置
    logger.remove()
    
    # 根据debug模式调整日志级别
    console_level = "DEBUG" if debug else log_level
    
    # 控制台输出配置（带颜色和详细格式）
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    logger.add(
        sys.stdout,
        format=console_format,
        level=console_level,
        colorize=True,
        backtrace=debug,  # 调试模式显示完整堆栈
        diagnose=debug   # 调试模式显示变量值
    )
    
    # 文件输出配置
    if not debug or os.getenv("FORCE_FILE_LOGGING", "").lower() == "true":
        # 确保日志目录存在
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # 普通日志文件（按日期轮转）
        logger.add(
            log_path / f"{app_name}_{{time:YYYY-MM-DD}}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="INFO",
            rotation="00:00",  # 每天午夜轮转
            retention="30 days",  # 保留30天
            compression="zip",  # 压缩旧日志
            encoding="utf-8"
        )
        
        # 错误日志文件（单独记录错误）
        logger.add(
            log_path / f"{app_name}_errors_{{time:YYYY-MM-DD}}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="ERROR",
            rotation="10 MB",  # 按大小轮转
            retention="90 days",  # 错误日志保留更久
            compression="zip",
            encoding="utf-8",
            backtrace=True,    # 错误日志总是显示堆栈
            diagnose=True      # 错误日志总是显示变量
        )
    
    # 添加性能日志过滤器（可选）
    def performance_filter(record):
        """性能相关的日志过滤器"""
        return "performance" in record["extra"]
    
    # 性能日志（如果需要）
    if debug:
        # 在调试模式下，性能日志输出到stderr，不需要rotation参数
        logger.add(
            sys.stderr,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | PERF | {message}",
            level="DEBUG",
            filter=performance_filter
        )
    
    return logger


def get_logger(name: str = None):
    """
    获取logger实例
    
    Args:
        name: logger名称，通常使用 __name__
        
    Returns:
        logger实例
    """
    if name:
        return logger.bind(name=name)
    return logger


# 性能日志装饰器
def log_performance(func):
    """
    装饰器：记录函数执行时间
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            logger.bind(performance=True).debug(
                f"{func.__name__} executed in {execution_time:.4f}s"
            )
            return result
        except Exception as e:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            logger.bind(performance=True).error(
                f"{func.__name__} failed after {execution_time:.4f}s: {e}"
            )
            raise
    
    return wrapper


# 使用示例：
# from config import settings
# from logging_setup import setup_logging, get_logger
#
# # 初始化日志系统
# setup_logging(
#     debug=settings.debug,
#     log_level=settings.log_level,
#     app_name=settings.app_name
# )
#
# # 获取logger并使用
# logger = get_logger(__name__)
# logger.info("应用启动成功")
# logger.debug("这是调试信息")
# logger.error("这是错误信息")
#
# # 使用性能装饰器
# @log_performance
# def slow_function():
#     import time
#     time.sleep(1)
#     return "done"