# GRUB Theme Manager

[English](./README.md) | [中文](#中文)

## 中文

一个用于管理GRUB启动主题的Python工具，提供CLI和GUI界面。

**我们推荐使用CLI**

### 功能特性

- 🎨 **主题播放列表管理**: 维护主题轮换播放列表
- 🎲 **随机主题切换**: 自动或手动随机选择主题
- 📁 **多种安装方式**: 支持文件、目录、URL安装
- 🖥️ **双接口支持**: GUI和CLI灵活使用
- ⚙️ **系统集成**: systemd服务支持启动时主题切换
- 🔒 **权限处理**: 正确的root权限检查

### 快速开始

#### 项目设置

```sh
# 同步依赖
uv sync
```

#### 开发运行

```sh
# 显示帮助
uv run main.py --help

# 启动GUI界面（不推荐）
uv run main.py gui

# 列出所有主题
uv run main.py list --all
```

#### 系统安装

```sh
# 系统级安装（需要root权限）
sudo scripts/install.sh

# 安装后可使用系统命令
grub-theme --help
grub-theme gui
```

**注意**: 系统安装后，会自动配置一个systemd服务，在每次系统启动时从播放列表中随机切换主题。您可以根据需要启用/禁用此服务：

```sh
# 启用启动时自动随机主题切换
sudo systemctl enable grub-theme-random.service

# 禁用启动时自动随机主题切换
sudo systemctl disable grub-theme-random.service

# 检查服务状态
sudo systemctl status grub-theme-random.service
```

### 主要命令

```sh
# 核心命令
grub-theme add <theme_path>         # 添加主题到播放列表
sudo grub-theme set <theme_name>         # 设置特定主题（需要root）
sudo grub-theme random                   # 随机主题切换（需要root）
grub-theme remove <theme_name>      # 从播放列表移除
grub-theme list                     # 显示播放列表
grub-theme list --all               # 显示所有主题
grub-theme current                  # 显示当前主题
sudo grub-theme install <file_or_url>    # 安装主题文件并自动添加到播放列表
grub-theme gui                      # 启动GUI
```

#### 一些示例

```sh
sudo grub-theme install /home/mcallzbl/Downloads/Hysilens_cn.tar.gz
sudo grub-theme install /home/mcallzbl/Downloads/StarRailGrubThemes-master/assets/themes/Aglaea_cn
```

### GUI界面

项目提供了基于tkinter的图形用户界面，支持：
- 拖拽安装主题
- 文件选择器
- URL下载
- 主题预览
- 一键切换

**注意**: GUI目前可能存在一些稳定性问题，建议优先使用CLI命令进行关键操作。

### 项目结构

```
grub-theme/
├── core/                      # 业务逻辑层
│   ├── models.py             # 数据模型
│   └── theme_manager.py      # 核心主题管理
├── cli/                      # 命令行接口
│   └── main.py              # CLI实现
├── gui/                      # 图形界面层
│   ├── base.py              # 抽象GUI接口
│   └── tkinter_gui.py       # tkinter实现
├── scripts/                  # 安装和服务文件
├── config.py                # 配置管理
├── logging_setup.py         # 日志系统
└── main.py                  # 应用入口点
```

### 权限要求

- **读取操作**: 普通用户权限
- **主题安装**: Root权限（写入 `/usr/share/grub/themes/`）
- **主题设置**: Root权限（修改 `/etc/default/grub`，运行 `update-grub`）
- **随机切换**: Root权限（同主题设置）

### 开发依赖

- Python >= 3.13
- uv包管理器
- tkinter（Python内置，GUI无需额外依赖）