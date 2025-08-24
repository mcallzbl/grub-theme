"""
GUI抽象基类 - 定义接口，方便替换GUI框架
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from pathlib import Path

from core.models import Theme, ThemeOperation
from core.theme_manager import ThemeManager
import subprocess
import os


class SudoThemeManager:
    """带sudo权限管理的ThemeManager包装类"""
    
    def __init__(self, theme_manager: ThemeManager, gui: 'BaseThemeGUI'):
        self.theme_manager = theme_manager
        self.gui = gui
        self._sudo_password: Optional[str] = None
    
    def __getattr__(self, name):
        """代理所有不需要权限的方法到原始theme_manager"""
        return getattr(self.theme_manager, name)
    
    def _needs_sudo(self, operation: str) -> bool:
        """检查操作是否需要sudo权限"""
        return os.geteuid() != 0
    
    def _request_sudo_password(self, operation_name: str) -> bool:
        """请求sudo密码"""
        if not self._needs_sudo(operation_name):
            return True
            
        if not self._sudo_password:
            password = self.gui.prompt_sudo_password(operation_name)
            if password:
                self._sudo_password = password
                return True
            return False
        return True
    
    def _execute_with_sudo(self, operation_name: str, operation_func):
        """使用sudo权限执行操作"""
        if not self._needs_sudo(operation_name):
            return operation_func()
        
        if not self._request_sudo_password(operation_name):
            from core.models import ThemeOperation
            return ThemeOperation(False, "用户取消了权限请求")
        
        # 临时设置环境变量来传递密码给subprocess
        original_env = os.environ.copy()
        try:
            # 使用sudo执行操作
            return operation_func()
        except PermissionError:
            # 如果权限失败，清除缓存的密码并重试
            self._sudo_password = None
            if self._request_sudo_password(operation_name):
                return operation_func()
            else:
                from core.models import ThemeOperation
                return ThemeOperation(False, "权限验证失败")
        finally:
            os.environ.clear()
            os.environ.update(original_env)
    
    def set_theme(self, theme_name: str):
        """设定主题（需要sudo权限）"""
        return self._execute_with_sudo(
            f"设定主题: {theme_name}",
            lambda: self.theme_manager.set_theme(theme_name)
        )
    
    def random_theme(self):
        """随机选择主题（需要sudo权限）"""
        return self._execute_with_sudo(
            "随机选择主题",
            lambda: self.theme_manager.random_theme()
        )
    
    def install_theme_from_file(self, file_path: Path, theme_name: Optional[str] = None):
        """从文件安装主题（需要sudo权限）"""
        return self._execute_with_sudo(
            f"安装主题: {theme_name or file_path.name}",
            lambda: self.theme_manager.install_theme_from_file(file_path, theme_name)
        )
    
    def install_theme_from_url(self, url: str, theme_name: Optional[str] = None):
        """从URL安装主题（需要sudo权限）"""
        return self._execute_with_sudo(
            f"下载并安装主题: {theme_name or url}",
            lambda: self.theme_manager.install_theme_from_url(url, theme_name)
        )


class BaseThemeGUI(ABC):
    """主题GUI抽象基类"""
    
    def __init__(self, theme_manager: ThemeManager):
        self.theme_manager = theme_manager
        self.on_theme_changed: Optional[Callable[[str], None]] = None
        self.on_playlist_updated: Optional[Callable[[], None]] = None
    
    @abstractmethod
    def show(self) -> None:
        """显示GUI"""
        pass
    
    @abstractmethod
    def hide(self) -> None:
        """隐藏GUI"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """关闭GUI"""
        pass
    
    @abstractmethod
    def show_message(self, title: str, message: str, message_type: str = "info") -> None:
        """显示消息对话框
        
        Args:
            title: 对话框标题
            message: 消息内容
            message_type: 消息类型 ("info", "warning", "error", "success")
        """
        pass
    
    @abstractmethod
    def show_confirmation(self, title: str, message: str) -> bool:
        """显示确认对话框
        
        Args:
            title: 对话框标题
            message: 确认消息
            
        Returns:
            bool: 用户是否确认
        """
        pass
    
    @abstractmethod
    def select_file(self, title: str = "选择文件", 
                   filetypes: Optional[List[tuple]] = None) -> Optional[Path]:
        """文件选择对话框
        
        Args:
            title: 对话框标题
            filetypes: 文件类型过滤器 [("描述", "*.ext"), ...]
            
        Returns:
            Optional[Path]: 选择的文件路径
        """
        pass
    
    @abstractmethod
    def select_directory(self, title: str = "选择目录") -> Optional[Path]:
        """目录选择对话框
        
        Args:
            title: 对话框标题
            
        Returns:
            Optional[Path]: 选择的目录路径
        """
        pass
    
    @abstractmethod
    def prompt_input(self, title: str, prompt: str, 
                    default_value: str = "") -> Optional[str]:
        """输入对话框
        
        Args:
            title: 对话框标题
            prompt: 提示文本
            default_value: 默认值
            
        Returns:
            Optional[str]: 用户输入的文本
        """
        pass
    
    @abstractmethod
    def update_theme_list(self, themes: List[Theme]) -> None:
        """更新主题列表显示"""
        pass
    
    @abstractmethod
    def update_playlist(self, playlist: List[str]) -> None:
        """更新播放列表显示"""
        pass
    
    @abstractmethod
    def update_current_theme(self, theme_name: Optional[str]) -> None:
        """更新当前主题显示"""
        pass
    
    @abstractmethod
    def show_progress(self, title: str, message: str) -> None:
        """显示进度对话框"""
        pass
    
    @abstractmethod
    def hide_progress(self) -> None:
        """隐藏进度对话框"""
        pass
    
    def prompt_sudo_password(self, operation_name: str) -> Optional[str]:
        """弹出sudo密码输入对话框（子类需要重写）"""
        return None
    
    # 事件处理方法 - 子类可以重写
    def on_add_theme_file(self) -> None:
        """处理添加主题文件事件"""
        filetypes = [
            ("压缩文件", "*.zip *.tar *.tar.gz *.tgz *.gz"),
            ("ZIP文件", "*.zip"),
            ("TAR文件", "*.tar *.tar.gz *.tgz *.gz"),
            ("所有文件", "*.*")
        ]
        
        file_path = self.select_file("选择主题文件", filetypes)
        if file_path:
            self._install_theme_from_file(file_path)
    
    def on_add_theme_directory(self) -> None:
        """处理添加主题目录事件"""
        dir_path = self.select_directory("选择主题目录")
        if dir_path:
            self._install_theme_from_file(dir_path)
    
    def on_add_theme_url(self) -> None:
        """处理从URL添加主题事件"""
        url = self.prompt_input("添加主题", "请输入主题下载链接:")
        if url and url.strip():
            self._install_theme_from_url(url.strip())
    
    def on_set_theme(self, theme_name: str) -> None:
        """处理设定主题事件"""
        try:
            self.show_progress("设定主题", f"正在设定主题: {theme_name}")
            # 使用sudo_manager（如果可用）或原始theme_manager
            manager = getattr(self, 'sudo_manager', self.theme_manager)
            result = manager.set_theme(theme_name)
            self.hide_progress()
            
            if result.success:
                self.show_message("成功", result.message, "success")
                self.update_current_theme(theme_name)
                if self.on_theme_changed:
                    self.on_theme_changed(theme_name)
            else:
                self.show_message("设定失败", result.message, "error")
                
        except Exception as e:
            self.hide_progress()
            self.show_message("错误", f"设定主题时发生错误: {e}", "error")
    
    def on_random_theme(self) -> None:
        """处理随机主题事件"""
        try:
            self.show_progress("随机主题", "正在随机选择主题...")
            # 使用sudo_manager（如果可用）或原始theme_manager
            manager = getattr(self, 'sudo_manager', self.theme_manager)
            result = manager.random_theme()
            self.hide_progress()
            
            if result.success:
                self.show_message("成功", result.message, "success")
                self.update_current_theme(result.theme.name if result.theme else None)
                if self.on_theme_changed and result.theme:
                    self.on_theme_changed(result.theme.name)
            else:
                self.show_message("随机选择失败", result.message, "error")
                
        except Exception as e:
            self.hide_progress()
            self.show_message("错误", f"随机选择主题时发生错误: {e}", "error")
    
    def on_add_to_playlist(self, theme_name: str) -> None:
        """处理添加到播放列表事件"""
        try:
            theme_path = self.theme_manager.grub_themes_dir / theme_name
            result = self.theme_manager.add_theme(theme_path)
            
            if result.success:
                self.show_message("成功", result.message, "success")
                self.update_playlist(self.theme_manager.playlist)
                if self.on_playlist_updated:
                    self.on_playlist_updated()
            else:
                self.show_message("添加失败", result.message, "error")
                
        except Exception as e:
            self.show_message("错误", f"添加到播放列表时发生错误: {e}", "error")
    
    def on_remove_from_playlist(self, theme_name: str) -> None:
        """处理从播放列表移除事件"""
        if self.show_confirmation("确认移除", f"确定要从播放列表中移除主题 '{theme_name}' 吗？"):
            try:
                result = self.theme_manager.remove_theme(theme_name)
                
                if result.success:
                    self.show_message("成功", result.message, "success")
                    self.update_playlist(self.theme_manager.playlist)
                    if self.on_playlist_updated:
                        self.on_playlist_updated()
                else:
                    self.show_message("移除失败", result.message, "error")
                    
            except Exception as e:
                self.show_message("错误", f"从播放列表移除时发生错误: {e}", "error")
    
    def on_refresh(self) -> None:
        """处理刷新事件"""
        try:
            themes = self.theme_manager.get_all_themes()
            self.update_theme_list(themes)
            self.update_playlist(self.theme_manager.playlist)
            self.update_current_theme(self.theme_manager.current_theme)
            self.show_message("刷新完成", f"已刷新，共找到 {len(themes)} 个主题", "info")
        except Exception as e:
            self.show_message("错误", f"刷新时发生错误: {e}", "error")
    
    def _install_theme_from_file(self, file_path: Path) -> None:
        """从文件安装主题的内部实现"""
        try:
            theme_name = self.prompt_input(
                "主题名称", 
                f"请输入主题名称 (默认: {file_path.stem}):",
                file_path.stem
            )
            
            if not theme_name:
                return
            
            self.show_progress("安装主题", f"正在安装主题: {theme_name}")
            # 使用sudo_manager（如果可用）或原始theme_manager
            manager = getattr(self, 'sudo_manager', self.theme_manager)
            result = manager.install_theme_from_file(file_path, theme_name)
            self.hide_progress()
            
            if result.success:
                self.show_message("安装成功", result.message, "success")
                
                # 询问是否添加到播放列表
                if self.show_confirmation("添加到播放列表", f"主题安装成功！是否将 '{theme_name}' 添加到播放列表？"):
                    add_result = self.theme_manager.add_theme(result.theme.path)
                    if add_result.success:
                        self.update_playlist(self.theme_manager.playlist)
                
                self.on_refresh()
            else:
                self.show_message("安装失败", result.message, "error")
                
        except Exception as e:
            self.hide_progress()
            self.show_message("错误", f"安装主题时发生错误: {e}", "error")
    
    def _install_theme_from_url(self, url: str) -> None:
        """从URL安装主题的内部实现"""
        try:
            # 从URL推测主题名称
            from urllib.parse import urlparse
            parsed = urlparse(url)
            default_name = Path(parsed.path).stem or "downloaded_theme"
            
            theme_name = self.prompt_input(
                "主题名称",
                f"请输入主题名称 (默认: {default_name}):",
                default_name
            )
            
            if not theme_name:
                return
            
            self.show_progress("下载主题", f"正在从 {url} 下载主题...")
            # 使用sudo_manager（如果可用）或原始theme_manager
            manager = getattr(self, 'sudo_manager', self.theme_manager)
            result = manager.install_theme_from_url(url, theme_name)
            self.hide_progress()
            
            if result.success:
                self.show_message("下载成功", result.message, "success")
                
                # 询问是否添加到播放列表
                if self.show_confirmation("添加到播放列表", f"主题下载成功！是否将 '{theme_name}' 添加到播放列表？"):
                    add_result = self.theme_manager.add_theme(result.theme.path)
                    if add_result.success:
                        self.update_playlist(self.theme_manager.playlist)
                
                self.on_refresh()
            else:
                self.show_message("下载失败", result.message, "error")
                
        except Exception as e:
            self.hide_progress()
            self.show_message("错误", f"下载主题时发生错误: {e}", "error")