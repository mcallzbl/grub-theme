# GRUB Theme Manager

[English](#english) | [中文](./README.zh.md)

## English

A Python tool for managing GRUB boot themes with both CLI and GUI interfaces.

**We recommend using CLI**

### Features

- 🎨 **Theme Playlist Management**: Maintain theme rotation playlists
- 🎲 **Random Theme Switching**: Automatic or manual random theme selection
- 📁 **Multiple Installation Methods**: Support files, directories, URLs
- 🖥️ **Dual Interface Support**: Flexible GUI and CLI usage
- ⚙️ **System Integration**: systemd service for boot-time theme switching
- 🔒 **Permission Handling**: Proper root permission checks

### Quick Start

#### Project Setup

```sh
# Sync dependencies
uv sync
```

#### Development Usage

```sh
# Show help
uv run main.py --help

# Launch GUI interface(not recommended)
uv run main.py gui   

# List all themes
uv run main.py list --all
```

#### System Installation

```sh
# System-wide installation (requires root)
sudo scripts/install.sh

# After installation, use system command
grub-theme --help
grub-theme gui
```

### Main Commands

```sh
# Core commands
grub-theme add <theme_path>         # Add theme to playlist
sudo grub-theme set <theme_name>         # Set specific theme (needs root)
sudo grub-theme random                   # Random theme switch (needs root)
grub-theme remove <theme_name>      # Remove from playlist
grub-theme list                     # Show playlist
grub-theme list --all               # Show all themes
grub-theme current                  # Show current theme
sudo grub-theme install <file_or_url>    # Install theme file and auto-add to playlist
grub-theme gui                      # Launch GUI
```

#### some example
sudo grub-theme install /home/mcallzbl/Downloads/Hysilens_cn.tar.gz
sudo grub-theme install /home/mcallzbl/Downloads/StarRailGrubThemes-master/assets/themes/Aglaea_cn


### GUI Interface

The project provides a tkinter-based graphical user interface supporting:
- Drag-and-drop theme installation
- File selector
- URL downloads
- Theme preview
- One-click switching

**Note**: The GUI may currently have some stability issues. CLI commands are recommended for critical operations.

### Project Structure

```
grub-theme/
├── core/                      # Business logic layer
│   ├── models.py             # Data models
│   └── theme_manager.py      # Core theme management
├── cli/                      # Command-line interface
│   └── main.py              # CLI implementation
├── gui/                      # Graphical interface layer
│   ├── base.py              # Abstract GUI interface
│   └── tkinter_gui.py       # tkinter implementation
├── scripts/                  # Installation and service files
├── config.py                # Configuration management
├── logging_setup.py         # Logging system
└── main.py                  # Application entry point
```

### Permission Requirements

- **Read Operations**: Normal user permissions
- **Theme Installation**: Root (writes to `/usr/share/grub/themes/`)
- **Theme Setting**: Root (modifies `/etc/default/grub`, runs `update-grub`)
- **Random Switching**: Root (same as theme setting)

### Development Dependencies

- Python >= 3.13
- uv package manager
- tkinter (built into Python, no extra dependencies for GUI)