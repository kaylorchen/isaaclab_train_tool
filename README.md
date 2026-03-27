# Isaac Lab Train Tool

A PyQt5-based GUI tool for managing Isaac Lab training and play sessions.

## Features

- Workspace scanning and task discovery
- Conda/venv environment management
- Train/Play mode with parameter configuration
- tmux session management for training processes
- Live stream and camera options
- Resume training with checkpoint selection
- Terminal auto-detection for session attachment
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

1. **Select Workspace**: Click "Browse..." or use "File > Select Workspace..." to choose your Isaac Lab project directory
2. **Scan**: Click "Scan" to discover available scripts and tasks
3. **Configure Environment**: Go to "Edit > Settings..." to configure your Python/Conda environment
4. **Select Task**: Choose the script directory, mode (Train/Play), and task
5. **Set Parameters**: Configure training parameters (num_envs, max_iterations, etc.)
6. **Run**: Click "Run" to start the training in a tmux session

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

## Configuration

Configuration is stored in `~/.config/isaaclab_train_tool/config.json`:

- **Python Environment**: Conda or venv environment settings
- **Default Parameters**: Saved training/play parameters
- **Recent Workspaces**: Quick access to recently used projects
- **Language**: UI language preference

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
└── README.md            # This file
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

## License

MIT License