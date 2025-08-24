#!/bin/bash
# GRUB主题管理器安装脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== GRUB主题管理器安装脚本 ==="

# 检查是否为root用户
if [[ $EUID -ne 0 ]]; then
   echo "此脚本需要root权限运行，请使用 sudo 执行"
   exit 1
fi

# 检查Python版本
echo "检查Python版本..."
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 13) else 1)" 2>/dev/null; then
    echo "错误: 需要Python 3.13或更高版本"
    exit 1
fi

# 检查uv是否安装
echo "检查uv包管理器..."
if ! command -v uv &> /dev/null; then
    echo "错误: 需要安装uv包管理器"
    echo "请访问 https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# 构建和安装Python包
echo "构建Python包..."
cd "$PROJECT_DIR"
uv build

echo "创建独立的虚拟环境..."
INSTALL_DIR="/opt/grub-theme"
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# 创建虚拟环境并安装包
cd "$INSTALL_DIR"
uv venv
uv pip install "$PROJECT_DIR/dist/"*.whl

# 创建系统命令链接
echo "创建系统命令..."
GRUB_THEME_BIN="/usr/local/bin/grub-theme"
cat > "$GRUB_THEME_BIN" << 'EOF'
#!/bin/bash
exec /opt/grub-theme/.venv/bin/grub-theme "$@"
EOF

chmod +x "$GRUB_THEME_BIN"

# 安装systemd服务（开机随机切换主题）
echo "安装systemd服务..."
cp "$SCRIPT_DIR/grub-theme-random.service" /etc/systemd/system/
systemctl daemon-reload

# 询问是否启用开机随机切换
read -p "是否启用开机随机切换主题服务？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl enable grub-theme-random.service
    echo "✓ 开机随机切换主题服务已启用"
else
    echo "○ 开机随机切换主题服务未启用，可以稍后使用以下命令启用:"
    echo "  sudo systemctl enable grub-theme-random.service"
fi

# 创建GRUB主题目录（如果不存在）
echo "检查GRUB主题目录..."
GRUB_THEMES_DIR="/usr/share/grub/themes"
if [[ ! -d "$GRUB_THEMES_DIR" ]]; then
    mkdir -p "$GRUB_THEMES_DIR"
    echo "✓ 已创建GRUB主题目录: $GRUB_THEMES_DIR"
fi

echo
echo "=== 安装完成 ==="
echo
echo "现在你可以使用以下命令："
echo "  grub-theme --help          查看帮助"
echo "  grub-theme list --all      列出所有主题"
echo "  grub-theme gui             启动图形界面"
echo "  grub-theme random          随机切换主题"
echo
echo "注意："
echo "- 设定主题和随机切换需要root权限"
echo "- 首次使用请先安装一些主题到 $GRUB_THEMES_DIR"
echo "- 使用GUI界面可以方便地管理主题文件"
echo