"""
主题管理器核心业务逻辑
"""
import json
import random
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.request import urlopen
from urllib.parse import urlparse
import tempfile
import zipfile
import tarfile

from .models import Theme, ThemeOperation, ThemeStatus
from config import settings
from logging_setup import get_logger
from i18n import _, init_i18n

# 初始化国际化
init_i18n()

logger = get_logger(__name__)


class ThemeManager:
    """GRUB主题管理器"""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.grub_themes_dir = Path("/usr/share/grub/themes")
        self.config_file = config_file or self._get_user_config_file()
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._playlist: List[str] = []
        self._current_theme: Optional[str] = None
        self.load_playlist()
    
    def _get_user_config_file(self) -> Path:
        """获取用户配置文件路径，优先使用原始用户HOME而不是sudo后的HOME"""
        import os
        
        # 如果是通过sudo运行，尝试获取原始用户的HOME
        original_user = os.getenv('SUDO_USER')
        if original_user and os.getenv('SUDO_UID'):
            # 构造原始用户的HOME目录路径
            original_home = Path(f"/home/{original_user}")
            if original_home.exists():
                config_path = original_home / ".config" / "grub-theme" / "playlist.json"
                logger.debug(f"检测到sudo环境，使用原始用户配置: {config_path}")
                return config_path
        
        # 默认使用当前用户的HOME
        config_path = Path.home() / ".config" / "grub-theme" / "playlist.json"
        logger.debug(f"使用当前用户配置: {config_path}")
        return config_path
    
    @property
    def playlist(self) -> List[str]:
        """获取播放列表"""
        return self._playlist.copy()
    
    @property
    def current_theme(self) -> Optional[str]:
        """获取当前主题"""
        return self._current_theme
    
    def load_playlist(self) -> None:
        """从配置文件加载播放列表"""
        try:
            if self.config_file.exists():
                logger.debug(f"加载配置文件: {self.config_file}")
                
                # 读取文件内容
                content = self.config_file.read_text(encoding='utf-8')
                logger.debug(f"配置文件内容: {content[:200]}...")
                
                # 解析JSON
                data = json.loads(content)
                logger.debug(f"解析的数据: {data}")
                
                # 提取播放列表
                playlist_data = data.get("playlist", [])
                logger.debug(f"原始播放列表数据: {playlist_data}")
                
                # 确保播放列表是列表类型
                if isinstance(playlist_data, list):
                    self._playlist = playlist_data.copy()
                    logger.info(f"成功加载播放列表: {len(self._playlist)} 个主题: {self._playlist}")
                else:
                    logger.warning(f"播放列表数据类型错误，期望list，得到{type(playlist_data)}: {playlist_data}")
                    self._playlist = []
                
                # 从GRUB配置文件解析真正的当前主题，而不是从JSON读取
                self._current_theme = self._get_current_theme_from_grub()
                logger.info(f"加载完成 - 播放列表: {len(self._playlist)} 个主题, 当前主题: {self._current_theme}")
            else:
                logger.info(f"配置文件不存在，初始化空播放列表: {self.config_file}")
                self._playlist = []
                self._current_theme = self._get_current_theme_from_grub()
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 文件: {self.config_file}")
            self._playlist = []
            self._current_theme = self._get_current_theme_from_grub()
        except UnicodeDecodeError as e:
            logger.error(f"文件编码错误: {e}, 文件: {self.config_file}")
            self._playlist = []
            self._current_theme = self._get_current_theme_from_grub()
        except Exception as e:
            logger.error(f"加载播放列表失败: {e}, 文件: {self.config_file}")
            self._playlist = []
            self._current_theme = self._get_current_theme_from_grub()
    
    def save_playlist(self) -> None:
        """保存播放列表到配置文件"""
        try:
            logger.debug(f"准备保存播放列表到: {self.config_file}")
            logger.debug(f"当前播放列表内容: {self._playlist}")
            
            # 获取真正的当前主题
            current_theme_from_grub = self._get_current_theme_from_grub()
            data = {
                "playlist": self._playlist.copy(),  # 创建副本避免引用问题
                "current_theme": current_theme_from_grub,  # 保存从GRUB解析的主题
                "last_updated": str(Path().cwd())
            }
            
            logger.debug(f"准备写入的数据: {data}")
            
            # 确保父目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            json_content = json.dumps(data, indent=2, ensure_ascii=False)
            self.config_file.write_text(json_content, encoding='utf-8')
            
            logger.info(f"播放列表已保存: {len(self._playlist)} 个主题到 {self.config_file}")
            
            # 验证写入是否成功
            try:
                verification_content = self.config_file.read_text(encoding='utf-8')
                verification_data = json.loads(verification_content)
                saved_count = len(verification_data.get('playlist', []))
                logger.debug(f"验证保存结果: 文件中有 {saved_count} 个主题")
                
                if saved_count != len(self._playlist):
                    logger.error(f"保存验证失败: 期望 {len(self._playlist)} 个主题，实际保存了 {saved_count} 个")
            except Exception as verify_e:
                logger.error(f"验证保存结果失败: {verify_e}")
                
        except Exception as e:
            logger.error(f"保存播放列表失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
    
    def get_all_themes(self) -> List[Theme]:
        """获取所有可用主题"""
        themes = []
        
        if not self.grub_themes_dir.exists():
            logger.warning(f"GRUB主题目录不存在: {self.grub_themes_dir}")
            return themes
        
        try:
            # 使用列表推导收集所有目录，避免迭代器问题
            theme_dirs = [d for d in self.grub_themes_dir.iterdir() if d.is_dir()]
            
            for theme_dir in theme_dirs:
                try:
                    theme = Theme(
                        name=theme_dir.name,
                        path=theme_dir,
                        status=ThemeStatus.ACTIVE if theme_dir.name == self._current_theme else ThemeStatus.AVAILABLE
                    )
                    
                    # 检查主题有效性
                    if not theme.is_valid:
                        theme.status = ThemeStatus.ERROR
                        logger.warning(f"主题无效: {theme.name}")
                    
                    # 查找预览图片
                    try:
                        for ext in ['.png', '.jpg', '.jpeg']:
                            preview = theme_dir / f"preview{ext}"
                            if preview.exists():
                                theme.preview_image = preview
                                break
                    except Exception as e:
                        logger.debug(f"查找预览图片失败 {theme_dir.name}: {e}")
                    
                    themes.append(theme)
                    
                except Exception as e:
                    logger.error(f"处理主题目录失败 {theme_dir.name}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"遍历主题目录失败: {e}")
            return []
        
        return sorted(themes, key=lambda t: t.name.lower())
    
    def add_theme(self, theme_path: Path) -> ThemeOperation:
        """添加主题到播放列表"""
        try:
            if not theme_path.exists():
                return ThemeOperation(False, _("Theme path does not exist: {path}").format(path=theme_path))
            
            theme_name = theme_path.name
            
            # 检查是否已在播放列表中
            if theme_name in self._playlist:
                return ThemeOperation(False, _("Theme '{name}' is already in playlist").format(name=theme_name))
            
            # 检查主题是否有效
            if not (theme_path / "theme.txt").exists():
                return ThemeOperation(False, _("Invalid GRUB theme: missing theme.txt file"))
            
            # 添加到播放列表
            self._playlist.append(theme_name)
            self.save_playlist()
            
            theme = Theme(name=theme_name, path=theme_path)
            logger.info(f"主题已添加到播放列表: {theme_name}")
            
            return ThemeOperation(True, _("Theme '{name}' added to playlist").format(name=theme_name), theme)
            
        except Exception as e:
            logger.error(f"添加主题失败: {e}")
            return ThemeOperation(False, _("Failed to add theme: {error}").format(error=e), error=e)
    
    def remove_theme(self, theme_name: str) -> ThemeOperation:
        """从播放列表中移除主题"""
        try:
            if theme_name not in self._playlist:
                return ThemeOperation(False, _("Theme '{name}' is not in playlist").format(name=theme_name))
            
            self._playlist.remove(theme_name)
            
            # 如果移除的是当前主题，清除当前主题记录
            if self._current_theme == theme_name:
                self._current_theme = None
            
            self.save_playlist()
            logger.info(f"主题已从播放列表移除: {theme_name}")
            
            return ThemeOperation(True, _("Theme '{name}' removed from playlist").format(name=theme_name))
            
        except Exception as e:
            logger.error(f"移除主题失败: {e}")
            return ThemeOperation(False, _("Failed to remove theme: {error}").format(error=e), error=e)
    
    def set_theme(self, theme_name: str) -> ThemeOperation:
        """设定指定主题为当前主题"""
        try:
            theme_path = self.grub_themes_dir / theme_name
            
            if not theme_path.exists():
                return ThemeOperation(False, _("Theme does not exist: {name}").format(name=theme_name))
            
            theme = Theme(name=theme_name, path=theme_path)
            if not theme.is_valid:
                return ThemeOperation(False, _("Invalid theme: {name}").format(name=theme_name))
            
            # 更新GRUB配置
            result = self._update_grub_config(theme_name)
            if not result.success:
                return result
            
            self._current_theme = theme_name
            self.save_playlist()
            
            logger.info(f"已设定主题: {theme_name}")
            return ThemeOperation(True, _("Theme set: {name}").format(name=theme_name), theme)
            
        except Exception as e:
            logger.error(f"设定主题失败: {e}")
            return ThemeOperation(False, _("Failed to set theme: {error}").format(error=e), error=e)
    
    def random_theme(self) -> ThemeOperation:
        """随机选择一个主题"""
        try:
            if not self._playlist:
                return ThemeOperation(False, _("Playlist is empty"))
            
            # 从播放列表中随机选择（排除当前主题）
            available_themes = [t for t in self._playlist if t != self._current_theme]
            
            if not available_themes:
                if len(self._playlist) == 1:
                    return ThemeOperation(False, _("Only one theme in playlist"))
                available_themes = self._playlist
            
            selected_theme = random.choice(available_themes)
            return self.set_theme(selected_theme)
            
        except Exception as e:
            logger.error(f"随机选择主题失败: {e}")
            return ThemeOperation(False, _("Failed to select random theme: {error}").format(error=e), error=e)
    
    def install_theme_from_file(self, file_path: Path, theme_name: Optional[str] = None) -> ThemeOperation:
        """从文件安装主题"""
        try:
            if not file_path.exists():
                return ThemeOperation(False, _("File does not exist: {path}").format(path=file_path))
            
            # 确定主题名称
            if not theme_name:
                theme_name = self._extract_theme_name_from_file(file_path)
            
            target_dir = self.grub_themes_dir / theme_name
            
            # 检查目标目录是否存在
            if target_dir.exists():
                return ThemeOperation(False, _("Theme already exists: {name}").format(name=theme_name))
            
            # 根据文件类型处理
            file_suffix = file_path.suffix.lower()
            file_name = file_path.name.lower()
            
            if file_suffix in ['.zip']:
                return self._extract_zip_theme(file_path, target_dir, theme_name)
            elif file_suffix in ['.tar', '.tgz'] or file_name.endswith('.tar.gz'):
                return self._extract_tar_theme(file_path, target_dir, theme_name)
            elif file_path.is_dir():
                return self._copy_theme_directory(file_path, target_dir, theme_name)
            else:
                return ThemeOperation(False, _("Unsupported file type: {type}").format(type=file_path.suffix))
                
        except Exception as e:
            logger.error(f"安装主题失败: {e}")
            return ThemeOperation(False, _("Failed to install theme: {error}").format(error=e), error=e)
    
    def install_theme_from_url(self, url: str, theme_name: Optional[str] = None) -> ThemeOperation:
        """从URL下载并安装主题"""
        try:
            # 确定文件名
            parsed_url = urlparse(url)
            filename = Path(parsed_url.path).name
            if not filename:
                filename = "theme.zip"
            
            # 下载到临时文件
            with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp_file:
                logger.info(f"正在下载: {url}")
                
                with urlopen(url) as response:
                    shutil.copyfileobj(response, tmp_file)
                
                tmp_path = Path(tmp_file.name)
            
            try:
                # 安装主题
                result = self.install_theme_from_file(tmp_path, theme_name)
                return result
            finally:
                # 清理临时文件
                tmp_path.unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"从URL安装主题失败: {e}")
            return ThemeOperation(False, _("Failed to install theme from URL: {error}").format(error=e), error=e)
    
    def _extract_zip_theme(self, zip_path: Path, target_dir: Path, theme_name: str) -> ThemeOperation:
        """提取ZIP主题文件"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                self._ensure_root_access()
                
                # 先提取到临时目录
                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    zip_ref.extractall(temp_path)
                    
                    # 查找主题目录
                    theme_source = self._find_theme_directory(temp_path)
                    if not theme_source:
                        return ThemeOperation(False, _("No valid GRUB theme directory found in ZIP file"))
                    
                    # 复制到目标位置
                    shutil.copytree(theme_source, target_dir)
                
                # 验证主题
                theme = Theme(name=theme_name, path=target_dir)
                if not theme.is_valid:
                    shutil.rmtree(target_dir, ignore_errors=True)
                    return ThemeOperation(False, _("Extracted files are not a valid GRUB theme"))
                
                logger.info(f"ZIP主题已提取: {theme_name}")
                return ThemeOperation(True, _("Theme '{name}' installed successfully").format(name=theme_name), theme)
                
        except Exception as e:
            # 清理失败的安装
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            raise e
    
    def _extract_tar_theme(self, tar_path: Path, target_dir: Path, theme_name: str) -> ThemeOperation:
        """提取TAR主题文件"""
        try:
            with tarfile.open(tar_path, 'r:*') as tar_ref:
                self._ensure_root_access()
                
                # 先提取到临时目录
                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    tar_ref.extractall(temp_path)
                    
                    # 查找主题目录
                    theme_source = self._find_theme_directory(temp_path)
                    if not theme_source:
                        return ThemeOperation(False, _("No valid GRUB theme directory found in TAR file"))
                    
                    # 复制到目标位置
                    shutil.copytree(theme_source, target_dir)
                
                # 验证主题
                theme = Theme(name=theme_name, path=target_dir)
                if not theme.is_valid:
                    shutil.rmtree(target_dir, ignore_errors=True)
                    return ThemeOperation(False, _("Extracted files are not a valid GRUB theme"))
                
                logger.info(f"TAR主题已提取: {theme_name}")
                return ThemeOperation(True, _("Theme '{name}' installed successfully").format(name=theme_name), theme)
                
        except Exception as e:
            # 清理失败的安装
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            raise e
    
    def _copy_theme_directory(self, source_dir: Path, target_dir: Path, theme_name: str) -> ThemeOperation:
        """复制主题目录"""
        try:
            # 验证源主题
            source_theme = Theme(name=source_dir.name, path=source_dir)
            if not source_theme.is_valid:
                return ThemeOperation(False, _("Source directory is not a valid GRUB theme"))
            
            # 复制目录
            self._ensure_root_access()
            shutil.copytree(source_dir, target_dir)
            
            theme = Theme(name=theme_name, path=target_dir)
            logger.info(f"主题目录已复制: {theme_name}")
            return ThemeOperation(True, f"主题 '{theme_name}' 安装成功", theme)
            
        except Exception as e:
            # 清理失败的安装
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            raise e
    
    def _find_theme_directory(self, search_path: Path) -> Optional[Path]:
        """在给定路径中查找GRUB主题目录"""
        # 首先检查根目录是否直接包含theme.txt
        if (search_path / "theme.txt").exists():
            return search_path
        
        # 递归搜索子目录中的主题
        for item in search_path.rglob("*"):
            if item.is_dir() and (item / "theme.txt").exists():
                logger.info(f"找到主题目录: {item}")
                return item
        
        # 如果没有找到theme.txt，查找可能的主题目录
        # 有些主题可能文件名大小写不同
        for item in search_path.rglob("*"):
            if item.is_dir():
                # 检查常见的主题文件名变体
                for theme_file in ["theme.txt", "Theme.txt", "THEME.TXT", "theme.conf"]:
                    if (item / theme_file).exists():
                        logger.info(f"找到主题目录 (变体): {item}")
                        return item
        
        return None
    
    def _update_grub_config(self, theme_name: str) -> ThemeOperation:
        """更新GRUB配置以使用指定主题"""
        try:
            self._ensure_root_access()
            
            # 更新GRUB默认配置
            grub_default_path = Path("/etc/default/grub")
            
            if not grub_default_path.exists():
                return ThemeOperation(False, _("GRUB config file does not exist: /etc/default/grub"))
            
            # 读取当前配置
            lines = grub_default_path.read_text().splitlines()
            
            # 更新主题设置
            theme_line = f'GRUB_THEME="/usr/share/grub/themes/{theme_name}/theme.txt"'
            theme_found = False
            
            for i, line in enumerate(lines):
                if line.startswith("GRUB_THEME="):
                    lines[i] = theme_line
                    theme_found = True
                    break
            
            if not theme_found:
                lines.append(theme_line)
            
            # 写回配置文件
            grub_default_path.write_text("\n".join(lines) + "\n")
            
            # 更新GRUB - 根据系统智能选择命令
            update_commands = self._get_grub_update_commands()
            
            last_error = None
            for cmd in update_commands:
                try:
                    logger.info(f"尝试GRUB更新命令: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        logger.info(f"GRUB配置已更新: {theme_name}")
                        return ThemeOperation(True, _("GRUB config updated successfully (using: {cmd})").format(cmd=cmd[0]))
                    else:
                        last_error = f"{cmd[0]}: {result.stderr}"
                        logger.warning(f"命令 {cmd[0]} 失败: {result.stderr}")
                except FileNotFoundError:
                    last_error = f"命令不存在: {cmd[0]}"
                    logger.debug(f"命令不存在: {cmd[0]}")
                    continue
                except subprocess.TimeoutExpired:
                    last_error = f"命令超时: {cmd[0]}"
                    logger.warning(f"命令超时: {cmd[0]}")
                    continue
                except Exception as e:
                    last_error = f"命令执行出错 {cmd[0]}: {e}"
                    logger.warning(f"命令执行出错 {cmd[0]}: {e}")
                    continue
            
            return ThemeOperation(False, _("All GRUB update commands failed. Last error: {error}").format(error=last_error))
            
        except Exception as e:
            logger.error(f"更新GRUB配置失败: {e}")
            return ThemeOperation(False, _("Failed to update GRUB config: {error}").format(error=e), error=e)
    
    def _get_grub_update_commands(self):
        """根据系统类型获取GRUB更新命令"""
        commands = []
        
        # 检查系统是否使用UEFI
        is_uefi = Path("/sys/firmware/efi").exists()
        
        # 检查发行版
        distro_info = self._detect_distro()
        
        if distro_info.get("family") == "debian":
            # Debian/Ubuntu系列
            commands.append(["update-grub"])
        elif distro_info.get("family") == "arch":
            # Arch Linux
            if is_uefi:
                commands.append(["grub-mkconfig", "-o", "/boot/grub/grub.cfg"])
            else:
                commands.append(["grub-mkconfig", "-o", "/boot/grub/grub.cfg"])
        elif distro_info.get("family") == "fedora":
            # Fedora/RHEL系列
            if is_uefi:
                commands.append(["grub2-mkconfig", "-o", "/boot/efi/EFI/fedora/grub.cfg"])
                commands.append(["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"])  # fallback
            else:
                commands.append(["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"])
        elif distro_info.get("family") == "suse":
            # openSUSE
            commands.append(["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"])
        
        # 添加通用命令作为fallback
        fallback_commands = [
            ["update-grub"],
            ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"],
            ["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"],
        ]
        
        # 避免重复命令
        for cmd in fallback_commands:
            if cmd not in commands:
                commands.append(cmd)
        
        return commands
    
    def _detect_distro(self):
        """检测Linux发行版"""
        try:
            # 尝试读取os-release文件
            if Path("/etc/os-release").exists():
                with open("/etc/os-release") as f:
                    content = f.read().lower()
                    
                    if "ubuntu" in content or "debian" in content:
                        return {"family": "debian", "name": "debian-based"}
                    elif "arch" in content:
                        return {"family": "arch", "name": "arch"}
                    elif "fedora" in content or "rhel" in content or "centos" in content:
                        return {"family": "fedora", "name": "fedora-based"}
                    elif "suse" in content:
                        return {"family": "suse", "name": "suse"}
            
            # fallback检测方法
            if Path("/etc/debian_version").exists():
                return {"family": "debian", "name": "debian-based"}
            elif Path("/etc/arch-release").exists():
                return {"family": "arch", "name": "arch"}
            elif Path("/etc/fedora-release").exists():
                return {"family": "fedora", "name": "fedora"}
            elif Path("/etc/SuSE-release").exists():
                return {"family": "suse", "name": "suse"}
                
        except Exception as e:
            logger.warning(f"检测发行版失败: {e}")
        
        return {"family": "unknown", "name": "unknown"}
    
    def _ensure_root_access(self):
        """确保有root权限"""
        import os
        if os.geteuid() != 0:
            raise PermissionError("需要root权限来修改GRUB主题")
    
    def get_theme_info(self, theme_name: str) -> Optional[Theme]:
        """获取指定主题的详细信息"""
        theme_path = self.grub_themes_dir / theme_name
        if not theme_path.exists():
            return None
        
        theme = Theme(
            name=theme_name,
            path=theme_path,
            status=ThemeStatus.ACTIVE if theme_name == self._current_theme else ThemeStatus.AVAILABLE
        )
        
        # 读取主题描述
        theme_txt = theme_path / "theme.txt"
        if theme_txt.exists():
            try:
                content = theme_txt.read_text()
                # 简单解析主题信息（可以扩展）
                for line in content.splitlines():
                    if line.startswith("#"):
                        if "description" in line.lower():
                            theme.description = line.strip("# ").strip()
                            break
            except Exception as e:
                logger.warning(f"读取主题描述失败 {theme_name}: {e}")
        
        return theme
    
    def _get_current_theme_from_grub(self) -> Optional[str]:
        """从GRUB配置文件解析当前主题"""
        try:
            grub_config_path = Path("/etc/default/grub")
            if not grub_config_path.exists():
                logger.warning("GRUB配置文件不存在: /etc/default/grub")
                return None
            
            content = grub_config_path.read_text()
            
            # 解析GRUB_THEME配置行
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("GRUB_THEME=") and not line.startswith("#"):
                    # 提取主题路径
                    theme_path_match = line.split("=", 1)[1].strip('"\'')
                    
                    # 解析主题名称（从路径中提取）
                    # 期望格式: /usr/share/grub/themes/主题名称/theme.txt
                    if "/usr/share/grub/themes/" in theme_path_match:
                        theme_name = theme_path_match.replace("/usr/share/grub/themes/", "")
                        theme_name = theme_name.replace("/theme.txt", "")
                        if theme_name:
                            logger.info(f"从GRUB配置解析当前主题: {theme_name}")
                            return theme_name
            
            logger.info("GRUB配置中未找到主题设置")
            return None
            
        except Exception as e:
            logger.error(f"解析GRUB配置失败: {e}")
            return None
    
    def get_grub_config_content(self) -> str:
        """获取GRUB配置文件内容"""
        try:
            grub_config_path = Path("/etc/default/grub")
            if not grub_config_path.exists():
                return "GRUB配置文件不存在: /etc/default/grub"
            
            return grub_config_path.read_text()
            
        except PermissionError:
            return "权限不足，无法读取GRUB配置文件（需要sudo权限）"
        except Exception as e:
            return f"读取GRUB配置文件失败: {e}"
    
    def _extract_theme_name_from_file(self, file_path: Path) -> str:
        """从文件路径提取主题名称，正确处理复合扩展名"""
        file_name = file_path.name
        
        # 处理常见的复合扩展名
        if file_name.endswith('.tar.gz'):
            # example.tar.gz -> example
            return file_name[:-7]
        elif file_name.endswith('.tar.bz2'):
            # example.tar.bz2 -> example  
            return file_name[:-8]
        elif file_name.endswith('.tar.xz'):
            # example.tar.xz -> example
            return file_name[:-7]
        else:
            # 使用标准的 stem (去掉最后一个扩展名)
            # example.zip -> example, example.tgz -> example
            return file_path.stem