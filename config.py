#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置管理模块"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class AppConfig:
    """应用配置"""
    env_type: str = "scan"  # scan, local, manual
    conda_env_path: str = ""
    conda_env_name: str = ""
    python_path: str = ""
    default_params: Dict[str, Any] = None
    recent_workspaces: List[str] = None
    workspace_history: List[str] = None  # Workspace 历史记录（最多20条）
    tmux_session_prefix: str = "isaaclab"
    last_workspace: str = ""
    # 当前会话配置
    last_task: str = ""
    last_script_dir: str = ""
    last_mode: str = "train"
    last_extra_params: str = ""
    # 语言设置
    language: str = "zh"  # zh or en
    # 日志保存路径
    log_save_path: str = ""
    # 自动保存日志
    auto_save_log: bool = False
    # Isaac Lab 路径设置
    isaaclab_path_mode: str = "auto"  # auto 或 manual
    isaaclab_path_manual: str = ""  # 手动指定的 Isaac Lab 路径

    def __post_init__(self):
        if self.default_params is None:
            self.default_params = {
                "train": {
                    "num_envs": 4096,
                    "max_iterations": 1000,
                    "headless": True,
                    "livestream": 0,
                    "enable_cameras": 0,
                },
                "play": {
                    "num_envs": 1,
                    "headless": False,
                    "livestream": 0,
                    "enable_cameras": 0,
                },
                "seed": -1,
                "device": "cuda:0",
            }
        if self.recent_workspaces is None:
            self.recent_workspaces = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        return cls(
            env_type=data.get("env_type", "scan"),
            conda_env_path=data.get("conda_env_path", ""),
            conda_env_name=data.get("conda_env_name", ""),
            python_path=data.get("python_path", ""),
            default_params=data.get("default_params"),
            recent_workspaces=data.get("recent_workspaces", []),
            workspace_history=data.get("workspace_history", []),
            tmux_session_prefix=data.get("tmux_session_prefix", "isaaclab"),
            last_workspace=data.get("last_workspace", ""),
            last_task=data.get("last_task", ""),
            last_script_dir=data.get("last_script_dir", ""),
            last_mode=data.get("last_mode", "train"),
            last_extra_params=data.get("last_extra_params", ""),
            language=data.get("language", "zh"),
            log_save_path=data.get("log_save_path", ""),
            auto_save_log=data.get("auto_save_log", False),
            # Isaac Lab 路径设置
            isaaclab_path_mode=data.get("isaaclab_path_mode", "auto"),
            isaaclab_path_manual=data.get("isaaclab_path_manual", ""),
        )


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            # 默认使用用户主目录下的配置
            config_dir = os.path.join(Path.home(), ".config", "isaaclab_train_tool")

        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "config.json")
        self._config: Optional[AppConfig] = None

        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)

    @property
    def config(self) -> AppConfig:
        """获取配置"""
        if self._config is None:
            self._config = self.load()
        return self._config

    def load(self) -> AppConfig:
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return AppConfig.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                # 配置文件损坏，返回默认配置
                return AppConfig()
        return AppConfig()

    def save(self) -> None:
        """保存配置"""
        if self._config is None:
            return

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self._config.to_dict(), f, indent=4, ensure_ascii=False)

    def update(self, **kwargs) -> None:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.save()

    def add_recent_workspace(self, workspace_path: str) -> None:
        """添加最近使用的workspace"""
        recent = self.config.recent_workspaces

        # 如果已存在，移到最前面
        if workspace_path in recent:
            recent.remove(workspace_path)

        recent.insert(0, workspace_path)

        # 最多保留10个
        self.config.recent_workspaces = recent[:10]
        self.config.last_workspace = workspace_path
        self.save()

    def get_activation_command(self) -> str:
        """获取环境激活命令"""
        env_type = self.config.env_type or "scan"

        if env_type == "local":
            # 本机环境，不需要激活
            return ""

        if self.config.conda_env_path and self.config.conda_env_name:
            # conda环境
            conda_root = os.path.dirname(os.path.dirname(self.config.conda_env_path))
            return f"source {conda_root}/etc/profile.d/conda.sh && conda activate {self.config.conda_env_name}"
        elif self.config.python_path:
            # 虚拟环境
            return f"source {self.config.python_path}/bin/activate"
        else:
            return ""

    def get_python_command(self) -> str:
        """获取Python执行命令"""
        env_type = self.config.env_type or "scan"

        if env_type == "local":
            return "python3"

        if self.config.conda_env_path and self.config.conda_env_name:
            return "python"
        elif self.config.python_path:
            return f"{self.config.python_path}/bin/python"
        else:
            return "python"

    def get_python_executable(self) -> str:
        """获取完整的Python可执行文件路径

        Returns:
            str: Python完整路径，如果无法确定则返回空字符串
        """
        env_type = self.config.env_type or "scan"

        if env_type == "local":
            return "/usr/bin/python3"

        if self.config.conda_env_path and self.config.conda_env_name:
            # conda环境：conda_env_path/bin/python
            return os.path.join(self.config.conda_env_path, "bin", "python")
        elif self.config.python_path:
            # 虚拟环境
            return os.path.join(self.config.python_path, "bin", "python")
        else:
            return ""