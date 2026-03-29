#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Internationalization module for multi-language support"""

from typing import Dict, Any

# Language codes
LANG_ZH = "zh"
LANG_EN = "en"

# Current language (default to Chinese)
_current_lang = LANG_ZH

# Translation dictionaries
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    LANG_ZH: {
        # Menu
        "menu.file": "文件",
        "menu.edit": "编辑",
        "menu.help": "帮助",
        "menu.open_workspace": "打开Workspace目录",
        "menu.select_workspace": "选择Workspace...",
        "menu.new_project": "生成新工程...",
        "menu.exit": "退出",
        "menu.settings": "设置...",
        "menu.about": "关于",
        "menu.language": "语言",

        # Main Window - Groups
        "group.workspace": "Workspace",
        "group.script_task": "脚本和任务",
        "group.parameters": "参数设置",
        "group.command_preview": "命令预览",
        "group.current_session": "当前会话",

        # Main Window - Labels
        "label.browse": "浏览...",
        "label.scan": "扫描",
        "label.script_dir": "脚本目录:",
        "label.mode": "模式:",
        "label.task": "任务:",
        "label.task_type": "类型:",
        "label.num_envs": "环境数量:",
        "label.max_iter": "最大迭代:",
        "label.headless": "无头模式:",
        "label.livestream": "实时流:",
        "label.enable_cameras": "启用相机:",
        "label.resume": "继续训练 (resume):",
        "label.load_run": "加载运行 (load_run):",
        "label.checkpoint": "检查点 (checkpoint):",
        "label.seed": "随机种子:",
        "label.extra_params": "额外参数:",
        "label.session_name": "会话名称:",
        "label.status": "状态:",
        "label.none": "无",
        "label.type": "类型:",

        # Main Window - Buttons
        "btn.settings": "设置",
        "btn.save_params": "保存参数",
        "btn.run": "运行",
        "btn.stop": "停止",
        "btn.attach": "附加到终端",
        "btn.refresh_runs": "刷新运行记录",
        "btn.force_stop": "强制停止",
        "btn.install_source": "安装源码",
        "btn.uninstall_source": "卸载源码",

        # Source install status
        "source.installed": "源码已安装",
        "source.not_installed": "源码未安装",
        "source.checking": "检查中...",
        "source.no_source_dir": "未找到 source 目录",
        "source.install_confirm": "确定要安装源码吗？\n将执行: pip install -e source/extension",
        "source.uninstall_confirm": "确定要卸载源码吗？\n将执行: pip uninstall",
        "source.installing": "正在安装源码...",
        "source.uninstalling": "正在卸载源码...",
        "source.install_success": "源码安装成功",
        "source.uninstall_success": "源码卸载成功",
        "source.install_failed": "源码安装失败: {}",
        "source.uninstall_failed": "源码卸载失败: {}",
        "source.installed_other": "已安装其他版本",
        "source.installed_non_editable": "已安装（非开发模式）",

        # Main Window - Combobox items
        "combo.disabled": "禁用",
        "combo.public_ip": "公网IP (1)",
        "combo.local_ip": "局域网IP (2)",
        "combo.enabled": "启用 (1)",
        "combo.no_checkpoint": "无检查点",
        "combo.no_runs": "未找到运行记录",
        "combo.no_logs": "logs目录不存在",
        "combo.select_run": "-- 选择运行记录 --",

        # Main Window - Placeholders
        "placeholder.workspace": "选择Isaac Lab项目目录...",
        "placeholder.extra_params": "其他命令行参数，如: --logger wandb",
        "placeholder.command": "运行命令将显示在这里...",
        "placeholder.log_content": "日志内容将显示在这里...",

        # Main Window - Status
        "status.ready": "就绪",
        "status.scanning": "正在扫描...",
        "status.scan_complete": "扫描完成: {} 个任务",
        "status.scan_failed": "扫描失败",
        "status.params_saved": "参数已保存",
        "status.session_started": "已启动会话: {}",
        "status.interrupt_sent": "已发送中断信号",
        "status.session_ended": "会话已结束",
        "status.session_force_stopped": "会话已强制终止",
        "status.session_stopped_preserved": "训练已停止，Session 保留",
        "status.log_saved": "日志已保存到: {}",
        "status.log_auto_saved": "日志已自动保存到: {}",
        "status.log_save_failed": "自动保存日志失败: {}",
        "status.log_dir_failed": "创建日志目录失败: {}",
        "status.force_stopped": "已强制终止会话",

        # Main Window - Messages
        "msg.no_workspace": "请先选择有效的Workspace目录",
        "msg.select_dir": "选择Isaac Lab项目目录",
        "msg.invalid_dir": "请选择有效的目录",
        "msg.no_scripts": "未在 {}/scripts 目录下找到训练或播放脚本",
        "msg.no_python_env": "未配置Python环境，将使用系统默认Python。\n是否继续？",
        "msg.stop_training": "确定要停止当前训练吗？\n这会终止tmux会话。",
        "msg.attach_terminal": "将在 {} 中附加到会话: {}\n\n按 Ctrl+B 然后按 D 可以分离会话",
        "msg.closing": "有正在运行的训练会话。\n关闭窗口不会停止训练，会话将继续在后台运行。\n\n确定要关闭吗？",
        "msg.about": "Isaac Lab Train Tool\n\n用于管理Isaac Lab项目训练和播放的图形界面工具\n\n版本: 1.0.0",
        "msg.create_session_failed": "无法创建tmux会话",
        "msg.start_failed": "启动失败: {}",
        "msg.language_changed": "语言已更改，重启应用以完全生效。",
        "msg.confirm": "确认",
        "msg.warning": "警告",
        "msg.error": "错误",
        "msg.tip": "提示",
        "msg.log_empty": "无日志内容",
        "msg.log_save_title": "保存日志",
        "msg.latest_model": "最新: {}",
        "msg.no_model": "无",

        # Isaac Lab detection
        "isaaclab.not_configured": "Isaac Lab: 未配置Python环境（请在设置中配置）",
        "isaaclab.not_detected": "Isaac Lab: 未检测到（请确认Python环境正确）",
        "isaaclab.detected": "Isaac Lab: {}",

        # New Project
        "new_project.title": "生成新工程",
        "new_project.select_path": "选择新工程路径",
        "new_project.path_label": "工程路径:",
        "new_project.create": "生成",
        "new_project.creating": "正在生成新工程...",
        "new_project.success": "新工程已创建: {}",
        "new_project.failed": "生成新工程失败",
        "new_project.no_isaaclab": "未检测到 Isaac Lab，无法生成新工程",
        "new_project.terminal_title": "Isaac Lab - 生成新工程",
        "new_project.path_copied": "路径已复制到剪切板",

        # Config Dialog
        "config.title": "设置",
        "config.python_env": "Python环境",
        "config.env_type": "环境类型:",
        "config.scan_env": "扫描环境",
        "config.local_env": "本机环境",
        "config.manual_input": "手动输入",
        "config.scan_conda": "扫描Conda",
        "config.scan_venv": "扫描venv",
        "config.select_env": "选择环境:",
        "config.path": "路径:",
        "config.not_selected": "未选择",
        "config.use_default": "将使用系统默认Python环境",
        "config.conda_env": "Conda环境",
        "config.venv": "虚拟环境(venv)",
        "config.env_name": "环境名称:",
        "config.env_path": "环境路径:",
        "config.env_name_placeholder": "环境名称，如 isaaclab",
        "config.env_path_placeholder": "环境路径",
        "config.train_params": "Train模式参数",
        "config.play_params": "Play模式参数",
        "config.common_params": "通用参数",
        "config.num_envs": "环境数量 (num_envs):",
        "config.max_iterations": "最大迭代次数:",
        "config.headless_mode": "无头模式 (headless)",
        "config.livestream": "实时流 (livestream):",
        "config.enable_cameras": "启用相机 (enable_cameras):",
        "config.seed": "随机种子 (-1为随机):",
        "config.device": "设备:",
        "config.tmux_settings": "tmux设置",
        "config.session_prefix": "会话名称前缀:",
        "config.conda_not_found": "未找到conda环境。\n请确保conda已安装并配置正确。",
        "config.venv_not_found": "未找到虚拟环境。\n您可以尝试手动输入。",
        "config.scan_complete": "扫描完成",
        "config.found_envs": "找到 {} 个{}环境",
        "config.log_settings": "日志设置",
        "config.auto_save_log": "自动保存日志",
        "config.log_save_path": "日志保存路径:",
        "config.log_save_path_placeholder": "默认保存到当前目录",
        "config.select_env_path": "选择环境路径",
        "config.select_log_path": "选择日志保存路径",

        # Log Panel
        "log.title": "日志面板",
        "log.refresh": "刷新",
        "log.save": "保存",
        "log.clear": "清除",
        "log.auto_scroll": "自动滚动",
        "log.no_session": "无活动会话",
        "log.saved": "日志已保存到: {}",
        "log.save_title": "保存日志",
        "log.no_content": "无日志内容",
        "log.save_path": "日志保存路径:",
        "log.save_path_placeholder": "默认保存到当前目录",
        "log.auto_save": "自动保存日志",

        # Tooltips
        "tooltip.save_params": "保存当前参数为默认值",
        "tooltip.stop": "终止当前训练会话",
    },
    LANG_EN: {
        # Menu
        "menu.file": "File",
        "menu.edit": "Edit",
        "menu.help": "Help",
        "menu.open_workspace": "Open Workspace Directory",
        "menu.select_workspace": "Select Workspace...",
        "menu.new_project": "Create New Project...",
        "menu.exit": "Exit",
        "menu.settings": "Settings...",
        "menu.about": "About",
        "menu.language": "Language",

        # Main Window - Groups
        "group.workspace": "Workspace",
        "group.script_task": "Script and Task",
        "group.parameters": "Parameters",
        "group.command_preview": "Command Preview",
        "group.current_session": "Current Session",

        # Main Window - Labels
        "label.browse": "Browse...",
        "label.scan": "Scan",
        "label.script_dir": "Script Dir:",
        "label.mode": "Mode:",
        "label.task": "Task:",
        "label.task_type": "Type:",
        "label.num_envs": "Num Envs:",
        "label.max_iter": "Max Iterations:",
        "label.headless": "Headless:",
        "label.livestream": "Livestream:",
        "label.enable_cameras": "Enable Cameras:",
        "label.resume": "Resume:",
        "label.load_run": "Load Run:",
        "label.checkpoint": "Checkpoint:",
        "label.seed": "Seed:",
        "label.extra_params": "Extra Args:",
        "label.session_name": "Session Name:",
        "label.status": "Status:",
        "label.none": "None",
        "label.type": "Type:",

        # Main Window - Buttons
        "btn.settings": "Settings",
        "btn.save_params": "Save Params",
        "btn.run": "Run",
        "btn.stop": "Stop",
        "btn.attach": "Attach Terminal",
        "btn.refresh_runs": "Refresh Runs",
        "btn.force_stop": "Force Stop",
        "btn.install_source": "Install Source",
        "btn.uninstall_source": "Uninstall Source",

        # Source install status
        "source.installed": "Source installed",
        "source.not_installed": "Source not installed",
        "source.checking": "Checking...",
        "source.no_source_dir": "source directory not found",
        "source.install_confirm": "Install source code?\nCommand: pip install -e source/extension",
        "source.uninstall_confirm": "Uninstall source code?\nCommand: pip uninstall",
        "source.installing": "Installing source...",
        "source.uninstalling": "Uninstalling source...",
        "source.install_success": "Source installed successfully",
        "source.uninstall_success": "Source uninstalled successfully",
        "source.install_failed": "Source installation failed: {}",
        "source.uninstall_failed": "Source uninstallation failed: {}",
        "source.installed_other": "Installed other version",
        "source.installed_non_editable": "Installed (non-editable)",

        # Main Window - Combobox items
        "combo.disabled": "Disabled",
        "combo.public_ip": "Public IP (1)",
        "combo.local_ip": "Local IP (2)",
        "combo.enabled": "Enabled (1)",
        "combo.no_checkpoint": "No checkpoint",
        "combo.no_runs": "No runs found",
        "combo.no_logs": "logs directory not found",
        "combo.select_run": "-- Select Run --",

        # Main Window - Placeholders
        "placeholder.workspace": "Select Isaac Lab project directory...",
        "placeholder.extra_params": "Additional CLI args, e.g.: --logger wandb",
        "placeholder.command": "Command will be displayed here...",
        "placeholder.log_content": "Log content will be displayed here...",

        # Main Window - Status
        "status.ready": "Ready",
        "status.scanning": "Scanning...",
        "status.scan_complete": "Scan complete: {} tasks",
        "status.scan_failed": "Scan failed",
        "status.params_saved": "Parameters saved",
        "status.session_started": "Session started: {}",
        "status.interrupt_sent": "Interrupt signal sent",
        "status.session_ended": "Session ended",
        "status.session_force_stopped": "Session forcefully terminated",
        "status.session_stopped_preserved": "Training stopped, session preserved",
        "status.log_saved": "Log saved to: {}",
        "status.log_auto_saved": "Log auto-saved to: {}",
        "status.log_save_failed": "Failed to auto-save log: {}",
        "status.log_dir_failed": "Failed to create log directory: {}",
        "status.force_stopped": "Session forcefully terminated",

        # Main Window - Messages
        "msg.no_workspace": "Please select a valid Workspace directory first",
        "msg.select_dir": "Select Isaac Lab Project Directory",
        "msg.invalid_dir": "Please select a valid directory",
        "msg.no_scripts": "No train or play scripts found in {}/scripts directory",
        "msg.no_python_env": "No Python environment configured, will use system default Python.\nContinue?",
        "msg.stop_training": "Stop current training?\nThis will terminate the tmux session.",
        "msg.attach_terminal": "Will attach to session in {}: {}\n\nPress Ctrl+B then D to detach from session",
        "msg.closing": "A training session is running.\nClosing the window will not stop the training, the session will continue in the background.\n\nAre you sure you want to close?",
        "msg.about": "Isaac Lab Train Tool\n\nA GUI tool for managing Isaac Lab training and play sessions\n\nVersion: 1.0.0",
        "msg.create_session_failed": "Failed to create tmux session",
        "msg.start_failed": "Failed to start: {}",
        "msg.language_changed": "Language changed. Restart the application for full effect.",
        "msg.confirm": "Confirm",
        "msg.warning": "Warning",
        "msg.error": "Error",
        "msg.tip": "Tip",
        "msg.log_empty": "No log content",
        "msg.log_save_title": "Save Log",
        "msg.latest_model": "latest: {}",
        "msg.no_model": "None",

        # Isaac Lab detection
        "isaaclab.not_configured": "Isaac Lab: Python environment not configured (please configure in Settings)",
        "isaaclab.not_detected": "Isaac Lab: Not detected (please verify Python environment)",
        "isaaclab.detected": "Isaac Lab: {}",

        # New Project
        "new_project.title": "Create New Project",
        "new_project.select_path": "Select New Project Path",
        "new_project.path_label": "Project Path:",
        "new_project.create": "Create",
        "new_project.creating": "Creating new project...",
        "new_project.success": "New project created: {}",
        "new_project.failed": "Failed to create new project",
        "new_project.no_isaaclab": "Isaac Lab not detected, cannot create new project",
        "new_project.terminal_title": "Isaac Lab - Create New Project",
        "new_project.path_copied": "Path copied to clipboard",

        # Config Dialog
        "config.title": "Settings",
        "config.python_env": "Python Environment",
        "config.env_type": "Environment Type:",
        "config.scan_env": "Scan Environment",
        "config.local_env": "Local Environment",
        "config.manual_input": "Manual Input",
        "config.scan_conda": "Scan Conda",
        "config.scan_venv": "Scan venv",
        "config.select_env": "Select Environment:",
        "config.path": "Path:",
        "config.not_selected": "Not selected",
        "config.use_default": "Will use system default Python environment",
        "config.conda_env": "Conda Environment",
        "config.venv": "Virtual Environment (venv)",
        "config.env_name": "Environment Name:",
        "config.env_path": "Environment Path:",
        "config.env_name_placeholder": "Environment name, e.g. isaaclab",
        "config.env_path_placeholder": "Environment path",
        "config.train_params": "Train Mode Parameters",
        "config.play_params": "Play Mode Parameters",
        "config.common_params": "Common Parameters",
        "config.num_envs": "Num Envs:",
        "config.max_iterations": "Max Iterations:",
        "config.headless_mode": "Headless Mode",
        "config.livestream": "Livestream:",
        "config.enable_cameras": "Enable Cameras:",
        "config.seed": "Seed (-1 for random):",
        "config.device": "Device:",
        "config.tmux_settings": "tmux Settings",
        "config.session_prefix": "Session Name Prefix:",
        "config.conda_not_found": "No conda environments found.\nPlease ensure conda is installed and configured correctly.",
        "config.venv_not_found": "No virtual environments found.\nYou can try manual input.",
        "config.scan_complete": "Scan complete",
        "config.found_envs": "Found {} {} environments",
        "config.log_settings": "Log Settings",
        "config.auto_save_log": "Auto Save Log",
        "config.log_save_path": "Log Save Path:",
        "config.log_save_path_placeholder": "Default to current directory",
        "config.select_env_path": "Select Environment Path",
        "config.select_log_path": "Select Log Save Path",

        # Log Panel
        "log.title": "Log Panel",
        "log.refresh": "Refresh",
        "log.save": "Save",
        "log.clear": "Clear",
        "log.auto_scroll": "Auto Scroll",
        "log.no_session": "No active session",
        "log.saved": "Log saved to: {}",
        "log.save_title": "Save Log",
        "log.no_content": "No log content",
        "log.save_path": "Log Save Path:",
        "log.save_path_placeholder": "Default to current directory",
        "log.auto_save": "Auto Save Log",

        # Tooltips
        "tooltip.save_params": "Save current parameters as default",
        "tooltip.stop": "Terminate current training session",
    }
}


def set_language(lang: str) -> None:
    """Set the current language"""
    global _current_lang
    if lang in TRANSLATIONS:
        _current_lang = lang


def get_language() -> str:
    """Get the current language"""
    return _current_lang


def t(key: str, *args, **kwargs) -> str:
    """Translate a key to the current language

    Args:
        key: The translation key
        *args: Positional arguments for string formatting
        **kwargs: Keyword arguments for string formatting

    Returns:
        The translated string
    """
    translations = TRANSLATIONS.get(_current_lang, TRANSLATIONS[LANG_ZH])
    text = translations.get(key, key)

    if args or kwargs:
        try:
            return text.format(*args, **kwargs)
        except (IndexError, KeyError):
            return text

    return text