#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主窗口"""

import os
import re
import shutil
import subprocess
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QGroupBox,
    QSpinBox, QCheckBox, QMessageBox, QFileDialog, QListWidget,
    QListWidgetItem, QSplitter, QTextEdit, QStatusBar, QMenu, QAction,
    QMenuBar, QStackedWidget, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QColor, QIcon, QPixmap, QCursor

from models import Mode, WorkspaceInfo, ScriptInfo, TaskInfo, SessionInfo
from config import ConfigManager
from config_dialog import ConfigDialog
from workspace_scanner import WorkspaceScanner
from tmux_manager import get_tmux_manager
import i18n


# ANSI 颜色代码映射
ANSI_COLORS = {
    '30': '#000000',  # 黑色
    '31': '#e74c3c',  # 红色
    '32': '#2ecc71',  # 绿色
    '33': '#f39c12',  # 黄色
    '34': '#3498db',  # 蓝色
    '35': '#9b59b6',  # 紫色
    '36': '#1abc9c',  # 青色
    '37': '#ecf0f1',  # 白色
    '90': '#7f8c8d',  # 亮黑色
    '91': '#ff6b6b',  # 亮红色
    '92': '#55efc4',  # 亮绿色
    '93': '#ffeaa7',  # 亮黄色
    '94': '#74b9ff',  # 亮蓝色
    '95': '#a29bfe',  # 亮紫色
    '96': '#81ecec',  # 亮青色
    '97': '#ffffff',  # 亮白色
}


def extract_number_from_filename(filename: str) -> int:
    """从文件名中提取数字用于排序

    Args:
        filename: 文件名，如 "model_1000.pt"

    Returns:
        int: 提取的数字，如果没有数字则返回 0
    """
    import re
    # 匹配文件名中的数字（包括下划线后的数字）
    match = re.search(r'(\d+)\.pt$', filename)
    if match:
        return int(match.group(1))
    # 尝试匹配任意数字
    numbers = re.findall(r'\d+', filename)
    if numbers:
        return int(numbers[-1])  # 返回最后一个数字
    return 0


def sort_pt_files_by_number(files: list) -> list:
    """按文件名中的数字降序排序

    Args:
        files: 文件名列表

    Returns:
        list: 排序后的文件名列表
    """
    return sorted(files, key=lambda f: extract_number_from_filename(f), reverse=True)


def sort_runs_by_number(runs: list) -> list:
    """按最新 checkpoint 数字降序排序 run

    Args:
        runs: run 信息列表，每个元素包含 'latest_model' 和 'algorithm' 字段

    Returns:
        list: 排序后的 run 列表
    """
    def get_run_number(r):
        latest_model = r.get('latest_model', '')
        algorithm = r.get('algorithm', 'rsl_rl')
        return extract_checkpoint_number(latest_model, algorithm)

    return sorted(runs, key=get_run_number, reverse=True)


# 不同算法的 checkpoint 搜索配置
CHECKPOINT_PATTERNS = {
    "rsl_rl": {
        "log_dir": "rsl_rl",
        "extensions": [".pt"],
        "prefix": "model_",
        "subdir": None,  # 直接在 run 目录
        "number_pattern": r"model_(\d+)\.pt"  # model_100.pt
    },
    "sb3": {
        "log_dir": "sb3",
        "extensions": [".zip"],
        "prefix": "model_",
        "subdir": None,
        "number_pattern": r"model_(\d+)_steps\.zip"  # model_1000_steps.zip
    },
    "skrl": {
        "log_dir": "skrl",
        "extensions": [".pt"],
        "prefix": "agent_",
        "subdir": "checkpoints",
        "number_pattern": r"agent_(\d+)\.pt"  # agent_100.pt
    },
    "rl_games": {
        "log_dir": "rl_games",
        "extensions": [".pth"],
        "prefix": "",
        "subdir": "nn",
        "number_pattern": r"ep_(\d+)"  # last_xxx_ep_100_rew_xxx.pth
    }
}


def extract_checkpoint_number(filename: str, algorithm: str) -> int:
    """根据算法类型从 checkpoint 文件名中提取数字

    Args:
        filename: 文件名
        algorithm: 算法类型

    Returns:
        int: 提取的数字，如果没有匹配则返回 0
    """
    pattern = CHECKPOINT_PATTERNS.get(algorithm, CHECKPOINT_PATTERNS["rsl_rl"])
    number_pattern = pattern.get("number_pattern", r"(\d+)")

    match = re.search(number_pattern, filename)
    if match:
        return int(match.group(1))

    # 如果特定模式没匹配，尝试通用数字提取
    numbers = re.findall(r'\d+', filename)
    if numbers:
        return int(numbers[-1])
    return 0


def sort_checkpoints_by_number(checkpoints: list, algorithm: str) -> list:
    """按 checkpoint 数字降序排序

    Args:
        checkpoints: checkpoint 文件名列表
        algorithm: 算法类型

    Returns:
        list: 排序后的文件名列表
    """
    return sorted(checkpoints, key=lambda f: extract_checkpoint_number(f, algorithm), reverse=True)


def detect_terminal() -> str:
    """检测用户默认终端

    Returns:
        str: 终端命令名称，如 'gnome-terminal', 'konsole' 等
    """
    # 优先检查环境变量
    terminal_env = os.environ.get('TERMINAL', '')
    if terminal_env and shutil.which(terminal_env):
        return terminal_env

    # 检查 TERM 环境变量
    term = os.environ.get('TERM', '')
    if term and shutil.which(term):
        return term

    # 按优先级检测常见终端
    terminals = [
        'gnome-terminal',
        'konsole',
        'xfce4-terminal',
        'mate-terminal',
        'lxterminal',
        'terminator',
        'tilix',
        'alacritty',
        'kitty',
        'xterm',
        'rxvt',
    ]

    for term in terminals:
        if shutil.which(term):
            return term

    # 默认返回 gnome-terminal
    return 'gnome-terminal'


def detect_isaaclab_path(python_cmd: str = None) -> str:
    """检测 Isaac Lab 安装路径

    Args:
        python_cmd: Python 命令路径（可选），用于查找包位置

    Returns:
        str: Isaac Lab 路径，如果未检测到则返回空字符串
    """
    print(f"[IsaacLab检测] 开始检测，python_cmd={python_cmd}")

    if not python_cmd:
        print(f"[IsaacLab检测] 未提供 python_cmd，无法检测")
        return ''

    # 使用 pip show isaaclab 获取包信息
    print(f"[IsaacLab检测] 执行 pip show isaaclab...")
    try:
        result = subprocess.run(
            [python_cmd, "-m", "pip", "show", "isaaclab"],
            capture_output=True, text=True, timeout=10
        )
        print(f"[IsaacLab检测] pip show 结果: returncode={result.returncode}")
        print(f"[IsaacLab检测] stdout:\n{result.stdout}")
        print(f"[IsaacLab检测] stderr: {result.stderr.strip()[:200]}")

        if result.returncode == 0 and result.stdout.strip():
            # 解析 Location 或 Editable project location
            location = None
            editable_location = None

            for line in result.stdout.split('\n'):
                if line.startswith('Location:'):
                    location = line.split(':', 1)[1].strip()
                elif line.startswith('Editable project location:'):
                    editable_location = line.split(':', 1)[1].strip()

            print(f"[IsaacLab检测] Location: {location}")
            print(f"[IsaacLab检测] Editable location: {editable_location}")

            # 优先使用 Editable project location（-e 安装的方式）
            pkg_path = editable_location or location

            if pkg_path:
                print(f"[IsaacLab检测] 包路径: {pkg_path}")
                # isaaclab 包路径通常是: /path/to/IsaacLab/source/isaaclab
                # Isaac Lab 根目录就是包路径的父目录的父目录（去掉 source/isaaclab）
                # 或者直接去掉 /source/isaaclab 部分

                # 尝试向上查找包含 isaaclab.sh 或 source 目录的路径
                path = pkg_path
                while path:
                    isaaclab_sh = os.path.join(path, 'isaaclab.sh')
                    source_dir = os.path.join(path, 'source')

                    if os.path.exists(isaaclab_sh):
                        print(f"[IsaacLab检测] 找到 isaaclab.sh: {isaaclab_sh}")
                        print(f"[IsaacLab检测] Isaac Lab 根目录: {path}")
                        return path

                    if os.path.isdir(source_dir):
                        # 检查 source 目录下是否有 isaaclab 子目录
                        isaaclab_subdir = os.path.join(source_dir, 'isaaclab')
                        if os.path.isdir(isaaclab_subdir):
                            print(f"[IsaacLab检测] 找到 source/isaaclab 目录")
                            print(f"[IsaacLab检测] Isaac Lab 根目录: {path}")
                            return path

                    parent = os.path.dirname(path)
                    if parent == path:
                        break
                    path = parent

                print(f"[IsaacLab检测] 从包路径向上查找未找到根目录")

    except subprocess.TimeoutExpired:
        print(f"[IsaacLab检测] pip show 超时（10秒）")
    except Exception as e:
        print(f"[IsaacLab检测] pip show 异常: {type(e).__name__}: {e}")

    print(f"[IsaacLab检测] 未找到 Isaac Lab")
    return ''


def get_terminal_attach_command(terminal: str, session_name: str) -> str:
    """获取终端附加命令

    Args:
        terminal: 终端名称
        session_name: tmux 会话名称

    Returns:
        str: 完整的终端启动命令
    """
    if terminal in ['gnome-terminal', 'mate-terminal', 'xfce4-terminal', 'lxterminal']:
        return f"{terminal} -- bash -c 'tmux attach -t {session_name}; exec bash'"
    elif terminal == 'konsole':
        return f"konsole -e bash -c 'tmux attach -t {session_name}; exec bash'"
    elif terminal == 'terminator':
        return f"terminator -e 'bash -c \"tmux attach -t {session_name}; exec bash\"'"
    elif terminal in ['tilix', 'alacritty', 'kitty']:
        return f"{terminal} -e bash -c 'tmux attach -t {session_name}; exec bash'"
    else:
        # xterm, rxvt 等通用格式
        return f"{terminal} -e bash -c 'tmux attach -t {session_name}; exec bash'"


