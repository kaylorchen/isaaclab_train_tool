#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据模型定义"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Mode(Enum):
    """运行模式"""
    TRAIN = "train"
    PLAY = "play"


@dataclass
class ScriptInfo:
    """脚本信息"""
    name: str
    path: str
    script_type: Mode

    def __repr__(self):
        return f"ScriptInfo({self.name}, {self.script_type.value})"


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    entry_point: str
    config_path: Optional[str] = None

    @property
    def display_name(self) -> str:
        """显示名称，去掉Template-前缀"""
        if self.task_id.startswith("Template-"):
            return self.task_id[9:]  # 去掉"Template-"
        return self.task_id

    @property
    def is_play_task(self) -> bool:
        """是否是播放任务"""
        return "-Play" in self.task_id

    @property
    def train_task_id(self) -> str:
        """获取对应的训练任务ID"""
        if self.is_play_task:
            return self.task_id.replace("-Play", "")
        return self.task_id

    @property
    def play_task_id(self) -> str:
        """获取对应的播放任务ID"""
        if not self.is_play_task:
            # 在版本号前插入-Play
            parts = self.task_id.rsplit("-v", 1)
            if len(parts) == 2:
                return f"{parts[0]}-Play-v{parts[1]}"
            return self.task_id + "-Play"
        return self.task_id

    def __repr__(self):
        return f"TaskInfo({self.task_id})"


@dataclass
class SessionInfo:
    """tmux会话信息"""
    session_name: str
    workspace_path: str
    task_id: str
    mode: Mode
    script_path: str
    status: str = "running"  # running, stopped
    pid: Optional[int] = None

    def __repr__(self):
        return f"SessionInfo({self.session_name}, {self.status})"


@dataclass
class WorkspaceInfo:
    """Workspace信息"""
    path: str
    name: str = ""
    train_scripts: list = field(default_factory=list)
    play_scripts: list = field(default_factory=list)
    tasks: list = field(default_factory=list)

    @property
    def has_scripts(self) -> bool:
        return len(self.train_scripts) > 0 or len(self.play_scripts) > 0

    @property
    def script_dirs(self) -> list:
        """获取所有脚本目录"""
        dirs = set()
        for script in self.train_scripts + self.play_scripts:
            # 获取脚本所在目录
            import os
            dirs.add(os.path.dirname(script.path))
        return list(dirs)