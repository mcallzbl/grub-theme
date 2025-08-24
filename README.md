# python-uv

[English](./README.en.md) | [中文](#中文)

## 中文

### 项目设置

```sh
uv sync
```

### 运行应用

```sh
uv run main.py
```

### 添加新依赖

```sh
# 添加生产依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name
```

### Python 版本管理

```sh
# 查看当前使用的Python版本
uv python list

# 安装特定版本的Python
uv python install 3.13

# 在项目中使用特定版本
uv python pin 3.13
```

### 虚拟环境管理

```sh
# uv 会自动创建和管理虚拟环境
# 查看虚拟环境信息
uv venv --show

# 激活虚拟环境（可选，uv run 会自动处理）
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows
```

### 常用命令

```sh
# 查看已安装的包
uv pip list

# 更新所有依赖到最新版本
uv lock --upgrade

# 导出requirements.txt格式的依赖列表
uv export --format requirements-txt --output-file requirements.txt

# 运行Python模块
uv run python -m python-uv

# 运行脚本
uv run python script.py
```

### 项目结构

```
python-uv/
├── src/
│   └── python-uv/
│       └── __init__.py
├── hello.py
├── pyproject.toml
├── uv.lock
└── README.md
```

### 开发建议

1. **依赖管理**: 使用 `uv add` 添加依赖，避免手动编辑 `pyproject.toml`
2. **版本锁定**: `uv.lock` 文件应该提交到版本控制系统
3. **Python版本**: 建议在 `pyproject.toml` 中指定支持的Python版本范围
4. **虚拟环境**: uv 自动管理虚拟环境，通常不需要手动操作