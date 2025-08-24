"""
数据模型定义
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from enum import Enum


class ThemeStatus(Enum):
    """主题状态"""
    ACTIVE = "active"
    AVAILABLE = "available"
    ERROR = "error"


@dataclass
class Theme:
    """GRUB主题数据模型"""
    name: str
    path: Path
    description: Optional[str] = None
    preview_image: Optional[Path] = None
    status: ThemeStatus = ThemeStatus.AVAILABLE
    
    @property
    def is_valid(self) -> bool:
        """检查主题是否有效"""
        if not (self.path.exists() and self.path.is_dir()):
            return False
        
        # 检查常见的主题配置文件名
        theme_files = ["theme.txt", "Theme.txt", "THEME.TXT", "theme.conf"]
        return any((self.path / theme_file).exists() for theme_file in theme_files)
    
    def __str__(self) -> str:
        return f"{self.name} ({self.status.value})"


@dataclass
class ThemeOperation:
    """主题操作结果"""
    success: bool
    message: str
    theme: Optional[Theme] = None
    error: Optional[Exception] = None