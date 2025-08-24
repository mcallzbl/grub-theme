#!/usr/bin/env python3
"""
国际化工具脚本
用于提取消息、更新翻译文件和编译翻译
"""
import argparse
import os
import sys
from pathlib import Path
import subprocess
from typing import List, Optional

# 确保可以导入项目模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_command(cmd: List[str], cwd: Optional[Path] = None) -> bool:
    """运行命令并返回是否成功"""
    try:
        print(f"运行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"命令不存在: {cmd[0]}")
        return False

def extract_messages():
    """从Python文件中提取可翻译的消息"""
    print("=== 提取消息 ===")
    
    # 切换到项目根目录
    os.chdir(project_root)
    
    # 使用pybabel提取消息
    pot_file = project_root / "locales" / "grub-theme.pot"
    
    cmd = [
        "pybabel", "extract",
        "-F", "babel.cfg",           # 配置文件
        "-k", "_",                   # 翻译函数名
        "-o", str(pot_file),         # 输出POT文件
        "."                          # 搜索目录
    ]
    
    if run_command(cmd):
        print(f"✓ 消息已提取到: {pot_file}")
        return True
    else:
        print("✗ 消息提取失败")
        return False

def init_language(lang_code: str):
    """初始化新语言的翻译文件"""
    print(f"=== 初始化语言: {lang_code} ===")
    
    os.chdir(project_root)
    
    pot_file = project_root / "locales" / "grub-theme.pot"
    po_file = project_root / "locales" / lang_code / "LC_MESSAGES" / "grub-theme.po"
    
    # 确保目录存在
    po_file.parent.mkdir(parents=True, exist_ok=True)
    
    if not pot_file.exists():
        print("POT文件不存在，先提取消息")
        if not extract_messages():
            return False
    
    cmd = [
        "pybabel", "init",
        "-i", str(pot_file),         # 输入POT文件
        "-d", "locales",             # 输出目录
        "-l", lang_code              # 语言代码
    ]
    
    if run_command(cmd):
        print(f"✓ 语言 {lang_code} 初始化完成: {po_file}")
        return True
    else:
        print(f"✗ 语言 {lang_code} 初始化失败")
        return False

def update_translations():
    """更新现有的翻译文件"""
    print("=== 更新翻译 ===")
    
    os.chdir(project_root)
    
    pot_file = project_root / "locales" / "grub-theme.pot"
    
    if not pot_file.exists():
        print("POT文件不存在，先提取消息")
        if not extract_messages():
            return False
    
    # 查找所有现有的PO文件
    po_files = list((project_root / "locales").rglob("*.po"))
    
    if not po_files:
        print("没有找到现有的翻译文件")
        return False
    
    success = True
    for po_file in po_files:
        # 提取语言代码
        lang_code = po_file.parent.parent.name
        
        cmd = [
            "pybabel", "update",
            "-i", str(pot_file),     # 输入POT文件
            "-d", "locales",         # 输出目录
            "-l", lang_code          # 语言代码
        ]
        
        print(f"更新语言: {lang_code}")
        if not run_command(cmd):
            success = False
    
    if success:
        print("✓ 所有翻译文件已更新")
    else:
        print("✗ 部分翻译文件更新失败")
    
    return success

def compile_translations():
    """编译翻译文件为.mo格式"""
    print("=== 编译翻译 ===")
    
    os.chdir(project_root)
    
    # 查找所有PO文件
    po_files = list((project_root / "locales").rglob("*.po"))
    
    if not po_files:
        print("没有找到翻译文件")
        return False
    
    success = True
    for po_file in po_files:
        mo_file = po_file.with_suffix('.mo')
        
        cmd = [
            "pybabel", "compile",
            "-i", str(po_file),      # 输入PO文件
            "-o", str(mo_file)       # 输出MO文件
        ]
        
        print(f"编译: {po_file.name} -> {mo_file.name}")
        if not run_command(cmd):
            success = False
    
    if success:
        print("✓ 所有翻译文件已编译")
    else:
        print("✗ 部分翻译文件编译失败")
    
    return success

def stats():
    """显示翻译统计信息"""
    print("=== 翻译统计 ===")
    
    po_files = list((project_root / "locales").rglob("*.po"))
    
    if not po_files:
        print("没有找到翻译文件")
        return
    
    for po_file in po_files:
        lang_code = po_file.parent.parent.name
        
        cmd = ["msgfmt", "--statistics", str(po_file)]
        
        print(f"\n语言: {lang_code}")
        if not run_command(cmd):
            print(f"无法获取 {lang_code} 的统计信息")

def create_chinese_translations():
    """创建中文翻译模板"""
    print("=== 创建中文翻译 ===")
    
    # 先初始化中文
    if not init_language("zh_CN"):
        return False
    
    # 读取PO文件并添加一些基本翻译
    po_file = project_root / "locales" / "zh_CN" / "LC_MESSAGES" / "grub-theme.po"
    
    if not po_file.exists():
        print("中文PO文件不存在")
        return False
    
    # 基本翻译映射
    translations = {
        "GRUB Theme Manager": "GRUB主题管理器",
        "Use grub-theme <command> --help to see help for specific commands": "使用 grub-theme <command> --help 查看特定命令的帮助",
        "Available commands": "可用命令",
        "Add theme to playlist": "添加主题到播放列表",
        "Theme path or theme name": "主题路径或主题名称",
        "Set specified theme": "设定指定主题",
        "Theme name": "主题名称",
        "Randomly select theme": "随机选择主题",
        "Remove theme from playlist": "从播放列表移除主题",
        "Theme name to remove": "要移除的主题名称",
        "List themes": "列出主题",
        "Show all themes (default: playlist only)": "显示所有主题（默认只显示播放列表）",
        "Show detailed information": "显示详细信息",
        "Show current theme": "显示当前主题",
        "Install theme file": "安装主题文件",
        "Theme file path or URL": "主题文件路径或URL",
        "Specify theme name": "指定主题名称",
        "Do not add to playlist after installation (auto-add by default)": "安装后不添加到播放列表（默认会自动添加）",
        "Set as current theme after installation": "安装后设为当前主题",
        "Launch graphical interface": "启动图形界面",
        "View GRUB config file contents": "查看GRUB配置文件内容",
        "Show debug information (config paths, user info, etc.)": "显示调试信息（配置文件路径、用户信息等）",
        "Error: This operation requires root privileges, please run with sudo": "错误: 此操作需要root权限，请使用 sudo 运行",
        "Unknown command: {command}": "未知命令: {command}",
        "Operation cancelled by user": "操作被用户取消",
        "Error: {error}": "错误: {error}",
        "Command execution failed: {error}": "命令执行失败: {error}",
        "No themes found": "没有找到任何主题",
        "All themes ({count}):": "所有主题 ({count} 个):",
        "Playlist is empty": "播放列表为空",
        "Use 'grub-theme add <theme>' to add themes to playlist": "使用 'grub-theme add <主题>' 添加主题到播放列表",
        "Playlist ({count} themes):": "播放列表 ({count} 个主题):",
        "Current theme: {theme}": "当前主题: {theme}",
        "Path: {path}": "路径: {path}",
        "Description: {desc}": "描述: {desc}",
        "Yes": "是",
        "No": "否",
        "In playlist: {status}": "在播放列表中: {status}",
        "No theme currently set": "当前未设定主题",
    }
    
    try:
        # 读取现有内容
        content = po_file.read_text(encoding='utf-8')
        
        # 简单替换翻译
        for english, chinese in translations.items():
            # 查找消息条目并替换空的翻译
            content = content.replace(
                f'msgid "{english}"\nmsgstr ""',
                f'msgid "{english}"\nmsgstr "{chinese}"'
            )
        
        # 写回文件
        po_file.write_text(content, encoding='utf-8')
        
        print(f"✓ 中文翻译已更新: {po_file}")
        return True
        
    except Exception as e:
        print(f"✗ 更新中文翻译失败: {e}")
        return False

def create_english_translations():
    """创建英语翻译"""
    print("=== 创建英语翻译 ===")
    
    # 先初始化英语
    if not init_language("en_US"):
        return False
    
    # 直接处理英语PO文件
    po_file = project_root / "locales" / "en_US" / "LC_MESSAGES" / "grub-theme.po"
    
    if not po_file.exists():
        print("英语PO文件不存在")
        return False
    
    try:
        # 读取文件内容
        lines = po_file.read_text(encoding='utf-8').splitlines()
        updated_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 如果是msgid行
            if line.startswith('msgid '):
                msgid_lines = [line]
                i += 1
                
                # 收集多行msgid
                while i < len(lines) and (lines[i].startswith('"') or lines[i].strip() == ''):
                    msgid_lines.append(lines[i])
                    i += 1
                
                # 检查是否有对应的空msgstr
                if i < len(lines) and lines[i].startswith('msgstr "'):
                    msgstr_line = lines[i]
                    
                    # 如果msgstr为空，用msgid内容填充
                    if msgstr_line.strip() == 'msgstr ""':
                        # 提取msgid内容
                        if len(msgid_lines) == 1:
                            # 单行msgid
                            msgid_content = msgid_lines[0].replace('msgid ', 'msgstr ', 1)
                            updated_lines.extend(msgid_lines)
                            updated_lines.append(msgid_content)
                        else:
                            # 多行msgid
                            updated_lines.extend(msgid_lines)
                            # 复制msgid结构为msgstr
                            for j, msgid_line in enumerate(msgid_lines):
                                if j == 0:
                                    updated_lines.append(msgid_line.replace('msgid ', 'msgstr ', 1))
                                else:
                                    updated_lines.append(msgid_line)
                    else:
                        # msgstr不为空，保持原样
                        updated_lines.extend(msgid_lines)
                        updated_lines.append(msgstr_line)
                    i += 1
                else:
                    # 没有msgstr行，保持原样
                    updated_lines.extend(msgid_lines)
            else:
                updated_lines.append(line)
                i += 1
        
        # 写回文件
        po_file.write_text('\n'.join(updated_lines) + '\n', encoding='utf-8')
        
        print(f"✓ 英语翻译已更新: {po_file}")
        return True
        
    except Exception as e:
        print(f"✗ 创建英语翻译失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="国际化管理工具")
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 提取消息命令
    subparsers.add_parser('extract', help='从源代码提取可翻译消息')
    
    # 初始化语言命令
    init_parser = subparsers.add_parser('init', help='初始化新语言的翻译文件')
    init_parser.add_argument('language', help='语言代码 (如: zh_CN, en_US)')
    
    # 更新翻译命令
    subparsers.add_parser('update', help='更新现有翻译文件')
    
    # 编译翻译命令
    subparsers.add_parser('compile', help='编译翻译文件')
    
    # 统计命令
    subparsers.add_parser('stats', help='显示翻译统计信息')
    
    # 创建中文翻译命令
    subparsers.add_parser('zh', help='创建和更新中文翻译')
    
    # 创建英语翻译命令
    subparsers.add_parser('en', help='创建和更新英语翻译')
    
    # 完整工作流命令
    subparsers.add_parser('build', help='完整构建流程 (extract -> update -> compile)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'extract':
        extract_messages()
    elif args.command == 'init':
        init_language(args.language)
    elif args.command == 'update':
        update_translations()
    elif args.command == 'compile':
        compile_translations()
    elif args.command == 'stats':
        stats()
    elif args.command == 'zh':
        create_chinese_translations()
        compile_translations()
    elif args.command == 'en':
        create_english_translations()
        compile_translations()
    elif args.command == 'build':
        print("开始完整构建流程...")
        if extract_messages():
            if update_translations():
                compile_translations()

if __name__ == "__main__":
    main()