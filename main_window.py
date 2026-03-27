#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主窗口"""

import os
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
from PyQt5.QtGui import QFont

from models import Mode, WorkspaceInfo, ScriptInfo, TaskInfo, SessionInfo
from config import ConfigManager
from config_dialog import ConfigDialog
from workspace_scanner import WorkspaceScanner
from tmux_manager import get_tmux_manager
import i18n


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

        self.setWindowTitle("Isaac Lab Train Tool")
        self.setMinimumSize(800, 600)

        self._init_ui()
        self._init_menu()
        self._load_last_workspace()
        self._load_params_from_config()
        self._load_last_session_config()

        # 定时器检查会话状态
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._check_session_status)
        self.status_timer.start(2000)  # 每2秒检查一次

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

        main_layout = QVBoxLayout(central_widget)

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

        # 模式
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Train", "Play"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        selection_layout.addRow("模式:", self.mode_combo)

        # 任务
        self.task_combo = QComboBox()
        self.task_combo.currentIndexChanged.connect(self._on_task_changed)
        selection_layout.addRow("任务:", self.task_combo)

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

        # 更新状态栏
        self.statusBar().showMessage(i18n.t("status.ready"))

    def _load_last_session_config(self):
        """加载上次会话配置"""
        config = self.config_manager.config

        # 加载上次的模式
        if config.last_mode == "play":
            self.mode_combo.setCurrentIndex(1)
        else:
            self.mode_combo.setCurrentIndex(0)

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
            if self.mode_combo.currentIndex() == 1:  # Play模式
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

        # 获取该目录下的脚本
        scanner = WorkspaceScanner(self.current_workspace.path)
        train_script, play_script = scanner.get_script_by_dir(script_dir)

        # 更新模式可用性
        self.mode_combo.setItemText(0, "Train" if train_script else "Train (不可用)")
        self.mode_combo.setItemText(1, "Play" if play_script else "Play (不可用)")

        # 启用/禁用模式
        model = self.mode_combo.model()
        model.item(0).setEnabled(train_script is not None)
        model.item(1).setEnabled(play_script is not None)

        # 选择可用模式
        if train_script:
            self.mode_combo.setCurrentIndex(0)
        elif play_script:
            self.mode_combo.setCurrentIndex(1)

        self._update_run_button()

    def _on_mode_changed(self, index: int):
        """模式变化"""
        # 保存当前任务
        current_task = self.task_combo.currentData()

        # 切换参数页
        self.params_stack.setCurrentIndex(index)
        self._update_task_list()

        # 恢复任务选择
        if current_task:
            for i in range(self.task_combo.count()):
                if self.task_combo.itemData(i) == current_task:
                    self.task_combo.setCurrentIndex(i)
                    break

        self._update_run_button()
        # 启用/禁用Play模式的刷新按钮
        if index == 1:  # Play模式
            self.play_refresh_runs_btn.setEnabled(self.current_workspace is not None)
        self._update_cmd_preview()

    def _on_task_changed(self, index: int):
        """任务变化时，刷新运行记录"""
        # 刷新Train模式的runs
        if self.train_resume_check.isChecked() and self.train_refresh_runs_btn.isEnabled():
            self._refresh_train_runs()
        # 刷新Play模式的runs
        if self.play_refresh_runs_btn.isEnabled():
            self._refresh_play_runs()
        self._update_cmd_preview()

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
        config.last_mode = "play" if self.mode_combo.currentIndex() == 1 else "train"
        config.last_extra_params = self.extra_params_edit.text()

        self.config_manager.save()
        self.statusBar().showMessage("参数已保存", 3000)

    def _update_task_list(self):
        """更新任务列表"""
        self.task_combo.clear()

        if not self.current_workspace:
            return

        mode = Mode.TRAIN if self.mode_combo.currentIndex() == 0 else Mode.PLAY

        for task in self.current_workspace.tasks:
            # 根据模式过滤任务
            if mode == Mode.TRAIN and task.is_play_task:
                continue
            if mode == Mode.PLAY and not task.is_play_task:
                continue

            self.task_combo.addItem(task.display_name, task.task_id)

        self._update_run_button()

    def _update_run_button(self):
        """更新运行按钮状态"""
        can_run = (
            self.current_workspace is not None and
            self.script_dir_combo.count() > 0 and
            self.task_combo.count() > 0 and
            self.current_session is None
        )
        self.run_btn.setEnabled(can_run)

    def _build_command(self) -> str:
        """构建执行命令"""
        script_dir = self.script_dir_combo.currentText()
        is_train = self.mode_combo.currentIndex() == 0
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
                mode=Mode.TRAIN if self.mode_combo.currentIndex() == 0 else Mode.PLAY,
                script_path=self.script_dir_combo.currentText(),
                status="running"
            )

            self._update_session_status()
            self.run_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.attach_btn.setEnabled(True)

            self.statusBar().showMessage(f"已启动会话: {session_name}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动失败: {e}")

    def _stop_training(self):
        """停止训练"""
        if not self.current_session:
            return

        reply = QMessageBox.question(
            self, "确认",
            "确定要停止当前训练吗？\n这会发送Ctrl+C到训练进程。",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.tmux_manager.send_interrupt(self.current_session.session_name)
            self.statusBar().showMessage("已发送中断信号")

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

        exists = self.tmux_manager.session_exists(self.current_session.session_name)

        if not exists:
            # 会话已结束
            self.current_session = None
            self._update_session_status()
            self._update_run_button()
            self.stop_btn.setEnabled(False)
            self.attach_btn.setEnabled(False)
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
        config.last_mode = "play" if self.mode_combo.currentIndex() == 1 else "train"
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