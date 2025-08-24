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

# 初始化日志
setup_app_logging()
logger = get_logger(__name__)


class ThemeCLI:
    """主题管理命令行界面"""
    
    def __init__(self):
        self.manager = ThemeManager()
    
    def create_parser(self) -> argparse.ArgumentParser:
        """创建命令行参数解析器"""
        parser = argparse.ArgumentParser(
            prog='grub-theme',
            description='GRUB主题管理器',
            epilog='使用 grub-theme <command> --help 查看特定命令的帮助'
        )
        
        parser.add_argument(
            '--version', 
            action='version', 
            version='grub-theme 1.0.0'
        )
        
        # 创建子命令解析器
        subparsers = parser.add_subparsers(
            dest='command',
            help='可用命令',
            metavar='<command>'
        )
        
        # 添加主题命令
        add_parser = subparsers.add_parser(
            'add',
            help='添加主题到播放列表'
        )
        add_parser.add_argument(
            'theme_path',
            type=str,
            help='主题路径或主题名称'
        ).completer = self._complete_available_theme_names
        
        # 设定主题命令
        set_parser = subparsers.add_parser(
            'set',
            help='设定指定主题'
        )
        set_parser.add_argument(
            'theme_name',
            type=str,
            help='主题名称'
        ).completer = self._complete_theme_names
        
        # 随机主题命令
        subparsers.add_parser(
            'random',
            help='随机选择主题'
        )
        
        # 移除主题命令
        remove_parser = subparsers.add_parser(
            'remove',
            help='从播放列表移除主题'
        )
        remove_parser.add_argument(
            'theme_name',
            type=str,
            help='要移除的主题名称'
        ).completer = self._complete_playlist_theme_names
        
        # 列出主题命令
        list_parser = subparsers.add_parser(
            'list',
            help='列出主题'
        )
        list_parser.add_argument(
            '--all', '-a',
            action='store_true',
            help='显示所有主题（默认只显示播放列表）'
        )
        list_parser.add_argument(
            '--detailed', '-d',
            action='store_true',
            help='显示详细信息'
        )
        
        # 当前主题命令
        subparsers.add_parser(
            'current',
            help='显示当前主题'
        )
        
        # 安装主题命令
        install_parser = subparsers.add_parser(
            'install',
            help='安装主题文件'
        )
        install_parser.add_argument(
            'source',
            type=str,
            help='主题文件路径或URL'
        )
        install_parser.add_argument(
            '--name', '-n',
            type=str,
            help='指定主题名称'
        )
        install_parser.add_argument(
            '--no-add',
            action='store_true',
            help='安装后不添加到播放列表（默认会自动添加）'
        )
        install_parser.add_argument(
            '--set-current',
            action='store_true',
            help='安装后设为当前主题'
        )
        
        # GUI命令
        subparsers.add_parser(
            'gui',
            help='启动图形界面'
        )
        
        # 查看配置文件命令
        subparsers.add_parser(
            'config',
            help='查看GRUB配置文件内容'
        )
        
        # 调试命令
        subparsers.add_parser(
            'debug',
            help='显示调试信息（配置文件路径、用户信息等）'
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
                print("错误: 此操作需要root权限，请使用 sudo 运行", file=sys.stderr)
                return 1
            
            # 执行对应命令
            command_method = getattr(self, f'cmd_{parsed_args.command}', None)
            if command_method:
                return command_method(parsed_args)
            else:
                print(f"未知命令: {parsed_args.command}", file=sys.stderr)
                return 1
                
        except KeyboardInterrupt:
            print("\n操作被用户取消", file=sys.stderr)
            return 1
        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            print(f"错误: {e}", file=sys.stderr)
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
                print("没有找到任何主题")
                return 0
            
            print(f"所有主题 ({len(themes)} 个):")
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
                print("播放列表为空")
                print("使用 'grub-theme add <主题>' 添加主题到播放列表")
                return 0
            
            print(f"播放列表 ({len(playlist)} 个主题):")
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
            print(f"当前主题: {current}")
            
            # 显示主题详细信息
            theme = self.manager.get_theme_info(current)
            if theme:
                print(f"路径: {theme.path}")
                if theme.description:
                    print(f"描述: {theme.description}")
                
                in_playlist = "是" if current in self.manager.playlist else "否"
                print(f"在播放列表中: {in_playlist}")
        else:
            print("当前未设定主题")
        
        return 0
    
    def cmd_install(self, args) -> int:
        """安装主题"""
        source = args.source
        theme_name = args.name
        
        print(f"正在安装主题: {source}")
        
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
                    print(f"✓ 已添加到播放列表: {result.theme.name}")
                else:
                    print(f"! 添加到播放列表失败: {add_result.message}")
            
            # 如果指定了设为当前主题
            if args.set_current and result.theme:
                set_result = self.manager.set_theme(result.theme.name)
                if set_result.success:
                    print(f"✓ 已设为当前主题: {result.theme.name}")
                else:
                    print(f"! 设为当前主题失败: {set_result.message}")
            
            return 0
        else:
            print(f"✗ {result.message}", file=sys.stderr)
            return 1
    
    def cmd_gui(self, args) -> int:
        """启动图形界面"""
        try:
            from gui.tkinter_gui import TkinterThemeGUI
            
            print("启动图形界面...")
            gui = TkinterThemeGUI(self.manager)
            gui.run()
            return 0
            
        except ImportError as e:
            print(f"启动GUI失败，缺少依赖: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"GUI运行时出错: {e}", file=sys.stderr)
            return 1
    
    def cmd_config(self, args) -> int:
        """查看GRUB配置文件内容"""
        print("GRUB配置文件内容 (/etc/default/grub):")
        print("=" * 60)
        
        config_content = self.manager.get_grub_config_content()
        print(config_content)
        
        return 0
    
    def cmd_debug(self, args) -> int:
        """显示调试信息"""
        import os
        from pathlib import Path
        
        print("=== 调试信息 ===")
        print(f"当前用户: {os.getenv('USER', 'unknown')}")
        print(f"当前用户ID: {os.getuid()}")
        print(f"有效用户ID: {os.geteuid()}")
        print(f"HOME目录: {os.getenv('HOME', 'unknown')}")
        print(f"当前工作目录: {os.getcwd()}")
        print()
        
        print("=== 配置文件路径 ===")
        print(f"配置文件路径: {self.manager.config_file}")
        print(f"配置文件存在: {self.manager.config_file.exists()}")
        if self.manager.config_file.exists():
            print(f"配置文件大小: {self.manager.config_file.stat().st_size} bytes")
        print()
        
        print("=== GRUB主题目录 ===")
        print(f"GRUB主题目录: {self.manager.grub_themes_dir}")
        print(f"目录存在: {self.manager.grub_themes_dir.exists()}")
        if self.manager.grub_themes_dir.exists():
            theme_dirs = [d.name for d in self.manager.grub_themes_dir.iterdir() if d.is_dir()]
            print(f"目录中的主题: {theme_dirs}")
        print()
        
        print("=== 播放列表状态 ===")
        print(f"播放列表长度: {len(self.manager.playlist)}")
        print(f"播放列表内容: {self.manager.playlist}")
        print(f"当前主题: {self.manager.current_theme}")
        print()
        
        print("=== 配置文件内容 ===")
        if self.manager.config_file.exists():
            try:
                content = self.manager.config_file.read_text()
                print(content)
            except Exception as e:
                print(f"读取配置文件失败: {e}")
        else:
            print("配置文件不存在")
        
        return 0
    
    def _check_permissions(self) -> bool:
        """检查是否有必要权限"""
        import os
        return os.geteuid() == 0
    
    def _format_theme_list(self, themes, show_detailed=False):
        """格式化主题列表显示"""
        if not themes:
            return "没有找到主题"
        
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