#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置对话框"""

import subprocess
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox, QFileDialog,
    QDialogButtonBox, QSpinBox, QCheckBox, QComboBox, QMessageBox,
    QStackedWidget, QWidget, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt

from config import ConfigManager
import i18n


def scan_conda_environments():
    """扫描系统中的conda环境

    Returns:
        list: [(env_name, env_path), ...]
    """
    environments = []

    try:
        # 尝试运行 conda env list 命令
        result = subprocess.run(
            ["conda", "env", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                line = line.strip()
                # 跳过注释和空行
                if not line or line.startswith("#"):
                    continue

                # 解析格式: env_name /path/to/env
                parts = line.split()
                if len(parts) >= 2:
                    env_name = parts[0]
                    env_path = parts[-1]
                    environments.append((env_name, env_path))

    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 如果conda命令不可用，尝试扫描常见路径
    if not environments:
        common_paths = [
            os.path.expanduser("~/miniconda3/envs"),
            os.path.expanduser("~/anaconda3/envs"),
            os.path.expanduser("~/miniforge3/envs"),
            "/opt/conda/envs",
            "/usr/local/anaconda3/envs",
        ]

        for envs_dir in common_paths:
            if os.path.isdir(envs_dir):
                for env_name in os.listdir(envs_dir):
                    env_path = os.path.join(envs_dir, env_name)
                    if os.path.isdir(env_path):
                        # 检查是否是有效的conda环境
                        if os.path.exists(os.path.join(env_path, "pyvenv.cfg")) or \
                           os.path.exists(os.path.join(env_path, "conda-meta")):
                            environments.append((env_name, env_path))

    return environments


def scan_venv_environments():
    """扫描常见的虚拟环境

    Returns:
        list: [(env_name, env_path), ...]
    """
    environments = []

    # 扫描常见的虚拟环境位置
    common_paths = [
        os.path.expanduser("~/.virtualenvs"),
        os.path.expanduser("~/venvs"),
        os.path.expanduser("~/envs"),
        os.path.expanduser("~/.local/share/virtualenvs"),
    ]

    for venvs_dir in common_paths:
        if os.path.isdir(venvs_dir):
            for env_name in os.listdir(venvs_dir):
                env_path = os.path.join(venvs_dir, env_name)
                activate_script = os.path.join(env_path, "bin", "activate")
                if os.path.isdir(env_path) and os.path.exists(activate_script):
                    environments.append((env_name, env_path))

    return environments


class ConfigDialog(QDialog):
    """配置对话框"""

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle(i18n.t("config.title"))
        self.setMinimumWidth(600)

        self._init_ui()
        self._load_config()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ========== 环境设置组 ==========
        env_group = QGroupBox(i18n.t("config.python_env"))
        env_layout = QVBoxLayout()

        # 环境类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel(i18n.t("config.env_type")))

        self.env_type_group = QButtonGroup(self)
        self.scan_env_radio = QRadioButton(i18n.t("config.scan_env"))
        self.local_env_radio = QRadioButton(i18n.t("config.local_env"))
        self.manual_env_radio = QRadioButton(i18n.t("config.manual_input"))

        self.env_type_group.addButton(self.scan_env_radio, 0)
        self.env_type_group.addButton(self.local_env_radio, 1)
        self.env_type_group.addButton(self.manual_env_radio, 2)

        self.scan_env_radio.setChecked(True)
        self.env_type_group.buttonClicked.connect(self._on_env_type_changed)

        type_layout.addWidget(self.scan_env_radio)
        type_layout.addWidget(self.local_env_radio)
        type_layout.addWidget(self.manual_env_radio)
        type_layout.addStretch()
        env_layout.addLayout(type_layout)

        # 环境选择区域（使用StackedWidget）
        self.env_stack = QStackedWidget()

        # --- 扫描环境页面 ---
        scan_page = QWidget()
        scan_page_layout = QVBoxLayout(scan_page)
        scan_page_layout.setContentsMargins(0, 0, 0, 0)

        # 扫描按钮行
        scan_btn_layout = QHBoxLayout()
        self.scan_conda_btn = QPushButton(i18n.t("config.scan_conda"))
        self.scan_conda_btn.clicked.connect(self._scan_conda_envs)
        self.scan_venv_btn = QPushButton(i18n.t("config.scan_venv"))
        self.scan_venv_btn.clicked.connect(self._scan_venv_envs)
        scan_btn_layout.addWidget(self.scan_conda_btn)
        scan_btn_layout.addWidget(self.scan_venv_btn)
        scan_btn_layout.addStretch()
        scan_page_layout.addLayout(scan_btn_layout)

        # 环境下拉框
        scan_form = QFormLayout()
        self.env_combo = QComboBox()
        self.env_combo.setMinimumWidth(450)
        self.env_combo.currentIndexChanged.connect(self._on_env_selected)
        scan_form.addRow(i18n.t("config.select_env"), self.env_combo)

        self.env_path_label = QLabel(i18n.t("config.not_selected"))
        self.env_path_label.setStyleSheet("color: gray; font-size: 11px;")
        scan_form.addRow(i18n.t("config.path"), self.env_path_label)

        scan_page_layout.addLayout(scan_form)
        self.env_stack.addWidget(scan_page)

        # --- 本机环境页面 ---
        local_page = QWidget()
        local_page_layout = QVBoxLayout(local_page)
        local_page_layout.setContentsMargins(0, 0, 0, 0)

        local_label = QLabel(i18n.t("config.use_default"))
        local_label.setStyleSheet("color: #666; padding: 10px;")
        local_page_layout.addWidget(local_label)
        self.env_stack.addWidget(local_page)

        # --- 手动输入页面 ---
        manual_page = QWidget()
        manual_page_layout = QVBoxLayout(manual_page)
        manual_page_layout.setContentsMargins(0, 0, 0, 0)

        manual_form = QFormLayout()

        self.manual_env_type_combo = QComboBox()
        self.manual_env_type_combo.addItems([i18n.t("config.conda_env"), i18n.t("config.venv")])
        manual_form.addRow(i18n.t("config.env_type"), self.manual_env_type_combo)

        self.manual_env_name_edit = QLineEdit()
        self.manual_env_name_edit.setPlaceholderText(i18n.t("config.env_name_placeholder"))
        manual_form.addRow(i18n.t("config.env_name"), self.manual_env_name_edit)

        self.manual_env_path_edit = QLineEdit()
        self.manual_env_path_edit.setPlaceholderText(i18n.t("config.env_path_placeholder"))
        manual_form.addRow(i18n.t("config.env_path"), self.manual_env_path_edit)

        browse_btn_layout = QHBoxLayout()
        self.browse_manual_btn = QPushButton(i18n.t("label.browse"))
        self.browse_manual_btn.clicked.connect(self._browse_manual_path)
        browse_btn_layout.addWidget(self.browse_manual_btn)
        browse_btn_layout.addStretch()
        manual_form.addRow("", browse_btn_layout)

        manual_page_layout.addLayout(manual_form)
        self.env_stack.addWidget(manual_page)

        env_layout.addWidget(self.env_stack)
        env_group.setLayout(env_layout)
        layout.addWidget(env_group)

        # ========== Isaac Lab 路径设置组 ==========
        isaaclab_group = QGroupBox(i18n.t("config.isaaclab_path"))
        isaaclab_layout = QVBoxLayout()

        # 路径模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel(i18n.t("config.isaaclab_path_mode")))

        self.isaaclab_mode_group = QButtonGroup(self)
        self.isaaclab_auto_radio = QRadioButton(i18n.t("config.isaaclab_auto_detect"))
        self.isaaclab_manual_radio = QRadioButton(i18n.t("config.isaaclab_manual"))

        self.isaaclab_mode_group.addButton(self.isaaclab_auto_radio, 0)
        self.isaaclab_mode_group.addButton(self.isaaclab_manual_radio, 1)

        self.isaaclab_auto_radio.setChecked(True)
        self.isaaclab_mode_group.buttonClicked.connect(self._on_isaaclab_mode_changed)

        mode_layout.addWidget(self.isaaclab_auto_radio)
        mode_layout.addWidget(self.isaaclab_manual_radio)
        mode_layout.addStretch()
        isaaclab_layout.addLayout(mode_layout)

        # 手动路径输入区域
        self.isaaclab_manual_widget = QWidget()
        manual_path_layout = QHBoxLayout(self.isaaclab_manual_widget)
        manual_path_layout.setContentsMargins(0, 0, 0, 0)

        self.isaaclab_path_edit = QLineEdit()
        self.isaaclab_path_edit.setPlaceholderText(i18n.t("config.isaaclab_path_placeholder"))
        manual_path_layout.addWidget(self.isaaclab_path_edit)

        self.browse_isaaclab_btn = QPushButton(i18n.t("label.browse"))
        self.browse_isaaclab_btn.clicked.connect(self._browse_isaaclab_path)
        manual_path_layout.addWidget(self.browse_isaaclab_btn)

        self.isaaclab_manual_widget.setVisible(False)  # 默认隐藏手动输入区域
        isaaclab_layout.addWidget(self.isaaclab_manual_widget)

        # 提示标签
        hint_label = QLabel(i18n.t("config.isaaclab_path_hint"))
        hint_label.setStyleSheet("color: #666; font-size: 11px;")
        isaaclab_layout.addWidget(hint_label)

        isaaclab_group.setLayout(isaaclab_layout)
        layout.addWidget(isaaclab_group)

        # ========== Train模式参数组 ==========
        train_group = QGroupBox(i18n.t("config.train_params"))
        train_layout = QFormLayout()

        self.train_num_envs_spin = QSpinBox()
        self.train_num_envs_spin.setRange(1, 100000)
        self.train_num_envs_spin.setValue(4096)
        train_layout.addRow(i18n.t("config.num_envs"), self.train_num_envs_spin)

        self.train_max_iter_spin = QSpinBox()
        self.train_max_iter_spin.setRange(1, 100000000)
        self.train_max_iter_spin.setValue(1000)
        train_layout.addRow(i18n.t("config.max_iterations"), self.train_max_iter_spin)

        self.train_headless_check = QCheckBox(i18n.t("config.headless_mode"))
        self.train_headless_check.setChecked(True)
        train_layout.addRow("", self.train_headless_check)

        # Live stream选项：空(禁用)、1(公网IP)、2(局域网IP)
        self.train_livestream_combo = QComboBox()
        self.train_livestream_combo.addItem(i18n.t("combo.disabled"), 0)
        self.train_livestream_combo.addItem(i18n.t("combo.public_ip"), 1)
        self.train_livestream_combo.addItem(i18n.t("combo.local_ip"), 2)
        self.train_livestream_combo.currentIndexChanged.connect(self._on_train_livestream_changed)
        train_layout.addRow(i18n.t("config.livestream"), self.train_livestream_combo)

        # Enable cameras选项：空(禁用)、1(启用)
        self.train_enable_cameras_combo = QComboBox()
        self.train_enable_cameras_combo.addItem(i18n.t("combo.disabled"), 0)
        self.train_enable_cameras_combo.addItem(i18n.t("combo.enabled"), 1)
        train_layout.addRow(i18n.t("config.enable_cameras"), self.train_enable_cameras_combo)

        train_group.setLayout(train_layout)
        layout.addWidget(train_group)

        # ========== Play模式参数组 ==========
        play_group = QGroupBox(i18n.t("config.play_params"))
        play_layout = QFormLayout()

        self.play_num_envs_spin = QSpinBox()
        self.play_num_envs_spin.setRange(1, 100000)
        self.play_num_envs_spin.setValue(1)
        play_layout.addRow(i18n.t("config.num_envs"), self.play_num_envs_spin)

        self.play_headless_check = QCheckBox(i18n.t("config.headless_mode"))
        self.play_headless_check.setChecked(False)
        play_layout.addRow("", self.play_headless_check)

        # Live stream选项：空(禁用)、1(公网IP)、2(局域网IP)
        self.play_livestream_combo = QComboBox()
        self.play_livestream_combo.addItem(i18n.t("combo.disabled"), 0)
        self.play_livestream_combo.addItem(i18n.t("combo.public_ip"), 1)
        self.play_livestream_combo.addItem(i18n.t("combo.local_ip"), 2)
        self.play_livestream_combo.currentIndexChanged.connect(self._on_play_livestream_changed)
        play_layout.addRow(i18n.t("config.livestream"), self.play_livestream_combo)

        # Enable cameras选项：空(禁用)、1(启用)
        self.play_enable_cameras_combo = QComboBox()
        self.play_enable_cameras_combo.addItem(i18n.t("combo.disabled"), 0)
        self.play_enable_cameras_combo.addItem(i18n.t("combo.enabled"), 1)
        play_layout.addRow(i18n.t("config.enable_cameras"), self.play_enable_cameras_combo)

        play_group.setLayout(play_layout)
        layout.addWidget(play_group)

        # ========== 通用参数组 ==========
        common_group = QGroupBox(i18n.t("config.common_params"))
        common_layout = QFormLayout()

        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 100000)
        self.seed_spin.setValue(-1)
        common_layout.addRow(i18n.t("config.seed"), self.seed_spin)

        self.device_combo = QComboBox()
        self.device_combo.addItems(["cuda:0", "cuda:1", "cuda:2", "cuda:3", "cpu"])
        common_layout.addRow(i18n.t("config.device"), self.device_combo)

        common_group.setLayout(common_layout)
        layout.addWidget(common_group)

        # ========== tmux设置组 ==========
        tmux_group = QGroupBox(i18n.t("config.tmux_settings"))
        tmux_layout = QFormLayout()

        self.tmux_prefix_edit = QLineEdit()
        self.tmux_prefix_edit.setText("isaaclab")
        tmux_layout.addRow(i18n.t("config.session_prefix"), self.tmux_prefix_edit)

        tmux_group.setLayout(tmux_layout)
        layout.addWidget(tmux_group)

        # ========== 日志设置组 ==========
        log_group = QGroupBox(i18n.t("config.log_settings"))
        log_layout = QFormLayout()

        # 自动保存日志
        self.auto_save_log_check = QCheckBox(i18n.t("config.auto_save_log"))
        log_layout.addRow("", self.auto_save_log_check)

        # 日志保存路径
        log_path_layout = QHBoxLayout()
        self.log_path_edit = QLineEdit()
        self.log_path_edit.setPlaceholderText(i18n.t("config.log_save_path_placeholder"))
        log_path_layout.addWidget(self.log_path_edit)

        self.browse_log_btn = QPushButton(i18n.t("label.browse"))
        self.browse_log_btn.clicked.connect(self._browse_log_path)
        log_path_layout.addWidget(self.browse_log_btn)

        log_layout.addRow(i18n.t("config.log_save_path"), log_path_layout)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # ========== 按钮 ==========
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._save_and_close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_env_type_changed(self, button):
        """环境类型切换"""
        idx = self.env_type_group.checkedId()
        self.env_stack.setCurrentIndex(idx)

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

    def _scan_conda_envs(self):
        """扫描conda环境"""
        self.env_combo.clear()
        self.env_combo.addItem("-- " + i18n.t("config.select_env").replace(":", "") + " --", None)

        envs = scan_conda_environments()

        if not envs:
            QMessageBox.information(
                self, i18n.t("msg.tip"),
                i18n.t("config.conda_not_found")
            )
            return

        for env_name, env_path in envs:
            self.env_combo.addItem(f"[Conda] {env_name}", ("conda", env_name, env_path))

        QMessageBox.information(self, i18n.t("config.scan_complete"), i18n.t("config.found_envs", len(envs), "conda"))

    def _scan_venv_envs(self):
        """扫描虚拟环境"""
        self.env_combo.clear()
        self.env_combo.addItem("-- " + i18n.t("config.select_env").replace(":", "") + " --", None)

        envs = scan_venv_environments()

        if not envs:
            QMessageBox.information(
                self, i18n.t("msg.tip"),
                i18n.t("config.venv_not_found")
            )
            return

        for env_name, env_path in envs:
            self.env_combo.addItem(f"[venv] {env_name}", ("venv", env_name, env_path))

        QMessageBox.information(self, i18n.t("config.scan_complete"), i18n.t("config.found_envs", len(envs), "venv"))

    def _on_env_selected(self, index):
        """环境选择变化"""
        data = self.env_combo.currentData()
        if data:
            env_type, env_name, env_path = data
            self.env_path_label.setText(env_path)
            self.env_path_label.setStyleSheet("color: #2196F3; font-size: 11px;")

    def _browse_manual_path(self):
        """浏览手动输入路径"""
        path = QFileDialog.getExistingDirectory(
            self, i18n.t("config.select_env_path")
        )
        if path:
            self.manual_env_path_edit.setText(path)

    def _browse_log_path(self):
        """浏览日志保存路径"""
        path = QFileDialog.getExistingDirectory(
            self, i18n.t("config.select_log_path")
        )
        if path:
            self.log_path_edit.setText(path)

    def _on_isaaclab_mode_changed(self, button):
        """Isaac Lab路径模式切换"""
        idx = self.isaaclab_mode_group.checkedId()
        if idx == 0:  # 自动检测
            self.isaaclab_manual_widget.setVisible(False)
        else:  # 手动输入
            self.isaaclab_manual_widget.setVisible(True)

    def _browse_isaaclab_path(self):
        """浏览Isaac Lab路径"""
        path = QFileDialog.getExistingDirectory(
            self, i18n.t("config.select_isaaclab_path")
        )
        if path:
            self.isaaclab_path_edit.setText(path)

    def _load_config(self):
        """加载配置到界面"""
        config = self.config_manager.config

        # 环境设置
        env_type = config.env_type or "scan"
        if env_type == "scan":
            self.scan_env_radio.setChecked(True)
            # 如果有保存的环境，添加到下拉框并选中
            if config.conda_env_name and config.conda_env_path:
                self.env_combo.clear()
                self.env_combo.addItem(f"[Conda] {config.conda_env_name}", ("conda", config.conda_env_name, config.conda_env_path))
                self.env_path_label.setText(config.conda_env_path)
                self.env_path_label.setStyleSheet("color: #2196F3; font-size: 11px;")
            elif config.python_path:
                self.env_combo.clear()
                self.env_combo.addItem(f"[venv] {os.path.basename(config.python_path)}", ("venv", os.path.basename(config.python_path), config.python_path))
                self.env_path_label.setText(config.python_path)
                self.env_path_label.setStyleSheet("color: #2196F3; font-size: 11px;")
        elif env_type == "local":
            self.local_env_radio.setChecked(True)
        else:
            self.manual_env_radio.setChecked(True)
        self.env_stack.setCurrentIndex(0 if env_type == "scan" else (1 if env_type == "local" else 2))

        # 手动输入的环境信息
        if config.conda_env_name or config.python_path:
            self.manual_env_name_edit.setText(config.conda_env_name or "")
            self.manual_env_path_edit.setText(config.conda_env_path or config.python_path or "")
            if config.python_path and not config.conda_env_name:
                self.manual_env_type_combo.setCurrentIndex(1)

        # 参数设置
        params = config.default_params or {}

        # Train参数
        train_params = params.get("train", {})
        self.train_num_envs_spin.setValue(train_params.get("num_envs", 4096))
        self.train_max_iter_spin.setValue(train_params.get("max_iterations", 1000))
        self.train_headless_check.setChecked(train_params.get("headless", True))
        # livestream: 0=禁用, 1=公网IP, 2=局域网IP
        livestream_value = int(train_params.get("livestream", 0) or 0)
        self.train_livestream_combo.setCurrentIndex(livestream_value)
        # enable_cameras: 0=禁用, 1=启用
        enable_cameras_value = int(train_params.get("enable_cameras", 0) or 0)
        self.train_enable_cameras_combo.setCurrentIndex(enable_cameras_value)
        # 触发一次回调以更新headless状态
        self._on_train_livestream_changed(self.train_livestream_combo.currentIndex())

        # Play参数
        play_params = params.get("play", {})
        self.play_num_envs_spin.setValue(play_params.get("num_envs", 1))
        self.play_headless_check.setChecked(play_params.get("headless", False))
        livestream_value = int(play_params.get("livestream", 0) or 0)
        self.play_livestream_combo.setCurrentIndex(livestream_value)
        enable_cameras_value = int(play_params.get("enable_cameras", 0) or 0)
        self.play_enable_cameras_combo.setCurrentIndex(enable_cameras_value)
        # 触发一次回调以更新headless状态
        self._on_play_livestream_changed(self.play_livestream_combo.currentIndex())

        # 通用参数
        self.seed_spin.setValue(params.get("seed", -1))
        device = params.get("device", "cuda:0")
        index = self.device_combo.findText(device)
        if index >= 0:
            self.device_combo.setCurrentIndex(index)

        self.tmux_prefix_edit.setText(config.tmux_session_prefix)

        # 日志设置
        self.auto_save_log_check.setChecked(config.auto_save_log)
        self.log_path_edit.setText(config.log_save_path or "")

        # Isaac Lab 路径设置
        isaaclab_mode = config.isaaclab_path_mode or "auto"
        if isaaclab_mode == "auto":
            self.isaaclab_auto_radio.setChecked(True)
            self.isaaclab_manual_widget.setVisible(False)
        else:
            self.isaaclab_manual_radio.setChecked(True)
            self.isaaclab_manual_widget.setVisible(True)
        self.isaaclab_path_edit.setText(config.isaaclab_path_manual or "")

    def _save_and_close(self):
        """保存配置并关闭"""
        config = self.config_manager.config

        # 环境设置
        env_type_idx = self.env_type_group.checkedId()
        if env_type_idx == 0:  # 扫描环境
            config.env_type = "scan"
            data = self.env_combo.currentData()
            if data:
                env_type, env_name, env_path = data
                config.conda_env_name = env_name
                config.conda_env_path = env_path
                config.python_path = ""
            else:
                config.conda_env_name = ""
                config.conda_env_path = ""
                config.python_path = ""
        elif env_type_idx == 1:  # 本机环境
            config.env_type = "local"
            config.conda_env_name = ""
            config.conda_env_path = ""
            config.python_path = ""
        else:  # 手动输入
            config.env_type = "manual"
            if self.manual_env_type_combo.currentIndex() == 0:  # Conda
                config.conda_env_name = self.manual_env_name_edit.text()
                config.conda_env_path = self.manual_env_path_edit.text()
                config.python_path = ""
            else:  # venv
                config.conda_env_name = ""
                config.conda_env_path = ""
                config.python_path = self.manual_env_path_edit.text()

        # 参数设置
        config.default_params = {
            "train": {
                "num_envs": self.train_num_envs_spin.value(),
                "max_iterations": self.train_max_iter_spin.value(),
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
            "device": self.device_combo.currentText(),
        }

        # tmux设置
        config.tmux_session_prefix = self.tmux_prefix_edit.text()

        # 日志设置
        config.auto_save_log = self.auto_save_log_check.isChecked()
        config.log_save_path = self.log_path_edit.text()

        # Isaac Lab 路径设置
        isaaclab_mode_idx = self.isaaclab_mode_group.checkedId()
        if isaaclab_mode_idx == 0:  # 自动检测
            config.isaaclab_path_mode = "auto"
            config.isaaclab_path_manual = ""
        else:  # 手动输入
            config.isaaclab_path_mode = "manual"
            config.isaaclab_path_manual = self.isaaclab_path_edit.text()

        self.config_manager.save()
        self.accept()