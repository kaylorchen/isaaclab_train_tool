# Isaac Lab 训练工具

一个基于 PyQt5 的 GUI 工具，用于管理 Isaac Lab 的训练和测试会话。

## 功能特性

- **工作空间管理**
  - 工作空间扫描和任务发现
  - 工作空间历史下拉框（最多20条记录）
  - 启动时、浏览选择、切换时自动扫描

- **环境管理**
  - Conda/venv 环境配置
  - 源码包安装/卸载状态检测
  - 一键源码安装（pip install -e）

- **训练与测试**
  - Train/Play 模式参数配置
  - 断点续训功能
  - 直播流和相机选项
  - 根据任务名自动识别模式

- **会话管理**
  - tmux 会话管理训练进程
  - 自动检测终端类型进行会话附加
  - 大历史缓冲区（50000行）用于日志捕获

- **日志管理**
  - 实时日志显示，支持 ANSI 颜色
  - 每3秒自动追加保存日志
  - 手动保存日志选项

- **配置管理**
  - 配置持久化保存
  - 多语言支持（中文/英文）

## 系统要求

- Python 3.8+
- PyQt5
- tmux

## 安装

### 1. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv tmux

# Fedora
sudo dnf install python3 python3-pip tmux

# Arch Linux
sudo pacman -S python python-pip tmux
```

### 2. 克隆或下载

```bash
cd ~/work/nvidia
git clone <repository_url> isaaclab_train_tool
cd isaaclab_train_tool
```

### 3. 创建虚拟环境（推荐）

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install PyQt5
```

## 使用方法

### 启动应用

```bash
python3 main.py
```

使用虚拟环境时：

```bash
source venv/bin/activate
python3 main.py
```

### 基本工作流程

1. **选择工作空间**：点击"浏览..."或使用"文件 > 选择工作空间..."来选择 Isaac Lab 项目目录。工作空间历史下拉框显示最近使用的工作空间。
2. **自动扫描**：工具会在启动时（如果存在上次的工作空间）和选择目录后自动扫描。
3. **配置环境**：进入"编辑 > 设置..."配置 Python/Conda 环境。
4. **源码安装**：如果工作空间包含 `source/` 目录，工具会检测安装状态。点击"安装源码"使用 `pip install -e` 安装。
5. **选择任务**：选择脚本目录、模式（Train/Play）和任务。模式会从任务名自动识别。
6. **设置参数**：配置训练参数（num_envs、max_iterations 等）。
7. **运行**：点击"运行"在 tmux 会话中启动训练。

### 语言切换

使用"编辑 > 语言"菜单切换中文和英文。

### 断点续训

1. 在 Train 模式下勾选"续训"复选框
2. 点击"刷新运行记录"加载可用的运行记录
3. 选择运行记录和断点进行续训

### Play 模式加载断点

1. 切换到 Play 模式
2. 点击"刷新运行记录"加载可用的运行记录
3. 选择运行记录和断点文件（.pt）进行加载

### 日志自动保存

日志每3秒自动追加保存到配置的日志目录。即使应用程序崩溃，日志也不会丢失。

## 配置

配置保存在 `~/.config/isaaclab_train_tool/config.json`：

- **Python 环境**：Conda 或 venv 环境设置
- **默认参数**：保存的训练/测试参数
- **最近工作空间**：快速访问最近使用的项目
- **工作空间历史**：最多20条最近工作空间路径
- **语言**：界面语言偏好
- **日志保存路径**：自动保存日志的目录

## 键盘快捷键

| 快捷键 | 操作 |
|--------|------|
| Ctrl+O | 打开工作空间目录 |
| Ctrl+, | 打开设置 |
| Ctrl+Q | 退出应用 |

## 目录结构

```
isaaclab_train_tool/
├── main.py              # 应用入口
├── main_window.py       # 主窗口界面
├── config_dialog.py     # 设置对话框
├── config.py            # 配置管理
├── models.py            # 数据模型
├── workspace_scanner.py # 工作空间扫描逻辑
├── tmux_manager.py      # tmux 会话管理
├── i18n.py              # 国际化
├── requirements.txt     # Python 依赖
├── README.md            # 英文文档
└── README_CN.md         # 中文文档
```

## 常见问题

### "未配置 Python 环境"

进入"编辑 > 设置..."，可以：
- 扫描 Conda/venv 环境
- 或手动输入环境路径

### "scripts 目录中未找到脚本"

确保选择的目录是有效的 Isaac Lab 项目，包含 `scripts/` 目录且其中有 `train.py` 或 `play.py`。

### 终端附加不工作

工具会自动检测终端模拟器。如果不工作：
- 确保安装了 tmux
- 尝试安装支持的终端（gnome-terminal、konsole、xfce4-terminal 等）

### 日志文件限制在约2000行

对于新会话，tmux history-limit 设置为 50000 行。v1.0.1 之前创建的旧会话可能仍使用默认的 2000 限制。创建新会话以使用增加的限制。

## 更新日志

### v1.0.1
- 添加工作空间历史下拉框（最多20条）
- 添加源码包安装/卸载功能
- 添加启动和浏览选择时的自动扫描
- 修复 tmux history-limit（现在为 50000 行）
- 添加实时日志追加保存（每3秒）
- 修复信号连接问题

### v1.0.0
- 初始版本
- 基本工作空间扫描和任务发现
- Train/Play 模式支持
- tmux 会话管理
- 多语言支持（中文/英文）

## 许可证

MIT License