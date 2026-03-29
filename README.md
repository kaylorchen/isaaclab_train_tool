# Isaac Lab Train Tool

[中文文档](README_CN.md)

A PyQt5-based GUI tool for managing Isaac Lab training and play sessions.

## Features

- **Workspace Management**
  - Workspace scanning and task discovery
  - Workspace history dropdown (up to 20 recent workspaces)
  - Auto-scan on startup, browse selection, and workspace change

- **Environment Management**
  - Conda/venv environment configuration
  - Source package installation/uninstallation detection
  - One-click source install with pip install -e

- **Training & Play**
  - Train/Play mode with parameter configuration
  - Resume training with checkpoint selection
  - Live stream and camera options
  - Automatic mode detection from task name

- **Session Management**
  - tmux session management for training processes
  - Terminal auto-detection for session attachment
  - Large history buffer (50000 lines) for log capture

- **Log Management**
  - Real-time log display with ANSI color support
  - Auto-save log every 3 seconds (append mode)
  - Manual log save option

- **Configuration**
  - Configuration persistence
  - Multi-language support (Chinese/English)

## Requirements

- Python 3.8+
- PyQt5
- tmux

## Installation

### 1. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv tmux

# Fedora
sudo dnf install python3 python3-pip tmux

# Arch Linux
sudo pacman -S python python-pip tmux
```

### 2. Clone or Download

```bash
cd ~/work/nvidia
git clone <repository_url> isaaclab_train_tool
cd isaaclab_train_tool
```

### 3. Create Virtual Environment (Optional but Recommended)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install PyQt5
```

## Usage

### Running the Application

```bash
python3 main.py
```

Or if using virtual environment:

```bash
source venv/bin/activate
python3 main.py
```

### Basic Workflow

1. **Select Workspace**: Click "Browse..." or use "File > Select Workspace..." to choose your Isaac Lab project directory. The workspace history dropdown shows recent workspaces.
2. **Auto Scan**: The tool automatically scans on startup (if last workspace exists) and after selecting a directory.
3. **Configure Environment**: Go to "Edit > Settings..." to configure your Python/Conda environment.
4. **Source Install**: If the workspace has a `source/` directory, the tool detects installation status. Click "Install Source" to install with `pip install -e`.
5. **Select Task**: Choose the script directory, mode (Train/Play), and task. Mode is auto-detected from task name.
6. **Set Parameters**: Configure training parameters (num_envs, max_iterations, etc.).
7. **Run**: Click "Run" to start the training in a tmux session.

### Language Switching

Use "Edit > Language" menu to switch between Chinese and English.

### Resume Training

1. Check "Resume" checkbox in Train mode
2. Click "Refresh Runs" to load available runs
3. Select a run and checkpoint to resume from

### Play Mode with Checkpoint

1. Switch to Play mode
2. Click "Refresh Runs" to load available runs
3. Select a run and checkpoint (.pt file) to load

### Log Auto-Save

Logs are automatically saved every 3 seconds to the configured log directory (append mode). This prevents log loss even if the application crashes.

## Configuration

Configuration is stored in `~/.config/isaaclab_train_tool/config.json`:

- **Python Environment**: Conda or venv environment settings
- **Default Parameters**: Saved training/play parameters
- **Recent Workspaces**: Quick access to recently used projects
- **Workspace History**: Up to 20 recent workspace paths
- **Language**: UI language preference
- **Log Save Path**: Directory for auto-saved logs

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open Workspace directory |
| Ctrl+, | Open Settings |
| Ctrl+Q | Exit application |

## Directory Structure

```
isaaclab_train_tool/
├── main.py              # Application entry point
├── main_window.py       # Main window UI
├── config_dialog.py     # Settings dialog
├── config.py            # Configuration management
├── models.py            # Data models
├── workspace_scanner.py # Workspace scanning logic
├── tmux_manager.py      # tmux session management
├── i18n.py              # Internationalization
├── requirements.txt     # Python dependencies
├── README.md            # English documentation
└── README_CN.md         # Chinese documentation
```

## Troubleshooting

### "No Python environment configured"

Go to "Edit > Settings..." and either:
- Scan for Conda/venv environments
- Or manually enter environment path

### "No scripts found in scripts directory"

Make sure the selected directory is a valid Isaac Lab project with a `scripts/` directory containing `train.py` or `play.py`.

### Terminal attachment not working

The tool auto-detects your terminal emulator. If it doesn't work:
- Make sure tmux is installed
- Try installing a supported terminal (gnome-terminal, konsole, xfce4-terminal, etc.)

### Log file limited to ~2000 lines

For new sessions, the tmux history-limit is set to 50000 lines. Old sessions created before v1.0.1 may still have the default 2000 limit. Create a new session to use the increased limit.

## Changelog

### v1.0.1
- Add workspace history dropdown (up to 20 entries)
- Add source package installation/uninstallation feature
- Add auto-scan on startup and browse selection
- Fix tmux history-limit (now 50000 lines)
- Add real-time log append save (every 3 seconds)
- Fix signal connection issues

### v1.0.0
- Initial release
- Basic workspace scanning and task discovery
- Train/Play mode support
- tmux session management
- Multi-language support (Chinese/English)

## License

MIT License