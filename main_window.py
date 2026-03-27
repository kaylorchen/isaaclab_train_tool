#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主窗口"""

import os
import re
import shutil
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QGroupBox,
    QSpinBox, QCheckBox, QMessageBox, QFileDialog, QListWidget,
    QListWidgetItem, QSplitter, QTextEdit, QStatusBar, QMenu, QAction,
    QMenuBar, QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QColor

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

        # Workspace选择区域
        workspace_group = QGroupBox("Workspace")
        workspace_layout = QHBoxLayout()

        self.workspace_edit = QLineEdit()
        self.workspace_edit.setPlaceholderText("选择Isaac Lab项目目录...")
        self.workspace_edit.textChanged.connect(self._on_workspace_changed)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self._browse_workspace)

        self.scan_btn = QPushButton("扫描")
        self.scan_btn.clicked.connect(self._scan_workspace)

        workspace_layout.addWidget(self.workspace_edit)
        workspace_layout.addWidget(self.browse_btn)
        workspace_layout.addWidget(self.scan_btn)

        workspace_group.setLayout(workspace_layout)
        main_layout.addWidget(workspace_group)

        # 脚本和任务选择区域
        selection_group = QGroupBox("脚本和任务")
        selection_layout = QFormLayout()

        # 脚本目录
        self.script_dir_combo = QComboBox()
        self.script_dir_combo.currentTextChanged.connect(self._on_script_dir_changed)
        selection_layout.addRow("脚本目录:", self.script_dir_combo)

        # 任务
        self.task_combo = QComboBox()
        self.task_combo.currentIndexChanged.connect(self._on_task_changed)
        selection_layout.addRow("任务:", self.task_combo)

        # 任务类型提示
        self.task_type_label = QLabel("")
        self.task_type_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        selection_layout.addRow("类型:", self.task_type_label)

        selection_group.setLayout(selection_layout)
        main_layout.addWidget(selection_group)

        # 参数设置区域 - 使用StackedWidget区分Train和Play参数
        params_group = QGroupBox("参数设置")
        params_group_layout = QVBoxLayout()
        self.params_stack = QStackedWidget()

        # --- Train模式参数页 ---
        train_params_widget = QWidget()
        train_params_layout = QFormLayout(train_params_widget)

        self.train_num_envs_spin = QSpinBox()
        self.train_num_envs_spin.setRange(1, 100000)
        self.train_num_envs_spin.valueChanged.connect(self._update_cmd_preview)
        train_params_layout.addRow("环境数量:", self.train_num_envs_spin)

        self.max_iter_spin = QSpinBox()
        self.max_iter_spin.setRange(1, 100000000)
        self.max_iter_spin.valueChanged.connect(self._update_cmd_preview)
        train_params_layout.addRow("最大迭代:", self.max_iter_spin)

        self.train_headless_check = QCheckBox()
        self.train_headless_check.stateChanged.connect(self._update_cmd_preview)
        train_params_layout.addRow("无头模式:", self.train_headless_check)

        # Live stream选项：空(禁用)、1(公网IP)、2(局域网IP)
        self.train_livestream_combo = QComboBox()
        self.train_livestream_combo.addItem("禁用", 0)
        self.train_livestream_combo.addItem("公网IP (1)", 1)
        self.train_livestream_combo.addItem("局域网IP (2)", 2)
        self.train_livestream_combo.currentIndexChanged.connect(self._on_train_livestream_changed)
        self.train_livestream_combo.currentIndexChanged.connect(self._update_cmd_preview)
        train_params_layout.addRow("实时流:", self.train_livestream_combo)

        # Enable cameras选项
        self.train_enable_cameras_combo = QComboBox()
        self.train_enable_cameras_combo.addItem("禁用", 0)
        self.train_enable_cameras_combo.addItem("启用 (1)", 1)
        self.train_enable_cameras_combo.currentIndexChanged.connect(self._update_cmd_preview)
        train_params_layout.addRow("启用相机:", self.train_enable_cameras_combo)

        # Resume选项
        self.train_resume_check = QCheckBox()
        self.train_resume_check.stateChanged.connect(self._on_train_resume_changed)
        train_params_layout.addRow("继续训练 (resume):", self.train_resume_check)

        # Load run选项
        self.train_load_run_combo = QComboBox()
        self.train_load_run_combo.setEnabled(False)
        self.train_load_run_combo.currentTextChanged.connect(self._on_train_load_run_changed)
        train_params_layout.addRow("加载运行 (load_run):", self.train_load_run_combo)

        # Checkpoint选项
        self.train_checkpoint_combo = QComboBox()
        self.train_checkpoint_combo.setEnabled(False)
        self.train_checkpoint_combo.currentTextChanged.connect(self._update_cmd_preview)
        train_params_layout.addRow("检查点 (checkpoint):", self.train_checkpoint_combo)

        # 刷新runs按钮
        self.train_refresh_runs_btn = QPushButton("刷新运行记录")
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
        play_params_layout.addRow("环境数量:", self.play_num_envs_spin)

        self.play_headless_check = QCheckBox()
        self.play_headless_check.stateChanged.connect(self._update_cmd_preview)
        play_params_layout.addRow("无头模式:", self.play_headless_check)

        # Live stream选项：空(禁用)、1(公网IP)、2(局域网IP)
        self.play_livestream_combo = QComboBox()
        self.play_livestream_combo.addItem("禁用", 0)
        self.play_livestream_combo.addItem("公网IP (1)", 1)
        self.play_livestream_combo.addItem("局域网IP (2)", 2)
        self.play_livestream_combo.currentIndexChanged.connect(self._on_play_livestream_changed)
        self.play_livestream_combo.currentIndexChanged.connect(self._update_cmd_preview)
        play_params_layout.addRow("实时流:", self.play_livestream_combo)

        # Enable cameras选项
        self.play_enable_cameras_combo = QComboBox()
        self.play_enable_cameras_combo.addItem("禁用", 0)
        self.play_enable_cameras_combo.addItem("启用 (1)", 1)
        self.play_enable_cameras_combo.currentIndexChanged.connect(self._update_cmd_preview)
        play_params_layout.addRow("启用相机:", self.play_enable_cameras_combo)

        # Load run选项
        self.play_load_run_combo = QComboBox()
        self.play_load_run_combo.currentTextChanged.connect(self._on_play_load_run_changed)
        play_params_layout.addRow("加载运行 (load_run):", self.play_load_run_combo)

        # Checkpoint选项
        self.play_checkpoint_combo = QComboBox()
        self.play_checkpoint_combo.currentTextChanged.connect(self._update_cmd_preview)
        play_params_layout.addRow("检查点 (checkpoint):", self.play_checkpoint_combo)

        # 刷新runs按钮
        self.play_refresh_runs_btn = QPushButton("刷新运行记录")
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
        common_layout.addRow("随机种子:", self.seed_spin)

        self.extra_params_edit = QLineEdit()
        self.extra_params_edit.setPlaceholderText("其他命令行参数，如: --logger wandb")
        self.extra_params_edit.textChanged.connect(self._update_cmd_preview)
        common_layout.addRow("额外参数:", self.extra_params_edit)

        params_group_layout.addLayout(common_layout)
        params_group.setLayout(params_group_layout)
        main_layout.addWidget(params_group)

        # 命令预览区域
        cmd_group = QGroupBox("命令预览")
        cmd_layout = QVBoxLayout()

        self.cmd_preview_edit = QTextEdit()
        self.cmd_preview_edit.setReadOnly(True)
        self.cmd_preview_edit.setMinimumHeight(100)
        self.cmd_preview_edit.setStyleSheet("background-color: #f5f5f5; font-family: monospace; font-size: 12px;")
        self.cmd_preview_edit.setPlaceholderText("运行命令将显示在这里...")
        self.cmd_preview_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        cmd_layout.addWidget(self.cmd_preview_edit)

        cmd_group.setLayout(cmd_layout)
        main_layout.addWidget(cmd_group)

        # 控制按钮区域
        control_layout = QHBoxLayout()

        self.settings_btn = QPushButton("设置")
        self.settings_btn.clicked.connect(self._show_config_dialog)

        self.save_params_btn = QPushButton("保存参数")
        self.save_params_btn.clicked.connect(self._save_current_params)
        self.save_params_btn.setToolTip("保存当前参数为默认值")

        self.run_btn = QPushButton("运行")
        self.run_btn.clicked.connect(self._run_training)
        self.run_btn.setEnabled(False)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._stop_training)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setToolTip("终止当前训练会话")
        self.stop_btn.setStyleSheet("background-color: #ff6b6b;")

        self.attach_btn = QPushButton("附加到终端")
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
        status_group = QGroupBox("当前会话")
        status_layout = QFormLayout()

        self.session_name_label = QLabel("无")
        status_layout.addRow("会话名称:", self.session_name_label)

        self.session_status_label = QLabel("无")
        status_layout.addRow("状态:", self.session_status_label)

        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # 将左侧面板添加到分割器
        main_splitter.addWidget(left_widget)

        # 右侧日志面板
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)

        log_group = QGroupBox("日志面板")
        log_group_layout = QVBoxLayout(log_group)

        # 日志工具栏
        log_toolbar = QHBoxLayout()

        self.log_refresh_btn = QPushButton("刷新")
        self.log_refresh_btn.clicked.connect(self._refresh_log)

        self.log_save_btn = QPushButton("保存")
        self.log_save_btn.clicked.connect(self._save_log)

        self.log_clear_btn = QPushButton("清除")
        self.log_clear_btn.clicked.connect(self._clear_log)

        self.log_auto_scroll_check = QCheckBox("自动滚动")
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
        self.log_text_edit.setPlaceholderText("日志内容将显示在这里...")
        self.log_text_edit.setLineWrapMode(QTextEdit.NoWrap)  # 不自动换行
        log_group_layout.addWidget(self.log_text_edit)

        log_group.setLayout(log_group_layout)
        log_layout.addWidget(log_group)

        main_splitter.addWidget(log_widget)

        # 设置分割器大小比例 - 日志面板占更多宽度
        # 左侧控制面板：右侧日志面板 = 1 : 3
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)

        # 设置日志文本框的最小宽度（约190字符 * 9px = 1710px）
        self.log_text_edit.setMinimumWidth(1200)

        # 将分割器设置为主布局
        splitter_layout = QVBoxLayout(central_widget)
        splitter_layout.setContentsMargins(5, 5, 5, 5)
        splitter_layout.addWidget(main_splitter)

        # 保存引用
        self.main_splitter = main_splitter
        self.log_widget = log_widget

        # 状态栏
        self.statusBar().showMessage("就绪")

    def _load_last_workspace(self):
        """加载上次的workspace和配置"""
        last = self.config_manager.config.last_workspace
        if last and os.path.isdir(last):
            self.workspace_edit.setText(last)

        # 加载上次的其他配置
        config = self.config_manager.config
        if config.last_extra_params:
            self.extra_params_edit.setText(config.last_extra_params)

    def _switch_language(self, lang: str):
        """切换语言"""
        if lang == i18n.get_language():
            return

        i18n.set_language(lang)
        self.config_manager.config.language = lang
        self.config_manager.save()
        self._update_ui_text()
        QMessageBox.information(self, i18n.t("menu.settings"),
                               "Language changed. Restart the application for full effect." if lang == "en"
                               else "语言已更改，重启应用以完全生效。")

    def _update_ui_text(self):
        """更新所有UI文本"""
        # 更新菜单
        self.file_menu.setTitle(i18n.t("menu.file"))
        self.open_action.setText(i18n.t("menu.open_workspace"))
        self.browse_action.setText(i18n.t("menu.select_workspace"))
        self.exit_action.setText(i18n.t("menu.exit"))
        self.edit_menu.setTitle(i18n.t("menu.edit"))
        self.config_action.setText(i18n.t("menu.settings"))
        self.lang_menu.setTitle(i18n.t("menu.language"))
        self.help_menu.setTitle(i18n.t("menu.help"))
        self.about_action.setText(i18n.t("menu.about"))

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

        # 日志面板按钮
        self.log_refresh_btn.setText(i18n.t("log.refresh"))
        self.log_save_btn.setText(i18n.t("log.save"))
        self.log_clear_btn.setText(i18n.t("log.clear"))
        self.log_auto_scroll_check.setText(i18n.t("log.auto_scroll"))

        # 更新状态栏
        self.statusBar().showMessage(i18n.t("status.ready"))

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

        # 搜索 logs 目录
        logs_dir = os.path.join(self.current_workspace.path, "logs")
        if not os.path.isdir(logs_dir):
            self.train_load_run_combo.addItem("logs目录不存在", None)
            return

        # 遍历 logs/<logger>/<task_name>/ 目录
        runs = []
        for logger_name in os.listdir(logs_dir):
            logger_path = os.path.join(logs_dir, logger_name)
            if not os.path.isdir(logger_path):
                continue

            for task_dir in os.listdir(logger_path):
                task_path = os.path.join(logger_path, task_dir)
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
                            # 查找最新的checkpoint
                            try:
                                pt_files = sorted([f for f in os.listdir(run_path) if f.endswith('.pt')])
                                latest_model = pt_files[-1] if pt_files else "无"
                                runs.append({
                                    'name': run_name,
                                    'path': run_path,
                                    'logger': logger_name,
                                    'task': task_dir,
                                    'latest_model': latest_model,
                                    'display': f"[{task_dir}] {run_name} (最新: {latest_model})"
                                })
                            except OSError:
                                pass

        if runs:
            # 按时间倒序排列
            runs.sort(key=lambda x: x['name'], reverse=True)
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
                self.train_load_run_combo.addItem("未找到运行记录", None)

    def _list_all_runs(self):
        """列出所有运行记录"""
        if not self.current_workspace:
            return []

        logs_dir = os.path.join(self.current_workspace.path, "logs")
        if not os.path.isdir(logs_dir):
            return []

        runs = []
        for logger_name in os.listdir(logs_dir):
            logger_path = os.path.join(logs_dir, logger_name)
            if not os.path.isdir(logger_path):
                continue

            for task_dir in os.listdir(logger_path):
                task_path = os.path.join(logger_path, task_dir)
                if not os.path.isdir(task_path):
                    continue

                for run_name in os.listdir(task_path):
                    run_path = os.path.join(task_path, run_name)
                    if os.path.isdir(run_path):
                        try:
                            pt_files = sorted([f for f in os.listdir(run_path) if f.endswith('.pt')])
                            latest_model = pt_files[-1] if pt_files else "无"
                            runs.append({
                                'name': run_name,
                                'path': run_path,
                                'logger': logger_name,
                                'task': task_dir,
                                'latest_model': latest_model,
                                'display': f"[{task_dir}] {run_name} (最新: {latest_model})"
                            })
                        except OSError:
                            pass

        runs.sort(key=lambda x: x['name'], reverse=True)
        return runs

    def _load_train_checkpoints(self, run_path: str):
        """加载Train模式的checkpoint列表"""
        self.train_checkpoint_combo.clear()

        if not run_path or not os.path.isdir(run_path):
            self.train_checkpoint_combo.addItem("无", None)
            return

        pt_files = sorted([f for f in os.listdir(run_path) if f.endswith('.pt')], reverse=True)
        if pt_files:
            for pt_file in pt_files:
                full_path = os.path.join(run_path, pt_file)
                self.train_checkpoint_combo.addItem(pt_file, full_path)
        else:
            self.train_checkpoint_combo.addItem("无检查点", None)

    def _refresh_play_runs(self):
        """刷新Play模式的运行记录"""
        if not self.current_workspace:
            return

        task_id = self.task_combo.currentData()
        if not task_id:
            return

        self.play_load_run_combo.clear()
        self.play_checkpoint_combo.clear()

        # 搜索 logs 目录
        logs_dir = os.path.join(self.current_workspace.path, "logs")
        if not os.path.isdir(logs_dir):
            self.play_load_run_combo.addItem("logs目录不存在", None)
            return

        # 遍历 logs/<logger>/<task_name>/ 目录
        runs = []
        for logger_name in os.listdir(logs_dir):
            logger_path = os.path.join(logs_dir, logger_name)
            if not os.path.isdir(logger_path):
                continue

            for task_dir in os.listdir(logger_path):
                task_path = os.path.join(logger_path, task_dir)
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
                                pt_files = sorted([f for f in os.listdir(run_path) if f.endswith('.pt')])
                                latest_model = pt_files[-1] if pt_files else "无"
                                runs.append({
                                    'name': run_name,
                                    'path': run_path,
                                    'logger': logger_name,
                                    'task': task_dir,
                                    'latest_model': latest_model,
                                    'display': f"[{task_dir}] {run_name} (最新: {latest_model})"
                                })
                            except OSError:
                                pass

        if runs:
            runs.sort(key=lambda x: x['name'], reverse=True)
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
                self.play_load_run_combo.addItem("未找到运行记录", None)

    def _load_play_checkpoints(self, run_path: str):
        """加载Play模式的checkpoint列表"""
        self.play_checkpoint_combo.clear()

        if not run_path or not os.path.isdir(run_path):
            self.play_checkpoint_combo.addItem("无", None)
            return

        pt_files = sorted([f for f in os.listdir(run_path) if f.endswith('.pt')], reverse=True)
        if pt_files:
            for pt_file in pt_files:
                full_path = os.path.join(run_path, pt_file)
                self.play_checkpoint_combo.addItem(pt_file, full_path)
        else:
            self.play_checkpoint_combo.addItem("无检查点", None)

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

    def _browse_workspace(self):
        """浏览选择workspace"""
        path = QFileDialog.getExistingDirectory(
            self, "选择Isaac Lab项目目录"
        )
        if path:
            self.workspace_edit.setText(path)

    def _open_workspace_dir(self):
        """打开当前workspace目录"""
        path = self.workspace_edit.text()
        if path and os.path.isdir(path):
            # 使用系统默认文件管理器打开目录
            import subprocess
            subprocess.Popen(['xdg-open', path])
        else:
            QMessageBox.warning(self, "提示", "请先选择有效的Workspace目录")

    def _on_workspace_changed(self, path: str):
        """workspace路径变化"""
        if path and os.path.isdir(path):
            self._scan_workspace()
        else:
            self._clear_workspace_info()

    def _scan_workspace(self):
        """扫描workspace"""
        path = self.workspace_edit.text()
        if not path or not os.path.isdir(path):
            QMessageBox.warning(self, "错误", "请选择有效的目录")
            return

        self.statusBar().showMessage("正在扫描...")

        try:
            scanner = WorkspaceScanner(path)
            self.current_workspace = scanner.scan()

            # 检查是否是有效的workspace
            if not self.current_workspace.has_scripts:
                QMessageBox.warning(
                    self, "警告",
                    f"未在 {path}/scripts 目录下找到训练或播放脚本"
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

            # 保存到最近使用的workspace
            self.config_manager.add_recent_workspace(path)

            self.statusBar().showMessage(f"扫描完成: {len(self.current_workspace.tasks)} 个任务")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"扫描失败: {e}")
            self.statusBar().showMessage("扫描失败")

    def _clear_workspace_info(self):
        """清空workspace信息"""
        self.current_workspace = None
        self.script_dir_combo.clear()
        self.task_combo.clear()
        self.run_btn.setEnabled(False)
        self.train_refresh_runs_btn.setEnabled(False)
        self.play_refresh_runs_btn.setEnabled(False)
        self.cmd_preview_edit.clear()

    def _on_script_dir_changed(self, script_dir: str):
        """脚本目录变化"""
        if not script_dir or not self.current_workspace:
            return

        self._update_run_button()

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
        self.statusBar().showMessage("参数已保存", 3000)

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

        # Train模式特定参数
        if is_train and resume:
            args.append("--resume")

        # load_run参数
        if load_run_data and isinstance(load_run_data, dict):
            args.append(f"--load_run {load_run_data['name']}")

        # checkpoint参数
        if checkpoint_path:
            args.append(f"--checkpoint {checkpoint_path}")

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

        # 检查环境配置
        activation_cmd = self.config_manager.get_activation_command()
        if not activation_cmd and not self.config_manager.config.conda_env_name:
            reply = QMessageBox.question(
                self, "确认",
                "未配置Python环境，将使用系统默认Python。\n是否继续？",
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

        # 创建会话并运行
        try:
            if not self.tmux_manager.create_session(session_name):
                QMessageBox.critical(self, "错误", "无法创建tmux会话")
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

            # 启动日志自动刷新
            self.log_refresh_timer.start(1000)  # 每秒刷新一次

            self.statusBar().showMessage(f"已启动会话: {session_name}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动失败: {e}")

    def _stop_training(self):
        """停止训练 - 直接终止会话"""
        if not self.current_session:
            return

        reply = QMessageBox.question(
            self, "确认",
            "确定要停止当前训练吗？\n这会终止tmux会话。",
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
            self.statusBar().showMessage("会话已终止")

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

        # 即使 session 不存在，也尝试从缓存显示
        if not self.tmux_manager.session_exists(session_name):
            # 从缓存显示
            cached = self.session_logs.get(session_name, "")
            if cached:
                html = parse_ansi_to_html(cached)
                self.log_text_edit.setHtml(f"<pre style='margin:0;white-space:pre-wrap;'>{html}</pre>")
            return

        output = self.tmux_manager.capture_output(session_name, lines=2000)
        if output:
            # 存储当前 session 的日志
            self.session_logs[session_name] = output

            # 显示当前 session 的日志
            html = parse_ansi_to_html(output)
            self.log_text_edit.setHtml(f"<pre style='margin:0;white-space:pre-wrap;'>{html}</pre>")

            if self.log_auto_scroll:
                cursor = self.log_text_edit.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.log_text_edit.setTextCursor(cursor)

    def _save_log(self):
        """保存日志到文件"""
        content = self.log_text_edit.toPlainText()
        if not content.strip():
            QMessageBox.information(self, "提示", "无日志内容")
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
            self, "保存日志", default_path, "Text Files (*.txt)"
        )

        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.statusBar().showMessage(f"日志已保存到: {path}")

    def _auto_save_log(self):
        """自动保存日志"""
        # 直接从 tmux 获取日志，确保获取到最新内容
        if self.current_session:
            session_name = self.current_session.session_name
            # 尝试从 tmux 获取日志
            if self.tmux_manager.session_exists(session_name):
                content = self.tmux_manager.capture_output(session_name, lines=5000)
            else:
                # 如果 session 已结束，从缓存获取
                content = self.session_logs.get(session_name, "")
        else:
            content = self.log_text_edit.toPlainText()

        if not content or not content.strip():
            print("日志内容为空，跳过保存")
            return

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
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.statusBar().showMessage(f"日志已自动保存到: {path}")
            print(f"日志已自动保存到: {path}")
        except Exception as e:
            self.statusBar().showMessage(f"自动保存日志失败: {e}")
            print(f"自动保存日志失败: {e}")

    def _clear_log(self):
        """清除日志内容"""
        self.log_text_edit.clear()

    def _on_auto_scroll_changed(self, state):
        """自动滚动选项变化"""
        self.log_auto_scroll = state == Qt.Checked

    def _attach_to_session(self):
        """附加到当前会话的终端"""
        if self.current_session:
            # 检测终端
            terminal = detect_terminal()

            # 显示提示
            QMessageBox.information(
                self, "提示",
                f"将在 {terminal} 中附加到会话: {self.current_session.session_name}\n\n"
                "按 Ctrl+B 然后按 D 可以分离会话"
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
            self.statusBar().showMessage("训练已停止，Session 保留")
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
            self.statusBar().showMessage("会话已强制终止")
        else:
            self.statusBar().showMessage("会话已结束")

    def _update_session_status(self):
        """更新会话状态显示"""
        if self.current_session:
            self.session_name_label.setText(self.current_session.session_name)
            self.session_status_label.setText(self.current_session.status)
        else:
            self.session_name_label.setText("无")
            self.session_status_label.setText("无")

    def _show_config_dialog(self):
        """显示配置对话框"""
        dialog = ConfigDialog(self.config_manager, self)
        dialog.exec_()

        # 更新默认参数
        self._load_params_from_config()

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, "关于",
            "Isaac Lab Train Tool\n\n"
            "用于管理Isaac Lab项目训练和播放的图形界面工具\n\n"
            "版本: 1.0.0"
        )

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.current_session:
            reply = QMessageBox.question(
                self, "确认",
                "有正在运行的训练会话。\n关闭窗口不会停止训练，会话将继续在后台运行。\n\n确定要关闭吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return

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