def parse_ansi_to_html(text: str) -> str:
    """将ANSI颜色代码转换为HTML

    Args:
        text: 包含ANSI转义序列的文本

    Returns:
        转换后的HTML文本
    """
    # 转义HTML特殊字符（但保留ANSI代码）
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # ANSI转义序列正则
    ansi_pattern = re.compile(r'\x1b\[([0-9;]*)m')

    result = []
    current_color = None
    last_end = 0

    for match in ansi_pattern.finditer(text):
        # 添加之前的文本
        if match.start() > last_end:
            chunk = text[last_end:match.start()]
            if current_color:
                result.append(f'<span style="color:{current_color}">{chunk}</span>')
            else:
                result.append(chunk)

        # 解析颜色代码
        codes = match.group(1).split(';')
        if codes == ['0'] or codes == ['']:
            current_color = None  # 重置
        else:
            for code in codes:
                if code in ANSI_COLORS:
                    current_color = ANSI_COLORS[code]
                elif code == '0':
                    current_color = None
                elif code == '1':
                    pass  # 粗体，暂不处理

        last_end = match.end()

    # 添加剩余文本
    if last_end < len(text):
        chunk = text[last_end:]
        if current_color:
            result.append(f'<span style="color:{current_color}">{chunk}</span>')
        else:
            result.append(chunk)

    html = ''.join(result)

    # 处理换行，保留空格
    html = html.replace('\n', '<br>')
    html = html.replace('  ', '&nbsp;&nbsp;')

    return html


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()

        self.config_manager = ConfigManager()
        self.tmux_manager = get_tmux_manager()

        # 设置语言
        i18n.set_language(self.config_manager.config.language)

        self.current_workspace: WorkspaceInfo = None
        self.current_session: SessionInfo = None

        # Log panel state
        self.log_auto_scroll = True
        # 日志存储：按 session_name 存储
        self.session_logs: dict = {}  # {session_name: log_content}

        self.setWindowTitle("Isaac Lab Train Tool")
        self.setMinimumSize(1400, 800)

        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(__file__), "icon.jpeg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._init_ui()
        self._init_menu()
        self._load_last_workspace()
        self._load_params_from_config()
        self._load_last_session_config()

        # 定时器检查会话状态
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._check_session_status)
        self.status_timer.start(2000)  # 每2秒检查一次

        # 日志自动刷新定时器
        self.log_refresh_timer = QTimer()
        self.log_refresh_timer.timeout.connect(self._auto_refresh_log)

        # 日志追加保存定时器（每3秒追加保存一次）
        self.log_append_timer = QTimer()
        self.log_append_timer.timeout.connect(self._append_log_to_file)
        self.log_append_timer.start(3000)  # 每3秒追加一次

        # 记录每个 session 上次保存的日志长度
        self.session_log_saved_length = {}  # session_name -> 已保存的字符数

    def _init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        self.file_menu = menubar.addMenu(i18n.t("menu.file"))

        self.open_action = QAction(i18n.t("menu.open_workspace"), self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self._open_workspace_dir)
        self.file_menu.addAction(self.open_action)

        self.browse_action = QAction(i18n.t("menu.select_workspace"), self)
        self.browse_action.triggered.connect(self._browse_workspace)
        self.file_menu.addAction(self.browse_action)

        self.new_project_action = QAction(i18n.t("menu.new_project"), self)
        self.new_project_action.triggered.connect(self._create_new_project)
        self.file_menu.addAction(self.new_project_action)

        self.file_menu.addSeparator()

        self.exit_action = QAction(i18n.t("menu.exit"), self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)

        # 编辑菜单
        self.edit_menu = menubar.addMenu(i18n.t("menu.edit"))

        self.config_action = QAction(i18n.t("menu.settings"), self)
        self.config_action.setShortcut("Ctrl+,")
        self.config_action.triggered.connect(self._show_config_dialog)
        self.edit_menu.addAction(self.config_action)

        # 语言子菜单
        self.lang_menu = self.edit_menu.addMenu(i18n.t("menu.language"))
        self.lang_zh_action = QAction("中文", self)
        self.lang_zh_action.triggered.connect(lambda: self._switch_language("zh"))
        self.lang_en_action = QAction("English", self)
        self.lang_en_action.triggered.connect(lambda: self._switch_language("en"))
        self.lang_menu.addAction(self.lang_zh_action)
        self.lang_menu.addAction(self.lang_en_action)

        # 帮助菜单
        self.help_menu = menubar.addMenu(i18n.t("menu.help"))

        self.about_action = QAction(i18n.t("menu.about"), self)
        self.about_action.triggered.connect(self._show_about)
        self.help_menu.addAction(self.about_action)

    def _init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主水平分割器
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(1)

        # 左侧主面板
        left_widget = QWidget()
        main_layout = QVBoxLayout(left_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Isaac Lab 安装路径显示（包含标签、自动检测和手动配置按钮）
        self.isaaclab_layout = QHBoxLayout()
        self.isaaclab_label = QLabel()
        self.isaaclab_auto_btn = QPushButton(i18n.t("btn.auto_detect"))
        self.isaaclab_auto_btn.setStyleSheet("padding: 2px 8px;")
        self.isaaclab_auto_btn.clicked.connect(self._auto_detect_isaaclab_path)
        self.isaaclab_manual_btn = QPushButton(i18n.t("btn.manual_config"))
        self.isaaclab_manual_btn.setStyleSheet("padding: 2px 8px;")
        self.isaaclab_manual_btn.clicked.connect(self._manual_config_isaaclab_path)

        self.isaaclab_layout.addWidget(self.isaaclab_label)
        self.isaaclab_layout.addWidget(self.isaaclab_auto_btn)
        self.isaaclab_layout.addWidget(self.isaaclab_manual_btn)
        self.isaaclab_layout.addStretch()

        self._update_isaaclab_display()

        main_layout.addLayout(self.isaaclab_layout)

        # Workspace选择区域
        self.workspace_group = QGroupBox(i18n.t("group.workspace"))
        workspace_main_layout = QVBoxLayout()

        # 第一行：路径输入和按钮
        workspace_layout = QHBoxLayout()

        self.workspace_combo = QComboBox()
        self.workspace_combo.setEditable(True)
        self.workspace_combo.lineEdit().setPlaceholderText(i18n.t("placeholder.workspace"))
        self.workspace_combo.currentTextChanged.connect(self._on_workspace_changed)

        self.browse_btn = QPushButton(i18n.t("label.browse"))
        self.browse_btn.clicked.connect(self._browse_workspace)

        self.scan_btn = QPushButton(i18n.t("label.scan"))
        self.scan_btn.clicked.connect(self._scan_workspace)

        workspace_layout.addWidget(self.workspace_combo)
        workspace_layout.addWidget(self.browse_btn)
        workspace_layout.addWidget(self.scan_btn)

        workspace_main_layout.addLayout(workspace_layout)

        # 第二行：源码安装状态和按钮
        source_layout = QHBoxLayout()

        self.source_status_label = QLabel("")
        self.source_status_label.setStyleSheet("color: #666; font-size: 11px;")

        self.install_source_btn = QPushButton(i18n.t("btn.install_source"))
        self.install_source_btn.clicked.connect(self._toggle_source_install)
        self.install_source_btn.setEnabled(False)

        source_layout.addWidget(self.source_status_label)
        source_layout.addStretch()
        source_layout.addWidget(self.install_source_btn)

        workspace_main_layout.addLayout(source_layout)

        self.workspace_group.setLayout(workspace_main_layout)
        main_layout.addWidget(self.workspace_group)

        # 脚本和任务选择区域
        self.selection_group = QGroupBox(i18n.t("group.script_task"))
        selection_layout = QFormLayout()

        # 脚本目录
        self.script_dir_combo = QComboBox()
        self.script_dir_combo.currentTextChanged.connect(self._on_script_dir_changed)
        selection_layout.addRow(i18n.t("label.script_dir"), self.script_dir_combo)

        # 任务
        self.task_combo = QComboBox()
        self.task_combo.currentIndexChanged.connect(self._on_task_changed)
        selection_layout.addRow(i18n.t("label.task"), self.task_combo)

        # 任务类型提示
        self.task_type_label = QLabel("")
        self.task_type_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        selection_layout.addRow(i18n.t("label.type"), self.task_type_label)

        self.selection_group.setLayout(selection_layout)
        main_layout.addWidget(self.selection_group)

        # 参数设置区域 - 使用StackedWidget区分Train和Play参数
        self.params_group = QGroupBox(i18n.t("group.parameters"))
        params_group_layout = QVBoxLayout()
        self.params_stack = QStackedWidget()

        # --- Train模式参数页 ---
        train_params_widget = QWidget()
        train_params_layout = QFormLayout(train_params_widget)

        self.train_num_envs_spin = QSpinBox()
        self.train_num_envs_spin.setRange(1, 100000)
        self.train_num_envs_spin.valueChanged.connect(self._update_cmd_preview)
        train_params_layout.addRow(i18n.t("label.num_envs"), self.train_num_envs_spin)

        self.max_iter_spin = QSpinBox()
        self.max_iter_spin.setRange(1, 100000000)
        self.max_iter_spin.valueChanged.connect(self._update_cmd_preview)
        train_params_layout.addRow(i18n.t("label.max_iter"), self.max_iter_spin)

        self.train_headless_check = QCheckBox()
        self.train_headless_check.stateChanged.connect(self._update_cmd_preview)
        train_params_layout.addRow(i18n.t("label.headless"), self.train_headless_check)

        # Live stream选项：空(禁用)、1(公网IP)、2(局域网IP)
        self.train_livestream_combo = QComboBox()
        self.train_livestream_combo.addItem(i18n.t("combo.disabled"), 0)
        self.train_livestream_combo.addItem(i18n.t("combo.public_ip"), 1)
        self.train_livestream_combo.addItem(i18n.t("combo.local_ip"), 2)
        self.train_livestream_combo.currentIndexChanged.connect(self._on_train_livestream_changed)
        self.train_livestream_combo.currentIndexChanged.connect(self._update_cmd_preview)
        train_params_layout.addRow(i18n.t("label.livestream"), self.train_livestream_combo)

        # Enable cameras选项
        self.train_enable_cameras_combo = QComboBox()
        self.train_enable_cameras_combo.addItem(i18n.t("combo.disabled"), 0)
        self.train_enable_cameras_combo.addItem(i18n.t("combo.enabled"), 1)
        self.train_enable_cameras_combo.currentIndexChanged.connect(self._update_cmd_preview)
        train_params_layout.addRow(i18n.t("label.enable_cameras"), self.train_enable_cameras_combo)

        # Resume选项
        self.train_resume_check = QCheckBox()
        self.train_resume_check.stateChanged.connect(self._on_train_resume_changed)
        train_params_layout.addRow(i18n.t("label.resume"), self.train_resume_check)

        # Load run选项
        self.train_load_run_combo = QComboBox()
        self.train_load_run_combo.setEnabled(False)
        self.train_load_run_combo.currentTextChanged.connect(self._on_train_load_run_changed)
        train_params_layout.addRow(i18n.t("label.load_run"), self.train_load_run_combo)

        # Checkpoint选项
        self.train_checkpoint_combo = QComboBox()
        self.train_checkpoint_combo.setEnabled(False)
        self.train_checkpoint_combo.currentTextChanged.connect(self._update_cmd_preview)
        train_params_layout.addRow(i18n.t("label.checkpoint"), self.train_checkpoint_combo)

        # 刷新runs按钮
        self.train_refresh_runs_btn = QPushButton(i18n.t("btn.refresh_runs"))
        self.train_refresh_runs_btn.clicked.connect(self._refresh_train_runs)
        self.train_refresh_runs_btn.setEnabled(False)
        train_params_layout.addRow("", self.train_refresh_runs_btn)

        self.params_stack.addWidget(train_params_widget)

        # --- Play模式参数页 ---
        play_params_widget = QWidget()
        play_params_layout = QFormLayout(play_params_widget)

        self.play_num_envs_spin = QSpinBox()
        self.play_num_envs_spin.setRange(1, 100000)
        self.play_num_envs_spin.valueChanged.connect(self._update_cmd_preview)
        play_params_layout.addRow(i18n.t("label.num_envs"), self.play_num_envs_spin)

        self.play_headless_check = QCheckBox()
        self.play_headless_check.stateChanged.connect(self._update_cmd_preview)
        play_params_layout.addRow(i18n.t("label.headless"), self.play_headless_check)

        # Live stream选项：空(禁用)、1(公网IP)、2(局域网IP)
        self.play_livestream_combo = QComboBox()
        self.play_livestream_combo.addItem(i18n.t("combo.disabled"), 0)
        self.play_livestream_combo.addItem(i18n.t("combo.public_ip"), 1)
        self.play_livestream_combo.addItem(i18n.t("combo.local_ip"), 2)
        self.play_livestream_combo.currentIndexChanged.connect(self._on_play_livestream_changed)
        self.play_livestream_combo.currentIndexChanged.connect(self._update_cmd_preview)
        play_params_layout.addRow(i18n.t("label.livestream"), self.play_livestream_combo)

        # Enable cameras选项
        self.play_enable_cameras_combo = QComboBox()
        self.play_enable_cameras_combo.addItem(i18n.t("combo.disabled"), 0)
        self.play_enable_cameras_combo.addItem(i18n.t("combo.enabled"), 1)
        self.play_enable_cameras_combo.currentIndexChanged.connect(self._update_cmd_preview)
        play_params_layout.addRow(i18n.t("label.enable_cameras"), self.play_enable_cameras_combo)

        # Load run选项
        self.play_load_run_combo = QComboBox()
        self.play_load_run_combo.currentTextChanged.connect(self._on_play_load_run_changed)
        play_params_layout.addRow(i18n.t("label.load_run"), self.play_load_run_combo)

        # Checkpoint选项
        self.play_checkpoint_combo = QComboBox()
        self.play_checkpoint_combo.currentTextChanged.connect(self._update_cmd_preview)
        play_params_layout.addRow(i18n.t("label.checkpoint"), self.play_checkpoint_combo)

        # 刷新runs按钮
        self.play_refresh_runs_btn = QPushButton(i18n.t("btn.refresh_runs"))
        self.play_refresh_runs_btn.clicked.connect(self._refresh_play_runs)
        self.play_refresh_runs_btn.setEnabled(False)
        play_params_layout.addRow("", self.play_refresh_runs_btn)

        self.params_stack.addWidget(play_params_widget)

        params_group_layout.addWidget(self.params_stack)

        # 通用参数
        common_layout = QFormLayout()

        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 100000)
        self.seed_spin.valueChanged.connect(self._update_cmd_preview)
        common_layout.addRow(i18n.t("label.seed"), self.seed_spin)

        self.extra_params_edit = QLineEdit()
        self.extra_params_edit.setPlaceholderText(i18n.t("placeholder.extra_params"))
        self.extra_params_edit.textChanged.connect(self._update_cmd_preview)
        common_layout.addRow(i18n.t("label.extra_params"), self.extra_params_edit)

        params_group_layout.addLayout(common_layout)
        self.params_group.setLayout(params_group_layout)
        main_layout.addWidget(self.params_group)

        # 命令预览区域
        self.cmd_group = QGroupBox(i18n.t("group.command_preview"))
        cmd_layout = QVBoxLayout()

        self.cmd_preview_edit = QTextEdit()
        self.cmd_preview_edit.setReadOnly(True)
        self.cmd_preview_edit.setMinimumHeight(100)
        self.cmd_preview_edit.setStyleSheet("background-color: #f5f5f5; font-family: monospace; font-size: 12px;")
        self.cmd_preview_edit.setPlaceholderText(i18n.t("placeholder.command"))
        self.cmd_preview_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        cmd_layout.addWidget(self.cmd_preview_edit)

        self.cmd_group.setLayout(cmd_layout)
        main_layout.addWidget(self.cmd_group)

        # 控制按钮区域
        control_layout = QHBoxLayout()

        self.settings_btn = QPushButton(i18n.t("btn.settings"))
        self.settings_btn.clicked.connect(self._show_config_dialog)

        self.save_params_btn = QPushButton(i18n.t("btn.save_params"))
        self.save_params_btn.clicked.connect(self._save_current_params)
        self.save_params_btn.setToolTip(i18n.t("tooltip.save_params"))

        self.run_btn = QPushButton(i18n.t("btn.run"))
        self.run_btn.clicked.connect(self._run_training)
        self.run_btn.setEnabled(False)

        self.stop_btn = QPushButton(i18n.t("btn.stop"))
        self.stop_btn.clicked.connect(self._stop_training)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setToolTip(i18n.t("tooltip.stop"))
        self.stop_btn.setStyleSheet("background-color: #ff6b6b;")

        self.attach_btn = QPushButton(i18n.t("btn.attach"))
        self.attach_btn.clicked.connect(self._attach_to_session)
        self.attach_btn.setEnabled(False)

        control_layout.addWidget(self.settings_btn)
        control_layout.addWidget(self.save_params_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.run_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.attach_btn)

        main_layout.addLayout(control_layout)

        # 会话状态区域
        self.status_group = QGroupBox(i18n.t("group.current_session"))
        status_layout = QFormLayout()

        self.session_name_label = QLabel(i18n.t("label.none"))
        status_layout.addRow(i18n.t("label.session_name"), self.session_name_label)

        self.session_status_label = QLabel(i18n.t("label.none"))
        status_layout.addRow(i18n.t("label.status"), self.session_status_label)

        self.status_group.setLayout(status_layout)
        main_layout.addWidget(self.status_group)

        # 将左侧面板添加到分割器
        main_splitter.addWidget(left_widget)

        # 右侧日志面板
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)

        self.log_group = QGroupBox(i18n.t("log.title"))
        log_group_layout = QVBoxLayout(self.log_group)

        # 日志工具栏
        log_toolbar = QHBoxLayout()

        self.log_refresh_btn = QPushButton(i18n.t("log.refresh"))
        self.log_refresh_btn.clicked.connect(self._refresh_log)

        self.log_save_btn = QPushButton(i18n.t("log.save"))
        self.log_save_btn.clicked.connect(self._save_log)

        self.log_clear_btn = QPushButton(i18n.t("log.clear"))
        self.log_clear_btn.clicked.connect(self._clear_log)

        self.log_auto_scroll_check = QCheckBox(i18n.t("log.auto_scroll"))
        self.log_auto_scroll_check.setChecked(True)
        self.log_auto_scroll_check.stateChanged.connect(self._on_auto_scroll_changed)

        log_toolbar.addWidget(self.log_refresh_btn)
        log_toolbar.addWidget(self.log_save_btn)
        log_toolbar.addWidget(self.log_clear_btn)
        log_toolbar.addStretch()
        log_toolbar.addWidget(self.log_auto_scroll_check)

        log_group_layout.addLayout(log_toolbar)

        # 日志内容区域
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        # 使用较小字体以显示更多字符（约190字符宽度）
        self.log_text_edit.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: monospace; font-size: 9px;")
        self.log_text_edit.setPlaceholderText(i18n.t("placeholder.log_content"))
        self.log_text_edit.setLineWrapMode(QTextEdit.NoWrap)  # 不自动换行
        log_group_layout.addWidget(self.log_text_edit)

        self.log_group.setLayout(log_group_layout)
        log_layout.addWidget(self.log_group)

        main_splitter.addWidget(log_widget)

        # 设置分割器大小比例 - 日志面板占更多宽度
        # 左侧控制面板：右侧日志面板 = 1 : 3
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)

        # 设置日志文本框的最小宽度（至少192字符 * 9px = 1728px）
        self.log_text_edit.setMinimumWidth(1728)

        # 将分割器设置为主布局
        splitter_layout = QVBoxLayout(central_widget)
        splitter_layout.setContentsMargins(5, 5, 5, 5)
        splitter_layout.addWidget(main_splitter)

        # 保存引用
        self.main_splitter = main_splitter
        self.log_widget = log_widget

        # 状态栏
        self.statusBar().showMessage(i18n.t("status.ready"))

    def _load_last_workspace(self):
        """加载上次的workspace和配置"""
        # 加载历史记录
        self._load_workspace_history()

        last = self.config_manager.config.last_workspace
        if last and os.path.isdir(last):
            self.workspace_combo.blockSignals(True)
            self.workspace_combo.setEditText(last)
            self.workspace_combo.blockSignals(False)
            # 自动扫描上次的 workspace
            self._scan_workspace()

        # 加载上次的其他配置
        config = self.config_manager.config
        if config.last_extra_params:
            self.extra_params_edit.setText(config.last_extra_params)

    def _load_workspace_history(self):
        """加载 Workspace 历史记录"""
        self.workspace_combo.blockSignals(True)
        self.workspace_combo.clear()
        history = self.config_manager.config.workspace_history or []
        for path in history:
            if os.path.isdir(path):
                self.workspace_combo.addItem(path)
        self.workspace_combo.blockSignals(False)

    def _save_workspace_history(self, path: str):
        """保存 Workspace 到历史记录"""
        if not path or not os.path.isdir(path):
            return

        history = list(self.config_manager.config.workspace_history or [])

        # 如果已存在，移到最前面
        if path in history:
            history.remove(path)

        history.insert(0, path)

        # 最多保留 20 条
        history = history[:20]

        self.config_manager.config.workspace_history = history
        self.config_manager.save()

        # 更新下拉列表（阻止信号触发）
        self._load_workspace_history()
        self.workspace_combo.blockSignals(True)
        self.workspace_combo.setEditText(path)
        self.workspace_combo.blockSignals(False)

    def _switch_language(self, lang: str):
        """切换语言"""
        if lang == i18n.get_language():
            return

        i18n.set_language(lang)
        self.config_manager.config.language = lang
        self.config_manager.save()
        self._update_ui_text()
        QMessageBox.information(self, i18n.t("msg.tip"), i18n.t("msg.language_changed"))

    def _update_ui_text(self):
        """更新所有UI文本"""
        # 更新菜单
        self.file_menu.setTitle(i18n.t("menu.file"))
        self.open_action.setText(i18n.t("menu.open_workspace"))
        self.browse_action.setText(i18n.t("menu.select_workspace"))
        self.new_project_action.setText(i18n.t("menu.new_project"))
        self.exit_action.setText(i18n.t("menu.exit"))
        self.edit_menu.setTitle(i18n.t("menu.edit"))
        self.config_action.setText(i18n.t("menu.settings"))
        self.lang_menu.setTitle(i18n.t("menu.language"))
        self.help_menu.setTitle(i18n.t("menu.help"))
        self.about_action.setText(i18n.t("menu.about"))

        # 更新 Isaac Lab 标签和按钮
        self.isaaclab_auto_btn.setText(i18n.t("btn.auto_detect"))
        self.isaaclab_manual_btn.setText(i18n.t("btn.manual_config"))
        self._update_isaaclab_display()

        # 更新 GroupBox 标题
        self.workspace_group.setTitle(i18n.t("group.workspace"))
        self.selection_group.setTitle(i18n.t("group.script_task"))
        self.params_group.setTitle(i18n.t("group.parameters"))
        self.cmd_group.setTitle(i18n.t("group.command_preview"))
        self.status_group.setTitle(i18n.t("group.current_session"))
        self.log_group.setTitle(i18n.t("log.title"))

        # 更新按钮
        self.browse_btn.setText(i18n.t("label.browse"))
        self.scan_btn.setText(i18n.t("label.scan"))
        self.settings_btn.setText(i18n.t("btn.settings"))
        self.save_params_btn.setText(i18n.t("btn.save_params"))
        self.run_btn.setText(i18n.t("btn.run"))
        self.stop_btn.setText(i18n.t("btn.stop"))
        self.attach_btn.setText(i18n.t("btn.attach"))
        self.train_refresh_runs_btn.setText(i18n.t("btn.refresh_runs"))
        self.play_refresh_runs_btn.setText(i18n.t("btn.refresh_runs"))

        # 更新工具提示
        self.save_params_btn.setToolTip(i18n.t("tooltip.save_params"))
        self.stop_btn.setToolTip(i18n.t("tooltip.stop"))

        # 更新日志面板
        self.log_refresh_btn.setText(i18n.t("log.refresh"))
        self.log_save_btn.setText(i18n.t("log.save"))
        self.log_clear_btn.setText(i18n.t("log.clear"))
        self.log_auto_scroll_check.setText(i18n.t("log.auto_scroll"))

        # 更新占位符
        self.workspace_combo.lineEdit().setPlaceholderText(i18n.t("placeholder.workspace"))
        self.extra_params_edit.setPlaceholderText(i18n.t("placeholder.extra_params"))
        self.cmd_preview_edit.setPlaceholderText(i18n.t("placeholder.command"))
        self.log_text_edit.setPlaceholderText(i18n.t("placeholder.log_content"))

        # 更新状态栏
        self.statusBar().showMessage(i18n.t("status.ready"))

        # 更新 ComboBox 项目（需要重新填充）
        self._update_combo_items()

    def _update_combo_items(self):
        """更新 ComboBox 项目文本"""
        # 保存当前选择
        train_livestream_idx = self.train_livestream_combo.currentIndex()
        train_cameras_idx = self.train_enable_cameras_combo.currentIndex()
        play_livestream_idx = self.play_livestream_combo.currentIndex()
        play_cameras_idx = self.play_enable_cameras_combo.currentIndex()

        # 更新 Train 模式 ComboBox
        self.train_livestream_combo.setItemText(0, i18n.t("combo.disabled"))
        self.train_livestream_combo.setItemText(1, i18n.t("combo.public_ip"))
        self.train_livestream_combo.setItemText(2, i18n.t("combo.local_ip"))
        self.train_enable_cameras_combo.setItemText(0, i18n.t("combo.disabled"))
        self.train_enable_cameras_combo.setItemText(1, i18n.t("combo.enabled"))

        # 更新 Play 模式 ComboBox
        self.play_livestream_combo.setItemText(0, i18n.t("combo.disabled"))
        self.play_livestream_combo.setItemText(1, i18n.t("combo.public_ip"))
        self.play_livestream_combo.setItemText(2, i18n.t("combo.local_ip"))
        self.play_enable_cameras_combo.setItemText(0, i18n.t("combo.disabled"))
        self.play_enable_cameras_combo.setItemText(1, i18n.t("combo.enabled"))

        # 恢复选择
        self.train_livestream_combo.setCurrentIndex(train_livestream_idx)
        self.train_enable_cameras_combo.setCurrentIndex(train_cameras_idx)
        self.play_livestream_combo.setCurrentIndex(play_livestream_idx)
        self.play_enable_cameras_combo.setCurrentIndex(play_cameras_idx)

    def _load_last_session_config(self):
        """加载上次会话配置"""
        config = self.config_manager.config

        # 加载上次的额外参数
        if config.last_extra_params:
            self.extra_params_edit.setText(config.last_extra_params)

    def _load_params_from_config(self):
        """从配置加载参数"""
        params = self.config_manager.config.default_params or {}

        # Train参数
        train_params = params.get("train", {})
        self.train_num_envs_spin.setValue(train_params.get("num_envs", 4096))
        self.max_iter_spin.setValue(train_params.get("max_iterations", 1000))
        self.train_headless_check.setChecked(train_params.get("headless", True))
        livestream_value = int(train_params.get("livestream", 0) or 0)
        self.train_livestream_combo.setCurrentIndex(livestream_value)
        enable_cameras_value = int(train_params.get("enable_cameras", 0) or 0)
        self.train_enable_cameras_combo.setCurrentIndex(enable_cameras_value)
        self._on_train_livestream_changed(self.train_livestream_combo.currentIndex())

        # Play参数
        play_params = params.get("play", {})
        self.play_num_envs_spin.setValue(play_params.get("num_envs", 1))
        self.play_headless_check.setChecked(play_params.get("headless", False))
        livestream_value = int(play_params.get("livestream", 0) or 0)
        self.play_livestream_combo.setCurrentIndex(livestream_value)
        enable_cameras_value = int(play_params.get("enable_cameras", 0) or 0)
        self.play_enable_cameras_combo.setCurrentIndex(enable_cameras_value)
        self._on_play_livestream_changed(self.play_livestream_combo.currentIndex())

        # 通用参数
        self.seed_spin.setValue(params.get("seed", -1))

    def _on_train_livestream_changed(self, index):
        """Train模式livestream变化时，强制勾选headless"""
        if index > 0:  # 选择了1或2
            self.train_headless_check.setChecked(True)
            self.train_headless_check.setEnabled(False)
        else:
            self.train_headless_check.setEnabled(True)

    def _on_play_livestream_changed(self, index):
        """Play模式livestream变化时，强制勾选headless"""
        if index > 0:  # 选择了1或2
            self.play_headless_check.setChecked(True)
            self.play_headless_check.setEnabled(False)
        else:
            self.play_headless_check.setEnabled(True)

    def _on_train_resume_changed(self, state):
        """Train模式resume选项变化"""
        enabled = state == Qt.Checked
        self.train_load_run_combo.setEnabled(enabled)
        self.train_checkpoint_combo.setEnabled(enabled)
        self.train_refresh_runs_btn.setEnabled(enabled)
        if enabled and self.current_workspace:
            self._refresh_train_runs()
        self._update_cmd_preview()

    def _on_train_load_run_changed(self, text: str):
        """Train模式load_run变化时，更新checkpoint列表"""
        run_data = self.train_load_run_combo.currentData()
        if run_data:
            self._load_train_checkpoints(run_data['path'])
        self._update_cmd_preview()

    def _refresh_train_runs(self):
        """刷新Train模式的运行记录"""
        if not self.current_workspace:
            return

        task_id = self.task_combo.currentData()
        if not task_id:
            return

        self.train_load_run_combo.clear()
        self.train_checkpoint_combo.clear()

        # 获取算法类型
        algorithm = self._get_algorithm_type()
        pattern = CHECKPOINT_PATTERNS.get(algorithm, CHECKPOINT_PATTERNS["rsl_rl"])

        # 搜索 logs/<algorithm> 目录
        logs_dir = os.path.join(self.current_workspace.path, "logs")
        if not os.path.isdir(logs_dir):
            self.train_load_run_combo.addItem(i18n.t("combo.no_logs"), None)
            return

        # 只搜索对应算法的日志目录
        algo_log_dir = os.path.join(logs_dir, pattern["log_dir"])
        runs = []

        if os.path.isdir(algo_log_dir):
            for task_dir in os.listdir(algo_log_dir):
                task_path = os.path.join(algo_log_dir, task_dir)
                if not os.path.isdir(task_path):
                    continue

                # 简化匹配逻辑：转换为小写并移除分隔符后比较
                task_id_normalized = task_id.lower().replace("_", "").replace("-", "")
                task_dir_normalized = task_dir.lower().replace("_", "").replace("-", "")

                # 如果任务名有包含关系或都包含某些关键词
                if (task_id_normalized in task_dir_normalized or
                    task_dir_normalized in task_id_normalized or
                    # 尝试匹配关键词
                    any(kw in task_dir_normalized for kw in task_id_normalized.split("v") if len(kw) > 2)):
                    for run_name in os.listdir(task_path):
                        run_path = os.path.join(task_path, run_name)
                        if os.path.isdir(run_path):
                            # 根据算法类型查找 checkpoint
                            try:
                                latest_model = self._get_latest_checkpoint(run_path, algorithm)
                                runs.append({
                                    'name': run_name,
                                    'path': run_path,
                                    'logger': pattern["log_dir"],
                                    'task': task_dir,
                                    'latest_model': latest_model,
                                    'algorithm': algorithm,
                                    'display': f"[{task_dir}] {run_name} ({i18n.t('msg.latest_model', latest_model)})"
                                })
                            except OSError:
                                pass

        if runs:
            # 按最新 checkpoint 数字降序排列
            runs = sort_runs_by_number(runs)
            for run in runs:
                self.train_load_run_combo.addItem(run['display'], run)

            # 加载第一个run的checkpoints
            self._load_train_checkpoints(runs[0]['path'])
        else:
            # 如果精确匹配没找到，尝试列出所有运行记录
            all_runs = self._list_all_runs()
            if all_runs:
                self.train_load_run_combo.addItem("-- 选择运行记录 --", None)
                for run in all_runs:
                    self.train_load_run_combo.addItem(run['display'], run)
            else:
                self.train_load_run_combo.addItem(i18n.t("combo.no_runs"), None)

    def _list_all_runs(self):
        """列出所有运行记录"""
        if not self.current_workspace:
            return []

        logs_dir = os.path.join(self.current_workspace.path, "logs")
        if not os.path.isdir(logs_dir):
            return []

        # 获取算法类型
        algorithm = self._get_algorithm_type()
        pattern = CHECKPOINT_PATTERNS.get(algorithm, CHECKPOINT_PATTERNS["rsl_rl"])

        runs = []
        # 只搜索对应算法的日志目录
        algo_log_dir = os.path.join(logs_dir, pattern["log_dir"])

        if os.path.isdir(algo_log_dir):
            for task_dir in os.listdir(algo_log_dir):
                task_path = os.path.join(algo_log_dir, task_dir)
                if not os.path.isdir(task_path):
                    continue

                for run_name in os.listdir(task_path):
                    run_path = os.path.join(task_path, run_name)
                    if os.path.isdir(run_path):
                        try:
                            latest_model = self._get_latest_checkpoint(run_path, algorithm)
                            runs.append({
                                'name': run_name,
                                'path': run_path,
                                'logger': pattern["log_dir"],
                                'task': task_dir,
                                'latest_model': latest_model,
                                'algorithm': algorithm,
                                'display': f"[{task_dir}] {run_name} ({i18n.t('msg.latest_model', latest_model)})"
                            })
                        except OSError:
                            pass

        runs = sort_runs_by_number(runs)
        return runs

    def _load_train_checkpoints(self, run_path: str):
        """加载Train模式的checkpoint列表"""
        self.train_checkpoint_combo.clear()

        if not run_path or not os.path.isdir(run_path):
            self.train_checkpoint_combo.addItem(i18n.t("label.none"), None)
            return

        # 根据算法类型查找 checkpoint
        algorithm = self._get_algorithm_type()
        checkpoints = self._find_checkpoints(run_path, algorithm)

        if checkpoints:
            for ckpt in checkpoints:
                self.train_checkpoint_combo.addItem(ckpt, ckpt)
        else:
            self.train_checkpoint_combo.addItem(i18n.t("combo.no_checkpoint"), None)

    def _refresh_play_runs(self):
        """刷新Play模式的运行记录"""
        if not self.current_workspace:
            return

        task_id = self.task_combo.currentData()
        if not task_id:
            return

        self.play_load_run_combo.clear()
        self.play_checkpoint_combo.clear()

        # 获取算法类型
        algorithm = self._get_algorithm_type()
        pattern = CHECKPOINT_PATTERNS.get(algorithm, CHECKPOINT_PATTERNS["rsl_rl"])

        # 搜索 logs/<algorithm> 目录
        logs_dir = os.path.join(self.current_workspace.path, "logs")
        if not os.path.isdir(logs_dir):
            self.play_load_run_combo.addItem(i18n.t("combo.no_logs"), None)
            return

        # 只搜索对应算法的日志目录
        algo_log_dir = os.path.join(logs_dir, pattern["log_dir"])
        runs = []

        if os.path.isdir(algo_log_dir):
            for task_dir in os.listdir(algo_log_dir):
                task_path = os.path.join(algo_log_dir, task_dir)
                if not os.path.isdir(task_path):
                    continue

                # 简化匹配逻辑：转换为小写并移除分隔符后比较
                task_id_normalized = task_id.lower().replace("_", "").replace("-", "")
                task_dir_normalized = task_dir.lower().replace("_", "").replace("-", "")

                if (task_id_normalized in task_dir_normalized or
                    task_dir_normalized in task_id_normalized or
                    any(kw in task_dir_normalized for kw in task_id_normalized.split("v") if len(kw) > 2)):
                    for run_name in os.listdir(task_path):
                        run_path = os.path.join(task_path, run_name)
                        if os.path.isdir(run_path):
                            try:
                                latest_model = self._get_latest_checkpoint(run_path, algorithm)
                                runs.append({
                                    'name': run_name,
                                    'path': run_path,
                                    'logger': pattern["log_dir"],
                                    'task': task_dir,
                                    'latest_model': latest_model,
                                    'algorithm': algorithm,
                                    'display': f"[{task_dir}] {run_name} ({i18n.t('msg.latest_model', latest_model)})"
                                })
                            except OSError:
                                pass

        if runs:
            runs = sort_runs_by_number(runs)
            for run in runs:
                self.play_load_run_combo.addItem(run['display'], run)
            self._load_play_checkpoints(runs[0]['path'])
        else:
            # 如果精确匹配没找到，尝试列出所有运行记录
            all_runs = self._list_all_runs()
            if all_runs:
                self.play_load_run_combo.addItem("-- 选择运行记录 --", None)
                for run in all_runs:
                    self.play_load_run_combo.addItem(run['display'], run)
            else:
                self.play_load_run_combo.addItem(i18n.t("combo.no_runs"), None)

    def _load_play_checkpoints(self, run_path: str):
        """加载Play模式的checkpoint列表"""
        self.play_checkpoint_combo.clear()

        if not run_path or not os.path.isdir(run_path):
            self.play_checkpoint_combo.addItem(i18n.t("label.none"), None)
            return

        # 根据算法类型查找 checkpoint
        algorithm = self._get_algorithm_type()
        checkpoints = self._find_checkpoints(run_path, algorithm)

        if checkpoints:
            for ckpt in checkpoints:
                self.play_checkpoint_combo.addItem(ckpt, ckpt)
        else:
            self.play_checkpoint_combo.addItem(i18n.t("combo.no_checkpoint"), None)

    def _on_play_load_run_changed(self, text: str):
        """Play模式load_run变化时，更新checkpoint列表"""
        run_data = self.play_load_run_combo.currentData()
        if run_data:
            self._load_play_checkpoints(run_data['path'])
        self._update_cmd_preview()

    def _update_cmd_preview(self):
        """更新命令预览"""
        if self.current_workspace:
            cmd = self._build_command()
            # 格式化命令，每个参数换行
            if cmd:
                parts = cmd.split(' ', 2)  # 分离 python script.py 和参数
                if len(parts) >= 3:
                    script_part = f"{parts[0]} {parts[1]}"
                    args_part = parts[2]
                    # 按参数分割，每个 -- 开头的参数换行，并添加反斜杠
                    args_list = args_part.split(' --')
                    formatted_args = ' \\\n    --'.join(args_list)
                    formatted_cmd = f"{script_part} \\\n    {formatted_args}"
                else:
                    formatted_cmd = cmd
                self.cmd_preview_edit.setPlainText(formatted_cmd)
            else:
                self.cmd_preview_edit.clear()
        else:
            self.cmd_preview_edit.clear()

    def _update_isaaclab_display(self):
        """更新 Isaac Lab 显示"""
        config = self.config_manager.config

        # 优先使用手动指定的路径
        if config.isaaclab_path_mode == "manual" and config.isaaclab_path_manual:
            manual_path = config.isaaclab_path_manual
            if os.path.isdir(manual_path):
                # 验证手动路径是否有效
                has_sh = os.path.exists(os.path.join(manual_path, 'isaaclab.sh'))
                has_source = os.path.exists(os.path.join(manual_path, 'source'))
                if has_sh or has_source:
                    self.isaaclab_label.setText(i18n.t("isaaclab.manual", manual_path))
                    self.isaaclab_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 5px;")
                    self.isaaclab_auto_btn.setVisible(True)
                    self.isaaclab_manual_btn.setVisible(True)
                    self.isaaclab_manual_btn.setText(i18n.t("btn.change_path"))
                else:
                    self.isaaclab_label.setText(i18n.t("isaaclab.manual", manual_path) + " (路径可能无效)")
                    self.isaaclab_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 5px;")
                    self.isaaclab_auto_btn.setVisible(True)
                    self.isaaclab_manual_btn.setVisible(True)
                    self.isaaclab_manual_btn.setText(i18n.t("btn.change_path"))
            else:
                self.isaaclab_label.setText(i18n.t("isaaclab.manual", manual_path) + " (路径不存在)")
                self.isaaclab_label.setStyleSheet("color: #f44336; font-weight: bold; padding: 5px;")
                self.isaaclab_auto_btn.setVisible(True)
                self.isaaclab_manual_btn.setVisible(True)
                self.isaaclab_manual_btn.setText(i18n.t("btn.change_path"))
        else:
            # 自动检测模式
            # 获取完整的 Python 可执行文件路径
            python_exe = self.config_manager.get_python_executable()

            if not python_exe or not os.path.exists(python_exe):
                # 未配置 Python 环境
                self.isaaclab_label.setText(i18n.t("isaaclab.not_configured"))
                self.isaaclab_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 5px;")
                self.isaaclab_auto_btn.setVisible(False)
                self.isaaclab_manual_btn.setVisible(True)
                self.isaaclab_manual_btn.setText(i18n.t("btn.manual_config"))
            else:
                # 使用配置的 Python 环境检测 Isaac Lab
                isaaclab_path = detect_isaaclab_path(python_exe)
                if isaaclab_path:
                    self.isaaclab_label.setText(i18n.t("isaaclab.detected", isaaclab_path))
                    self.isaaclab_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 5px;")
                    self.isaaclab_auto_btn.setVisible(True)
                    self.isaaclab_manual_btn.setVisible(False)
                else:
                    self.isaaclab_label.setText(i18n.t("isaaclab.not_detected"))
                    self.isaaclab_label.setStyleSheet("color: #f44336; font-weight: bold; padding: 5px;")
                    self.isaaclab_auto_btn.setVisible(True)
                    self.isaaclab_manual_btn.setVisible(True)
                    self.isaaclab_manual_btn.setText(i18n.t("btn.manual_config"))

    def _manual_config_isaaclab_path(self):
        """手动配置 Isaac Lab 路径"""
        # 弹出路径选择对话框
        current_path = self.config_manager.config.isaaclab_path_manual or ""
        path = QFileDialog.getExistingDirectory(
            self, i18n.t("config.select_isaaclab_path"), current_path
        )
        if path:
            # 验证路径是否有效
            has_sh = os.path.exists(os.path.join(path, 'isaaclab.sh'))
            has_source = os.path.exists(os.path.join(path, 'source'))

            if not has_sh and not has_source:
                reply = QMessageBox.question(
                    self, i18n.t("msg.warning"),
                    i18n.t("isaaclab.invalid_path_hint"),
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

            # 保存配置
            self.config_manager.config.isaaclab_path_mode = "manual"
            self.config_manager.config.isaaclab_path_manual = path
            self.config_manager.save()

            # 更新显示
            self._update_isaaclab_display()
            self.statusBar().showMessage(i18n.t("isaaclab.path_saved", path), 3000)

    def _auto_detect_isaaclab_path(self):
        """自动检测 Isaac Lab 路径"""
        python_exe = self.config_manager.get_python_executable()

        if not python_exe or not os.path.exists(python_exe):
            QMessageBox.warning(self, i18n.t("msg.warning"), i18n.t("isaaclab.no_python_env"))
            return

        self.statusBar().showMessage(i18n.t("isaaclab.detecting"))
        QApplication.processEvents()  # 更新UI

        isaaclab_path = detect_isaaclab_path(python_exe)

        if isaaclab_path:
            # 切换到自动检测模式
            self.config_manager.config.isaaclab_path_mode = "auto"
            self.config_manager.config.isaaclab_path_manual = ""
            self.config_manager.save()

            self._update_isaaclab_display()
            self.statusBar().showMessage(i18n.t("isaaclab.detected", isaaclab_path), 3000)
        else:
            QMessageBox.information(self, i18n.t("msg.tip"), i18n.t("isaaclab.detect_failed"))

    def _browse_workspace(self):
        """浏览选择workspace"""
        path = QFileDialog.getExistingDirectory(
            self, i18n.t("msg.select_dir")
        )
        if path:
            self.workspace_combo.setEditText(path)
            # 自动扫描选择的路径
            self._scan_workspace()

    def _open_workspace_dir(self):
        """打开当前workspace目录"""
        path = self.workspace_combo.currentText()
        if path and os.path.isdir(path):
            # 使用系统默认文件管理器打开目录
            import subprocess
            subprocess.Popen(['xdg-open', path])
        else:
            QMessageBox.warning(self, i18n.t("msg.tip"), i18n.t("msg.no_workspace"))

    def _create_new_project(self):
        """生成新的 Isaac Lab 工程"""
        # 获取 Isaac Lab 路径（优先手动配置）
        config = self.config_manager.config
        if config.isaaclab_path_mode == "manual" and config.isaaclab_path_manual:
            isaaclab_path = config.isaaclab_path_manual
        else:
            python_exe = self.config_manager.get_python_executable()
            isaaclab_path = detect_isaaclab_path(python_exe) if python_exe else ""

        if not isaaclab_path:
            QMessageBox.warning(self, i18n.t("msg.warning"), i18n.t("new_project.no_isaaclab"))
            return

        isaaclab_sh = os.path.join(isaaclab_path, "isaaclab.sh")
        if not os.path.exists(isaaclab_sh):
            QMessageBox.warning(self, i18n.t("msg.warning"), i18n.t("new_project.no_isaaclab"))
            return

        # 让用户选择新工程路径
        project_path = QFileDialog.getExistingDirectory(
            self, i18n.t("new_project.select_path")
        )
        if not project_path:
            return

        # 将路径复制到剪切板
        clipboard = QApplication.clipboard()
        clipboard.setText(project_path)

        # 检测终端
        terminal = detect_terminal()

        # 获取环境激活命令
        activation_cmd = self.config_manager.get_activation_command()

        # 构建命令：在选择的路径下运行 isaaclab.sh -n（使用绝对路径）
        # isaaclab.sh -n 会交互式地询问项目信息，需要用户在终端中操作
        if activation_cmd:
            cmd = f"{activation_cmd} && {isaaclab_sh} -n"
        else:
            cmd = f"{isaaclab_sh} -n"

        # 根据终端类型构建命令
        terminal_cmd = self._build_terminal_command(terminal, cmd, i18n.t("new_project.terminal_title"))

        # 显示提示
        QMessageBox.information(
            self, i18n.t("new_project.title"),
            i18n.t("new_project.path_label") + f" {project_path}\n\n" +
            i18n.t("new_project.path_copied") + "\n\n" +
            f"Terminal: {terminal}\n\n" +
            "请在终端中按照提示完成项目创建。\n" +
            "创建完成后，请手动选择新工程目录。"
        )

        # 在新终端中运行命令（工作目录为用户选择的路径）
        import subprocess
        subprocess.Popen(terminal_cmd, shell=True, cwd=project_path)

    def _build_terminal_command(self, terminal: str, cmd: str, title: str) -> str:
        """构建终端运行命令

        Args:
            terminal: 终端名称
            cmd: 要执行的命令
            title: 终端窗口标题

        Returns:
            str: 完整的终端启动命令
        """
        if terminal == 'gnome-terminal':
            return f"{terminal} --title='{title}' -- bash -c '{cmd}; exec bash'"
        elif terminal == 'konsole':
            return f"{terminal} -e bash -c '{cmd}; exec bash'"
        elif terminal == 'terminator':
            return f"terminator -e 'bash -c \"{cmd}; exec bash\"'"
        elif terminal in ['xfce4-terminal', 'mate-terminal', 'lxterminal']:
            return f"{terminal} --title='{title}' -e bash -c '{cmd}; exec bash'"
        elif terminal in ['tilix', 'alacritty', 'kitty']:
            return f"{terminal} -e bash -c '{cmd}; exec bash'"
        else:
            return f"{terminal} -e bash -c '{cmd}; exec bash'"

    def _on_workspace_changed(self, path: str):
        """workspace路径变化"""
        if path and os.path.isdir(path):
            self._scan_workspace()
        else:
            self._clear_workspace_info()
            self._clear_source_status()

    def _scan_workspace(self):
        """扫描workspace"""
        path = self.workspace_combo.currentText()
        if not path or not os.path.isdir(path):
            QMessageBox.warning(self, i18n.t("msg.error"), i18n.t("msg.invalid_dir"))
            return

        self.statusBar().showMessage(i18n.t("status.scanning"))

        try:
            scanner = WorkspaceScanner(path)
            self.current_workspace = scanner.scan()

            # 检查是否是有效的workspace
            if not self.current_workspace.has_scripts:
                QMessageBox.warning(
                    self, i18n.t("msg.warning"),
                    i18n.t("msg.no_scripts", path)
                )

            # 更新脚本目录下拉框
            self.script_dir_combo.clear()
            script_dirs = scanner.find_script_dirs()
            for dir_path in script_dirs:
                self.script_dir_combo.addItem(dir_path)

            # 恢复上次选择的脚本目录
            last_script_dir = self.config_manager.config.last_script_dir
            if last_script_dir:
                for i in range(self.script_dir_combo.count()):
                    if self.script_dir_combo.itemText(i) == last_script_dir:
                        self.script_dir_combo.setCurrentIndex(i)
                        break

            # 更新任务列表
            self._update_task_list()

            # 恢复上次选择的任务
            last_task = self.config_manager.config.last_task
            if last_task:
                for i in range(self.task_combo.count()):
                    if self.task_combo.itemData(i) == last_task:
                        self.task_combo.setCurrentIndex(i)
                        break

            # 启用运行记录刷新按钮
            self.train_refresh_runs_btn.setEnabled(True)
            self.play_refresh_runs_btn.setEnabled(True)

            # 检测源码安装状态
            self._check_source_install()

            # 保存到最近使用的workspace
            self.config_manager.add_recent_workspace(path)

            # 保存到历史记录
            self._save_workspace_history(path)

            self.statusBar().showMessage(i18n.t("status.scan_complete", len(self.current_workspace.tasks)))

        except Exception as e:
            QMessageBox.critical(self, i18n.t("msg.error"), i18n.t("status.scan_failed"))
            self.statusBar().showMessage(i18n.t("status.scan_failed"))

    def _clear_workspace_info(self):
        """清空workspace信息"""
        self.current_workspace = None
        self.script_dir_combo.clear()
        self.task_combo.clear()
        self.run_btn.setEnabled(False)
        self.train_refresh_runs_btn.setEnabled(False)
        self.play_refresh_runs_btn.setEnabled(False)
        self.cmd_preview_edit.clear()

    def _clear_source_status(self):
        """清空源码安装状态"""
        self.source_status_label.setText("")
        self.source_status_label.setStyleSheet("color: #666; font-size: 11px;")
        self.install_source_btn.setEnabled(False)
        self.install_source_btn.setText(i18n.t("btn.install_source"))

    def _check_source_install(self):
        """检测源码包是否已安装"""
        workspace_path = self.workspace_combo.currentText()
        source_dir = os.path.join(workspace_path, "source")

        if not os.path.isdir(source_dir):
            self._clear_source_status()
            self.source_status_label.setText(i18n.t("source.no_source_dir"))
            self.install_source_btn.setEnabled(False)
            return

        # 获取项目名（workspace 目录名）
        project_name = os.path.basename(workspace_path.rstrip("/"))
        project_source_dir = os.path.join(source_dir, project_name)

        if not os.path.isdir(project_source_dir):
            self._clear_source_status()
            self.source_status_label.setText(i18n.t("source.no_source_dir") + f" (source/{project_name})")
            self.install_source_btn.setEnabled(False)
            return

        # 获取 Python 可执行文件
        python_exe = self.config_manager.get_python_executable()
        if not python_exe or not os.path.exists(python_exe):
            python_exe = "python3"

        # 使用 pip show 检测包是否安装
        try:
            result = subprocess.run(
                [python_exe, "-m", "pip", "show", project_name],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                # 包已安装，解析安装路径
                install_path = None
                for line in result.stdout.split("\n"):
                    if line.startswith("Location:"):
                        install_path = line.split(":", 1)[1].strip()
                        break

                # 对于 -e 安装的包，检查 Editable project location
                editable_path = None
                for line in result.stdout.split("\n"):
                    if line.startswith("Editable project location:"):
                        editable_path = line.split(":", 1)[1].strip()
                        break

                if editable_path:
                    # 是 -e 安装的包
                    # 检查是否是当前工程
                    normalized_editable = os.path.normpath(editable_path)
                    normalized_project = os.path.normpath(project_source_dir)

                    if normalized_editable == normalized_project:
                        # 已安装且是当前工程
                        self.source_status_label.setText(f"✓ {i18n.t('source.installed')}: {editable_path}")
                        self.source_status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
                    else:
                        # 已安装但不是当前工程
                        self.source_status_label.setText(f"⚠ {i18n.t('source.installed_other')}: {editable_path}")
                        self.source_status_label.setStyleSheet("color: #FF9800; font-size: 11px;")
                elif install_path:
                    # 非 -e 安装
                    self.source_status_label.setText(f"⚠ {i18n.t('source.installed_non_editable')}: {install_path}")
                    self.source_status_label.setStyleSheet("color: #FF9800; font-size: 11px;")
                else:
                    self.source_status_label.setText(f"✓ {i18n.t('source.installed')}")
                    self.source_status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")

                self.install_source_btn.setText(i18n.t("btn.uninstall_source"))
                self.install_source_btn.setEnabled(True)
            else:
                # 包未安装
                self.source_status_label.setText(i18n.t("source.not_installed"))
                self.source_status_label.setStyleSheet("color: #f44336; font-size: 11px;")
                self.install_source_btn.setText(i18n.t("btn.install_source"))
                self.install_source_btn.setEnabled(True)

        except Exception as e:
            self._clear_source_status()
            self.source_status_label.setText(f"Error: {str(e)[:30]}")

    def _toggle_source_install(self):
        """安装或卸载源码"""
        workspace_path = self.workspace_combo.currentText()

        # 获取项目名（workspace 目录名）
        project_name = os.path.basename(workspace_path.rstrip("/"))

        # 检测终端
        terminal = detect_terminal()

        # 获取环境激活命令
        activation_cmd = self.config_manager.get_activation_command()

        # 获取 Python 可执行文件
        python_exe = self.config_manager.get_python_executable()
        if not python_exe or not os.path.exists(python_exe):
            python_exe = "python3"

        # 构建命令
        if activation_cmd:
            install_cmd = f"cd {workspace_path} && {activation_cmd} && {python_exe} -m pip install -e source/{project_name}"
            uninstall_cmd = f"{activation_cmd} && {python_exe} -m pip uninstall {project_name}"
        else:
            install_cmd = f"cd {workspace_path} && {python_exe} -m pip install -e source/{project_name}"
            uninstall_cmd = f"{python_exe} -m pip uninstall {project_name}"

        # 询问用户操作
        menu = QMenu(self)
        install_action = menu.addAction(i18n.t("btn.install_source"))
        uninstall_action = menu.addAction(i18n.t("btn.uninstall_source"))

        action = menu.exec_(QCursor.pos())

        if action == install_action:
            # 确认安装
            reply = QMessageBox.question(
                self, i18n.t("msg.confirm"),
                f"pip install -e source/{project_name}",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

            terminal_cmd = self._build_terminal_command(terminal, install_cmd, i18n.t("source.installing"))
            subprocess.Popen(terminal_cmd, shell=True)

        elif action == uninstall_action:
            # 确认卸载
            reply = QMessageBox.question(
                self, i18n.t("msg.confirm"),
                f"pip uninstall {project_name}",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

            terminal_cmd = self._build_terminal_command(terminal, uninstall_cmd, i18n.t("source.uninstalling"))
            subprocess.Popen(terminal_cmd, shell=True)

    def _on_script_dir_changed(self, script_dir: str):
        """脚本目录变化"""
        if not script_dir or not self.current_workspace:
            return

        # 刷新运行记录（因为不同算法有不同的日志目录）
        self._refresh_train_runs()
        self._refresh_play_runs()

        self._update_run_button()
        self._update_cmd_preview()

    def _get_algorithm_type(self) -> str:
        """根据脚本目录判断算法类型

        Returns:
            str: 算法类型 (rsl_rl, sb3, skrl, rl_games)
        """
        script_dir = self.script_dir_combo.currentText()
        for algo in CHECKPOINT_PATTERNS.keys():
            if algo in script_dir:
                return algo
        return "rsl_rl"  # 默认

    def _find_checkpoints(self, run_path: str, algorithm: str) -> list:
        """根据算法类型查找 checkpoint 文件

        Args:
            run_path: run 目录路径
            algorithm: 算法类型

        Returns:
            list: checkpoint 文件列表（按数字降序）
        """
        pattern = CHECKPOINT_PATTERNS.get(algorithm, CHECKPOINT_PATTERNS["rsl_rl"])

        # 确定搜索目录
        if pattern["subdir"]:
            search_dir = os.path.join(run_path, pattern["subdir"])
        else:
            search_dir = run_path

        if not os.path.isdir(search_dir):
            return []

        # 查找所有匹配的 checkpoint 文件
        checkpoints = []
        for f in os.listdir(search_dir):
            for ext in pattern["extensions"]:
                if f.endswith(ext):
                    checkpoints.append(f)
                    break

        # 按数字排序（降序）- 使用算法特定的排序
        if checkpoints:
            checkpoints = sort_checkpoints_by_number(checkpoints, algorithm)

        return checkpoints

    def _get_latest_checkpoint(self, run_path: str, algorithm: str) -> str:
        """获取最新的 checkpoint 文件名

        Args:
            run_path: run 目录路径
            algorithm: 算法类型

        Returns:
            str: 最新 checkpoint 文件名，如果没有则返回 "无"
        """
        checkpoints = self._find_checkpoints(run_path, algorithm)
        return checkpoints[0] if checkpoints else i18n.t("msg.no_model")

    def _on_task_changed(self, index: int):
        """任务变化时，根据任务名判断类型"""
        task_id = self.task_combo.currentData()
        if not task_id:
            self.task_type_label.setText("")
            return

        # 判断是 Train 还是 Play 任务
        is_play = "-Play" in task_id

        # 更新类型标签
        if is_play:
            self.task_type_label.setText("🎮 Play (播放)")
            self.task_type_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.params_stack.setCurrentIndex(1)  # Play参数页
        else:
            self.task_type_label.setText("🎯 Train (训练)")
            self.task_type_label.setStyleSheet("color: #2196F3; font-weight: bold;")
            self.params_stack.setCurrentIndex(0)  # Train参数页

        # 刷新运行记录
        if self.train_resume_check.isChecked() and self.train_refresh_runs_btn.isEnabled():
            self._refresh_train_runs()
        if self.play_refresh_runs_btn.isEnabled():
            self._refresh_play_runs()
        self._update_cmd_preview()

    def _is_play_task(self) -> bool:
        """判断当前任务是否是 Play 任务"""
        task_id = self.task_combo.currentData()
        if task_id:
            return "-Play" in task_id
        return False

    def _save_current_params(self):
        """保存当前参数到配置文件"""
        config = self.config_manager.config

        config.default_params = {
            "train": {
                "num_envs": self.train_num_envs_spin.value(),
                "max_iterations": self.max_iter_spin.value(),
                "headless": self.train_headless_check.isChecked(),
                "livestream": self.train_livestream_combo.currentData(),
                "enable_cameras": self.train_enable_cameras_combo.currentData(),
            },
            "play": {
                "num_envs": self.play_num_envs_spin.value(),
                "headless": self.play_headless_check.isChecked(),
                "livestream": self.play_livestream_combo.currentData(),
                "enable_cameras": self.play_enable_cameras_combo.currentData(),
            },
            "seed": self.seed_spin.value(),
        }

        # 保存当前会话配置
        config.last_task = self.task_combo.currentData() or ""
        config.last_script_dir = self.script_dir_combo.currentText() or ""
        config.last_mode = "play" if self._is_play_task() else "train"
        config.last_extra_params = self.extra_params_edit.text()

        self.config_manager.save()
        self.statusBar().showMessage(i18n.t("status.params_saved"), 3000)

    def _update_task_list(self):
        """更新任务列表"""
        self.task_combo.clear()

        if not self.current_workspace:
            return

        # 显示所有任务，不根据模式过滤
        for task in self.current_workspace.tasks:
            self.task_combo.addItem(task.display_name, task.task_id)

        self._update_run_button()

    def _update_run_button(self):
        """更新运行按钮状态"""
        # 当没有 session 或 session 已停止时，可以运行
        can_run = (
            self.current_workspace is not None and
            self.script_dir_combo.count() > 0 and
            self.task_combo.count() > 0 and
            (self.current_session is None or self.current_session.status == "stopped")
        )
        self.run_btn.setEnabled(can_run)

    def _build_command(self) -> str:
        """构建执行命令"""
        script_dir = self.script_dir_combo.currentText()
        is_train = not self._is_play_task()
        mode = "train" if is_train else "play"
        task_id = self.task_combo.currentData()

        # 根据模式获取参数
        if is_train:
            num_envs = self.train_num_envs_spin.value()
            headless = self.train_headless_check.isChecked()
            livestream = self.train_livestream_combo.currentData()
            enable_cameras = self.train_enable_cameras_combo.currentData()
            resume = self.train_resume_check.isChecked()
            load_run_data = self.train_load_run_combo.currentData()
            checkpoint_path = self.train_checkpoint_combo.currentData()
        else:
            num_envs = self.play_num_envs_spin.value()
            headless = self.play_headless_check.isChecked()
            livestream = self.play_livestream_combo.currentData()
            enable_cameras = self.play_enable_cameras_combo.currentData()
            load_run_data = self.play_load_run_combo.currentData()
            checkpoint_path = self.play_checkpoint_combo.currentData()

        # 构建参数
        args = []
        args.append(f"--task {task_id}")
        args.append(f"--num_envs {num_envs}")

        if is_train:
            args.append(f"--max_iterations {self.max_iter_spin.value()}")

        if self.seed_spin.value() >= 0:
            args.append(f"--seed {self.seed_spin.value()}")

        if headless:
            args.append("--headless")

        # livestream: 0=禁用, 1=公网IP, 2=局域网IP
        if livestream == 1:
            args.append("--livestream 1")
        elif livestream == 2:
            args.append("--livestream 2")

        # enable_cameras: 1=启用
        if enable_cameras == 1:
            args.append("--enable_cameras 1")

        # 获取算法类型
        algorithm = self._get_algorithm_type()

        # Train模式特定参数 - 根据算法类型生成不同的恢复训练命令
        if is_train and resume:
            if algorithm == "rsl_rl":
                # rsl_rl 使用 --resume --load_run --checkpoint 格式
                args.append("--resume")
                if load_run_data and isinstance(load_run_data, dict):
                    args.append(f"--load_run {load_run_data['name']}")
                if checkpoint_path:
                    # 使用相对于工作空间的路径
                    run_path = load_run_data['path']
                    workspace_path = self.current_workspace.path
                    ckpt_full_path = os.path.join(run_path, checkpoint_path)
                    ckpt_relative = os.path.relpath(ckpt_full_path, workspace_path)
                    args.append(f"--checkpoint {ckpt_relative}")
            else:
                # 其他算法使用完整 checkpoint 路径
                if load_run_data and isinstance(load_run_data, dict) and checkpoint_path:
                    # 构建 checkpoint 的完整路径
                    pattern = CHECKPOINT_PATTERNS.get(algorithm, CHECKPOINT_PATTERNS["rsl_rl"])
                    if pattern["subdir"]:
                        ckpt_full_path = os.path.join(load_run_data['path'], pattern["subdir"], checkpoint_path)
                    else:
                        ckpt_full_path = os.path.join(load_run_data['path'], checkpoint_path)
                    args.append(f"--checkpoint {ckpt_full_path}")

        # Play模式：根据算法类型加载 checkpoint
        if not is_train:
            if algorithm == "rsl_rl":
                # rsl_rl 使用 --load_run --checkpoint 格式
                if load_run_data and isinstance(load_run_data, dict):
                    args.append(f"--load_run {load_run_data['name']}")
                if checkpoint_path:
                    # 使用相对于工作空间的路径
                    run_path = load_run_data['path']
                    workspace_path = self.current_workspace.path
                    ckpt_full_path = os.path.join(run_path, checkpoint_path)
                    ckpt_relative = os.path.relpath(ckpt_full_path, workspace_path)
                    args.append(f"--checkpoint {ckpt_relative}")
            else:
                # 其他算法使用完整 checkpoint 路径
                if load_run_data and isinstance(load_run_data, dict) and checkpoint_path:
                    pattern = CHECKPOINT_PATTERNS.get(algorithm, CHECKPOINT_PATTERNS["rsl_rl"])
                    if pattern["subdir"]:
                        ckpt_full_path = os.path.join(load_run_data['path'], pattern["subdir"], checkpoint_path)
                    else:
                        ckpt_full_path = os.path.join(load_run_data['path'], checkpoint_path)
                    args.append(f"--checkpoint {ckpt_full_path}")

        # 额外参数
        extra = self.extra_params_edit.text().strip()
        if extra:
            args.append(extra)

        # 构建完整命令
        script_path = f"{script_dir}/{mode}.py"
        cmd = f"python3 {script_path} {' '.join(args)}"

        return cmd

    def _run_training(self):
        """运行训练"""
        if not self.current_workspace:
            return

        # 关闭上一个 session（如果存在）
        if self.current_session and self.tmux_manager.session_exists(self.current_session.session_name):
            self.tmux_manager.kill_session(self.current_session.session_name)
            self.current_session = None

        # 检查环境配置
        activation_cmd = self.config_manager.get_activation_command()
        if not activation_cmd and not self.config_manager.config.conda_env_name:
            reply = QMessageBox.question(
                self, i18n.t("msg.confirm"),
                i18n.t("msg.no_python_env"),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                self._show_config_dialog()
                return

        # 生成会话名称
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = self.config_manager.config.tmux_session_prefix
        task_name = self.task_combo.currentText().replace("-", "_").replace(":", "_")
        session_name = f"{prefix}_{task_name}_{timestamp}"

        # 构建命令
        cmd = self._build_command()

        # 计算日志面板的字符宽度
        char_width = self._get_log_panel_char_width()

        # 创建会话并运行
        try:
            if not self.tmux_manager.create_session(session_name, width=char_width):
                QMessageBox.critical(self, i18n.t("msg.error"), i18n.t("msg.create_session_failed"))
                return

            # 设置工作目录
            self.tmux_manager.send_command(session_name, f"cd {self.current_workspace.path}")

            # 激活环境
            if activation_cmd:
                self.tmux_manager.send_command(session_name, activation_cmd)

            # 执行命令
            self.tmux_manager.send_command(session_name, cmd)

            # 更新会话信息
            self.current_session = SessionInfo(
                session_name=session_name,
                workspace_path=self.current_workspace.path,
                task_id=self.task_combo.currentData(),
                mode=Mode.PLAY if self._is_play_task() else Mode.TRAIN,
                script_path=self.script_dir_combo.currentText(),
                status="running",
                start_time=datetime.now().timestamp()
            )

            self._update_session_status()
            self.run_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.attach_btn.setEnabled(True)

            # 初始化新 session 的日志存储
            if session_name not in self.session_logs:
                self.session_logs[session_name] = ""
            self.log_text_edit.clear()

            # 初始化日志保存长度记录（从头开始记录）
            self.session_log_saved_length[session_name] = 0

            # 启动日志自动刷新
            self.log_refresh_timer.start(1000)  # 每秒刷新一次

            self.statusBar().showMessage(i18n.t("status.session_started", session_name))

        except Exception as e:
            QMessageBox.critical(self, i18n.t("msg.error"), i18n.t("msg.start_failed", str(e)))

    def _stop_training(self):
        """停止训练 - 直接终止会话"""
        if not self.current_session:
            return

        reply = QMessageBox.question(
            self, i18n.t("msg.confirm"),
            i18n.t("msg.stop_training"),
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 自动保存日志
            if self.config_manager.config.auto_save_log:
                self._auto_save_log()

            self.tmux_manager.kill_session(self.current_session.session_name)
            self.current_session = None
            self._update_session_status()
            self._update_run_button()
            self.stop_btn.setEnabled(False)
            self.attach_btn.setEnabled(False)

            # 停止日志刷新，但保留内容
            self.log_refresh_timer.stop()
            self.statusBar().showMessage(i18n.t("status.session_ended"))

    def _auto_refresh_log(self):
        """自动刷新日志"""
        if self.current_session:
            # 即使 session 状态是 stopped，也尝试刷新（可能还有日志）
            self._refresh_log()

    def _refresh_log(self):
        """刷新日志内容 - 累积显示当前 session 的日志"""
        if not self.current_session:
            return

        session_name = self.current_session.session_name

        # 保存当前滚动位置比例（在获取新日志之前）
        scrollbar = self.log_text_edit.verticalScrollBar()
        scroll_ratio = scrollbar.value() / scrollbar.maximum() if scrollbar.maximum() > 0 else 1.0

        # 即使 session 不存在，也尝试从缓存显示
        if not self.tmux_manager.session_exists(session_name):
            # 从缓存显示
            cached = self.session_logs.get(session_name, "")
            if cached:
                html = parse_ansi_to_html(cached)
                self.log_text_edit.setHtml(f"<pre style='margin:0;white-space:pre-wrap;'>{html}</pre>")
                # 恢复滚动位置
                new_max = scrollbar.maximum()
                scrollbar.setValue(int(scroll_ratio * new_max))
            return

        output = self.tmux_manager.capture_output(session_name, lines=-1)
        if output:
            # 存储当前 session 的日志
            self.session_logs[session_name] = output

            # 显示当前 session 的日志
            html = parse_ansi_to_html(output)
            self.log_text_edit.setHtml(f"<pre style='margin:0;white-space:pre-wrap;'>{html}</pre>")

            # 恢复滚动位置
            new_max = scrollbar.maximum()
            if self.log_auto_scroll and scroll_ratio >= 0.95:
                # 用户在底部且开启了自动滚动，滚动到底部
                scrollbar.setValue(new_max)
            else:
                # 恢复到之前的滚动比例
                scrollbar.setValue(int(scroll_ratio * new_max))

    def _save_log(self):
        """保存日志到文件"""
        content = self.log_text_edit.toPlainText()
        if not content.strip():
            QMessageBox.information(self, i18n.t("msg.tip"), i18n.t("msg.log_empty"))
            return

        # 使用配置的日志保存路径
        log_path = self.config_manager.config.log_save_path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"log_{timestamp}.txt"

        if log_path:
            default_path = os.path.join(log_path, default_name)
        else:
            default_path = default_name

        path, _ = QFileDialog.getSaveFileName(
            self, i18n.t("msg.log_save_title"), default_path, "Text Files (*.txt)"
        )

        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.statusBar().showMessage(i18n.t("status.log_saved", path))

    def _append_log_to_file(self):
        """定时追加日志到文件（避免丢失日志）"""
        if not self.current_session:
            return

        # 检查是否启用了自动保存日志
        if not self.config_manager.config.auto_save_log:
            return

        session_name = self.current_session.session_name

        # 获取当前完整日志
        if self.tmux_manager.session_exists(session_name):
            content = self.tmux_manager.capture_output(session_name, lines=-1)
        else:
            content = self.session_logs.get(session_name, "")

        if not content or not content.strip():
            return

        # 获取上次已保存的长度
        saved_length = self.session_log_saved_length.get(session_name, 0)

        # 只保存新增部分
        if len(content) <= saved_length:
            return  # 没有新增内容

        new_content = content[saved_length:]

        # 确定保存路径
        log_path = self.config_manager.config.log_save_path
        if not log_path:
            if self.current_workspace and self.current_workspace.path:
                log_path = os.path.join(self.current_workspace.path, "logs", "saved_logs")
            else:
                log_path = os.path.expanduser("~/isaaclab_logs")

        try:
            os.makedirs(log_path, exist_ok=True)
        except Exception as e:
            print(f"创建日志目录失败: {e}")
            return

        # 清理 session 名称
        safe_session_name = session_name.replace(":", "_").replace("/", "_")
        filename = f"{safe_session_name}.txt"
        path = os.path.join(log_path, filename)

        try:
            # 追加写入
            with open(path, 'a', encoding='utf-8') as f:
                f.write(new_content)
            # 更新已保存长度
            self.session_log_saved_length[session_name] = len(content)
            print(f"日志追加保存: {len(new_content)} 字符 -> {path}")
        except Exception as e:
            print(f"追加保存日志失败: {e}")

    def _auto_save_log(self):
        """自动保存日志（session结束时追加剩余内容）"""
        # 直接从 tmux 获取日志，确保获取到最新内容
        if self.current_session:
            session_name = self.current_session.session_name
            # 尝试从 tmux 获取日志
            if self.tmux_manager.session_exists(session_name):
                content = self.tmux_manager.capture_output(session_name, lines=-1)
            else:
                # 如果 session 已结束，从缓存获取
                content = self.session_logs.get(session_name, "")
        else:
            content = self.log_text_edit.toPlainText()

        if not content or not content.strip():
            print("日志内容为空，跳过保存")
            return

        # 获取上次已保存的长度
        saved_length = self.session_log_saved_length.get(session_name, 0)

        # 只保存新增部分
        if len(content) <= saved_length:
            return  # 没有新增内容

        new_content = content[saved_length:]

        # 确定保存路径
        log_path = self.config_manager.config.log_save_path
        if not log_path:
            # 如果没有设置路径，使用 workspace 的 logs 目录
            if self.current_workspace and self.current_workspace.path:
                log_path = os.path.join(self.current_workspace.path, "logs", "saved_logs")
            else:
                log_path = os.path.expanduser("~/isaaclab_logs")

        # 确保目录存在
        try:
            os.makedirs(log_path, exist_ok=True)
        except Exception as e:
            self.statusBar().showMessage(f"创建日志目录失败: {e}")
            print(f"创建日志目录失败: {e}")
            return

        session_name = self.current_session.session_name if self.current_session else "unknown"
        # 清理 session 名称中的特殊字符
        safe_session_name = session_name.replace(":", "_").replace("/", "_")
        filename = f"{safe_session_name}.txt"
        path = os.path.join(log_path, filename)

        try:
            # 追加写入（而不是覆盖）
            with open(path, 'a', encoding='utf-8') as f:
                f.write(new_content)
            # 更新已保存长度
            self.session_log_saved_length[session_name] = len(content)
            self.statusBar().showMessage(i18n.t("status.log_auto_saved", path))
            print(f"日志追加保存完成: {path}")
        except Exception as e:
            self.statusBar().showMessage(i18n.t("status.log_save_failed", str(e)))
            print(f"追加保存日志失败: {e}")

    def _clear_log(self):
        """清除日志内容"""
        self.log_text_edit.clear()

    def _on_auto_scroll_changed(self, state):
        """自动滚动选项变化"""
        self.log_auto_scroll = state == Qt.Checked

    def _get_log_panel_char_width(self) -> int:
        """计算日志面板当前的字符宽度

        Returns:
            int: 字符宽度（列数）
        """
        # 字体大小为 9px，monospace 字体
        font_size = 9
        # 获取日志面板的像素宽度
        pixel_width = self.log_text_edit.width()
        # 计算字符宽度（考虑边距等，稍微减少一些）
        char_width = max(80, pixel_width // font_size - 2)
        return char_width

    def resizeEvent(self, event):
        """窗口大小变化事件"""
        super().resizeEvent(event)
        # 调整当前 tmux session 的宽度
        self._adjust_tmux_width()

    def _adjust_tmux_width(self):
        """调整当前 tmux session 的宽度"""
        if self.current_session:
            char_width = self._get_log_panel_char_width()
            self.tmux_manager.resize_window(
                self.current_session.session_name,
                width=char_width
            )

    def _attach_to_session(self):
        """附加到当前会话的终端"""
        if self.current_session:
            # 检测终端
            terminal = detect_terminal()

            # 显示提示
            QMessageBox.information(
                self, i18n.t("msg.tip"),
                i18n.t("msg.attach_terminal", terminal, self.current_session.session_name)
            )

            # 在新终端中运行tmux attach
            import subprocess
            terminal_cmd = get_terminal_attach_command(terminal, self.current_session.session_name)
            subprocess.Popen(terminal_cmd, shell=True)

    def _check_session_status(self):
        """检查当前会话状态"""
        if not self.current_session:
            return

        session_name = self.current_session.session_name
        exists = self.tmux_manager.session_exists(session_name)

        if not exists:
            # 会话被强制终止了
            self._on_session_ended(forced=True)
            return

        # 启动后5秒内不检查进程状态，避免误判
        if self.current_session.start_time:
            elapsed = datetime.now().timestamp() - self.current_session.start_time
            if elapsed < 5:
                # 在启动期间，确保状态是 running
                if self.current_session.status != "running":
                    self.current_session.status = "running"
                    self._update_session_status()
                return

        # 检查是否有活跃进程
        has_process = self.tmux_manager.has_active_process(session_name)
        print(f"[DEBUG] 检查会话状态: {session_name}, has_process={has_process}, current_status={self.current_session.status}")

        if not has_process and self.current_session.status == "running":
            # 进程已结束，但保留 session
            self.current_session.status = "stopped"
            self._update_session_status()
            self.stop_btn.setEnabled(True)  # 允许用户终止 session
            self.attach_btn.setEnabled(True)  # 仍然可以附加到 session
            self._update_run_button()  # 允许重新运行

            # 自动保存日志
            if self.config_manager.config.auto_save_log:
                self._auto_save_log()

            # 停止日志自动刷新，但保留内容
            self.log_refresh_timer.stop()
            self.statusBar().showMessage(i18n.t("status.session_stopped_preserved"))
            print(f"[DEBUG] 会话状态更新为 stopped")

    def _on_session_ended(self, forced: bool = False):
        """会话结束时的处理"""
        # 自动保存日志
        if self.config_manager.config.auto_save_log:
            self._auto_save_log()

        self.current_session = None
        self._update_session_status()
        self._update_run_button()
        self.stop_btn.setEnabled(False)
        self.attach_btn.setEnabled(False)

        # 停止日志刷新，但保留内容
        self.log_refresh_timer.stop()

        if forced:
            self.statusBar().showMessage(i18n.t("status.force_stopped"))
        else:
            self.statusBar().showMessage(i18n.t("status.session_ended"))

    def _update_session_status(self):
        """更新会话状态显示"""
        if self.current_session:
            self.session_name_label.setText(self.current_session.session_name)
            self.session_status_label.setText(self.current_session.status)
        else:
            self.session_name_label.setText(i18n.t("label.none"))
            self.session_status_label.setText(i18n.t("label.none"))

    def _show_config_dialog(self):
        """显示配置对话框"""
        dialog = ConfigDialog(self.config_manager, self)
        dialog.exec_()

        # 更新默认参数
        self._load_params_from_config()

        # 更新 Isaac Lab 标签
        self._update_isaaclab_display()

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, i18n.t("menu.about"),
            i18n.t("msg.about")
        )

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.current_session:
            # 创建自定义对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(i18n.t("msg.confirm"))
            msg_box.setText(i18n.t("msg.closing_session"))
            msg_box.setIcon(QMessageBox.Question)

            # 添加三个按钮
            btn_close_session = msg_box.addButton(i18n.t("btn.close_session"), QMessageBox.AcceptRole)
            btn_keep_running = msg_box.addButton(i18n.t("btn.keep_running"), QMessageBox.AcceptRole)
            btn_cancel = msg_box.addButton(i18n.t("btn.cancel"), QMessageBox.RejectRole)

            msg_box.exec_()

            clicked_button = msg_box.clickedButton()

            if clicked_button == btn_cancel:
                event.ignore()
                return
            elif clicked_button == btn_close_session:
                # 关闭当前的 session
                if self.tmux_manager.session_exists(self.current_session.session_name):
                    self.tmux_manager.kill_session(self.current_session.session_name)
            # btn_keep_running: 不关闭 session，让它在后台运行

        # 保存当前首页参数到配置
        config = self.config_manager.config
        config.last_task = self.task_combo.currentData() or ""
        config.last_script_dir = self.script_dir_combo.currentText() or ""
        config.last_mode = "play" if self._is_play_task() else "train"
        config.last_extra_params = self.extra_params_edit.text()

        # 保存首页当前参数为默认值
        config.default_params = {
            "train": {
                "num_envs": self.train_num_envs_spin.value(),
                "max_iterations": self.max_iter_spin.value(),
                "headless": self.train_headless_check.isChecked(),
                "livestream": self.train_livestream_combo.currentData(),
                "enable_cameras": self.train_enable_cameras_combo.currentData(),
            },
            "play": {
                "num_envs": self.play_num_envs_spin.value(),
                "headless": self.play_headless_check.isChecked(),
                "livestream": self.play_livestream_combo.currentData(),
                "enable_cameras": self.play_enable_cameras_combo.currentData(),
            },
            "seed": self.seed_spin.value(),
        }

        # 保存配置
        self.config_manager.save()
        event.accept()