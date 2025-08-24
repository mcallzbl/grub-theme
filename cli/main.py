"""
命令行界面主程序
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

from core.theme_manager import ThemeManager
from core.models import ThemeStatus
from config import settings, setup_app_logging
from logging_setup import get_logger
from i18n import _, init_i18n

# 初始化日志和国际化
setup_app_logging()
init_i18n()
logger = get_logger(__name__)


class ThemeCLI:
    """主题管理命令行界面"""
    
    def __init__(self):
        self.manager = ThemeManager()
    
    def create_parser(self) -> argparse.ArgumentParser:
        """创建命令行参数解析器"""
        parser = argparse.ArgumentParser(
            prog='grub-theme',
            description=_('GRUB Theme Manager'),
            epilog=_('Use grub-theme <command> --help to see help for specific commands')
        )
        
        parser.add_argument(
            '--version', 
            action='version', 
            version='grub-theme 1.0.0'
        )
        
        # 创建子命令解析器
        subparsers = parser.add_subparsers(
            dest='command',
            help=_('Available commands'),
            metavar='<command>'
        )
        
        # 添加主题命令
        add_parser = subparsers.add_parser(
            'add',
            help=_('Add theme to playlist')
        )
        add_parser.add_argument(
            'theme_path',
            type=str,
            help=_('Theme path or theme name')
        ).completer = self._complete_available_theme_names
        
        # 设定主题命令
        set_parser = subparsers.add_parser(
            'set',
            help=_('Set specified theme')
        )
        set_parser.add_argument(
            'theme_name',
            type=str,
            help=_('Theme name')
        ).completer = self._complete_theme_names
        
        # 随机主题命令
        subparsers.add_parser(
            'random',
            help=_('Randomly select theme')
        )
        
        # 移除主题命令
        remove_parser = subparsers.add_parser(
            'remove',
            help=_('Remove theme from playlist')
        )
        remove_parser.add_argument(
            'theme_name',
            type=str,
            help=_('Theme name to remove')
        ).completer = self._complete_playlist_theme_names
        
        # 列出主题命令
        list_parser = subparsers.add_parser(
            'list',
            help=_('List themes')
        )
        list_parser.add_argument(
            '--all', '-a',
            action='store_true',
            help=_('Show all themes (default: playlist only)')
        )
        list_parser.add_argument(
            '--detailed', '-d',
            action='store_true',
            help=_('Show detailed information')
        )
        
        # 当前主题命令
        subparsers.add_parser(
            'current',
            help=_('Show current theme')
        )
        
        # 安装主题命令
        install_parser = subparsers.add_parser(
            'install',
            help=_('Install theme file')
        )
        install_parser.add_argument(
            'source',
            type=str,
            help=_('Theme file path or URL')
        )
        install_parser.add_argument(
            '--name', '-n',
            type=str,
            help=_('Specify theme name')
        )
        install_parser.add_argument(
            '--no-add',
            action='store_true',
            help=_('Do not add to playlist after installation (auto-add by default)')
        )
        install_parser.add_argument(
            '--set-current',
            action='store_true',
            help=_('Set as current theme after installation')
        )
        
        # GUI命令
        subparsers.add_parser(
            'gui',
            help=_('Launch graphical interface')
        )
        
        # 查看配置文件命令
        subparsers.add_parser(
            'config',
            help=_('View GRUB config file contents')
        )
        
        # 调试命令
        subparsers.add_parser(
            'debug',
            help=_('Show debug information (config paths, user info, etc.)')
        )
        
        return parser
    
    def run(self, args: Optional[list] = None) -> int:
        """运行CLI"""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        if not parsed_args.command:
            parser.print_help()
            return 1
        
        try:
            # 检查权限（某些操作需要root权限）
            if parsed_args.command in ['set', 'random', 'install'] and not self._check_permissions():
                print(_("Error: This operation requires root privileges, please run with sudo"), file=sys.stderr)
                return 1
            
            # 执行对应命令
            command_method = getattr(self, f'cmd_{parsed_args.command}', None)
            if command_method:
                return command_method(parsed_args)
            else:
                print(_("Unknown command: {command}").format(command=parsed_args.command), file=sys.stderr)
                return 1
                
        except KeyboardInterrupt:
            print(_("\nOperation cancelled by user"), file=sys.stderr)
            return 1
        except Exception as e:
            logger.error(_("Command execution failed: {error}").format(error=e))
            print(_("Error: {error}").format(error=e), file=sys.stderr)
            return 1
    
    def cmd_add(self, args) -> int:
        """添加主题到播放列表"""
        theme_path_str = args.theme_path
        
        # 判断是路径还是主题名称
        if '/' in theme_path_str or Path(theme_path_str).exists():
            theme_path = Path(theme_path_str)
        else:
            # 假设是主题名称，构造路径
            theme_path = self.manager.grub_themes_dir / theme_path_str
        
        result = self.manager.add_theme(theme_path)
        
        if result.success:
            print(f"✓ {result.message}")
            return 0
        else:
            print(f"✗ {result.message}", file=sys.stderr)
            return 1
    
    def cmd_set(self, args) -> int:
        """设定指定主题"""
        result = self.manager.set_theme(args.theme_name)
        
        if result.success:
            print(f"✓ {result.message}")
            return 0
        else:
            print(f"✗ {result.message}", file=sys.stderr)
            return 1
    
    def cmd_random(self, args) -> int:
        """随机选择主题"""
        result = self.manager.random_theme()
        
        if result.success:
            print(f"✓ {result.message}")
            if result.theme:
                print(f"  已切换到: {result.theme.name}")
            return 0
        else:
            print(f"✗ {result.message}", file=sys.stderr)
            return 1
    
    def cmd_remove(self, args) -> int:
        """从播放列表移除主题"""
        result = self.manager.remove_theme(args.theme_name)
        
        if result.success:
            print(f"✓ {result.message}")
            return 0
        else:
            print(f"✗ {result.message}", file=sys.stderr)
            return 1
    
    def cmd_list(self, args) -> int:
        """列出主题"""
        if args.all:
            # 显示所有主题
            themes = self.manager.get_all_themes()
            
            if not themes:
                print(_("No themes found"))
                return 0
            
            print(_("All themes ({count}):")
                  .format(count=len(themes)))
            print("-" * 60)
            
            for theme in themes:
                status_icon = "●" if theme.status == ThemeStatus.ACTIVE else "○"
                playlist_icon = "♪" if theme.name in self.manager.playlist else " "
                
                if args.detailed:
                    print(f"{status_icon} {playlist_icon} {theme.name}")
                    print(f"    路径: {theme.path}")
                    if theme.description:
                        print(f"    描述: {theme.description}")
                    print(f"    状态: {theme.status.value}")
                    print()
                else:
                    status_text = f"({theme.status.value})" if theme.status != ThemeStatus.AVAILABLE else ""
                    print(f"{status_icon} {playlist_icon} {theme.name} {status_text}")
        else:
            # 只显示播放列表
            playlist = self.manager.playlist
            
            if not playlist:
                print(_("Playlist is empty"))
                print(_("Use 'grub-theme add <theme>' to add themes to playlist"))
                return 0
            
            print(_("Playlist ({count} themes):")
                  .format(count=len(playlist)))
            print("-" * 40)
            
            current = self.manager.current_theme
            for i, theme_name in enumerate(playlist, 1):
                icon = "▶" if theme_name == current else f"{i:2d}."
                print(f"{icon} {theme_name}")
        
        return 0
    
    def cmd_current(self, args) -> int:
        """显示当前主题"""
        current = self.manager.current_theme
        
        if current:
            print(_("Current theme: {theme}").format(theme=current))
            
            # 显示主题详细信息
            theme = self.manager.get_theme_info(current)
            if theme:
                print(_("Path: {path}").format(path=theme.path))
                if theme.description:
                    print(_("Description: {desc}").format(desc=theme.description))
                
                in_playlist = _("Yes") if current in self.manager.playlist else _("No")
                print(_("In playlist: {status}").format(status=in_playlist))
        else:
            print(_("No theme currently set"))
        
        return 0
    
    def cmd_install(self, args) -> int:
        """安装主题"""
        source = args.source
        theme_name = args.name
        
        print(_("Installing theme: {source}").format(source=source))
        
        # 判断是文件还是URL
        if source.startswith(('http://', 'https://')):
            result = self.manager.install_theme_from_url(source, theme_name)
        else:
            source_path = Path(source)
            result = self.manager.install_theme_from_file(source_path, theme_name)
        
        if result.success:
            print(f"✓ {result.message}")
            
            # 默认添加到播放列表，除非指定了 --no-add
            if not args.no_add and result.theme:
                add_result = self.manager.add_theme(result.theme.path)
                if add_result.success:
                    print(_("✓ Added to playlist: {theme}").format(theme=result.theme.name))
                else:
                    print(_("! Failed to add to playlist: {error}").format(error=add_result.message))
            
            # 如果指定了设为当前主题
            if args.set_current and result.theme:
                set_result = self.manager.set_theme(result.theme.name)
                if set_result.success:
                    print(_("✓ Set as current theme: {theme}").format(theme=result.theme.name))
                else:
                    print(_("! Failed to set as current theme: {error}").format(error=set_result.message))
            
            return 0
        else:
            print(f"✗ {result.message}", file=sys.stderr)
            return 1
    
    def cmd_gui(self, args) -> int:
        """启动图形界面"""
        try:
            from gui.tkinter_gui import TkinterThemeGUI
            
            print(_("Starting graphical interface..."))
            gui = TkinterThemeGUI(self.manager)
            gui.run()
            return 0
            
        except ImportError as e:
            print(_("Failed to start GUI, missing dependency: {error}").format(error=e), file=sys.stderr)
            return 1
        except Exception as e:
            print(_("GUI runtime error: {error}").format(error=e), file=sys.stderr)
            return 1
    
    def cmd_config(self, args) -> int:
        """查看GRUB配置文件内容"""
        print(_("GRUB config file contents (/etc/default/grub):"))
        print("=" * 60)
        
        config_content = self.manager.get_grub_config_content()
        print(config_content)
        
        return 0
    
    def cmd_debug(self, args) -> int:
        """显示调试信息"""
        import os
        from pathlib import Path
        
        print(_("=== Debug Information ==="))
        print(_("Current user: {user}").format(user=os.getenv('USER', 'unknown')))
        print(_("Current user ID: {uid}").format(uid=os.getuid()))
        print(_("Effective user ID: {euid}").format(euid=os.geteuid()))
        print(_("HOME directory: {home}").format(home=os.getenv('HOME', 'unknown')))
        print(_("Current working directory: {cwd}").format(cwd=os.getcwd()))
        print()
        
        print(_("=== Config File Paths ==="))
        print(_("Config file path: {path}").format(path=self.manager.config_file))
        print(_("Config file exists: {exists}").format(exists=self.manager.config_file.exists()))
        if self.manager.config_file.exists():
            print(_("Config file size: {size} bytes").format(size=self.manager.config_file.stat().st_size))
        print()
        
        print(_("=== GRUB Themes Directory ==="))
        print(_("GRUB themes directory: {dir}").format(dir=self.manager.grub_themes_dir))
        print(_("Directory exists: {exists}").format(exists=self.manager.grub_themes_dir.exists()))
        if self.manager.grub_themes_dir.exists():
            theme_dirs = [d.name for d in self.manager.grub_themes_dir.iterdir() if d.is_dir()]
            print(_("Themes in directory: {themes}").format(themes=theme_dirs))
        print()
        
        print(_("=== Playlist Status ==="))
        print(_("Playlist length: {length}").format(length=len(self.manager.playlist)))
        print(_("Playlist contents: {playlist}").format(playlist=self.manager.playlist))
        print(_("Current theme: {theme}").format(theme=self.manager.current_theme))
        print()
        
        print(_("=== Config File Contents ==="))
        if self.manager.config_file.exists():
            try:
                content = self.manager.config_file.read_text()
                print(content)
            except Exception as e:
                print(_("Failed to read config file: {error}").format(error=e))
        else:
            print(_("Config file does not exist"))
        
        return 0
    
    def _check_permissions(self) -> bool:
        """检查是否有必要权限"""
        import os
        return os.geteuid() == 0
    
    def _format_theme_list(self, themes, show_detailed=False):
        """格式化主题列表显示"""
        if not themes:
            return _("No themes found")
        
        lines = []
        current = self.manager.current_theme
        playlist = self.manager.playlist
        
        for theme in themes:
            # 状态图标
            if theme.name == current:
                icon = "▶"
            elif theme.name in playlist:
                icon = "♪"
            else:
                icon = " "
            
            line = f"{icon} {theme.name}"
            
            if show_detailed:
                line += f" ({theme.status.value})"
                if theme.description:
                    line += f" - {theme.description}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def _complete_theme_names(self, prefix, parsed_args, **kwargs):
        """自动补全所有主题名称"""
        try:
            themes = self.manager.get_all_themes()
            return [theme.name for theme in themes if theme.name.startswith(prefix)]
        except:
            return []
    
    def _complete_playlist_theme_names(self, prefix, parsed_args, **kwargs):
        """自动补全播放列表中的主题名称"""
        try:
            playlist = self.manager.playlist
            return [name for name in playlist if name.startswith(prefix)]
        except:
            return []
    
    def _complete_available_theme_names(self, prefix, parsed_args, **kwargs):
        """自动补全可用的主题名称（未在播放列表中的主题）"""
        try:
            all_themes = self.manager.get_all_themes()
            playlist = set(self.manager.playlist)
            available = [theme.name for theme in all_themes if theme.name not in playlist]
            return [name for name in available if name.startswith(prefix)]
        except:
            return []


def main():
    """主函数"""
    cli = ThemeCLI()
    
    # 启用Tab补全（如果argcomplete可用）
    try:
        import argcomplete
        parser = cli.create_parser()
        argcomplete.autocomplete(parser)
    except ImportError:
        # argcomplete未安装，跳过
        pass
    
    sys.exit(cli.run())