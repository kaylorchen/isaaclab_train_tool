#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workspace扫描器 - 扫描Isaac Lab项目结构"""

import os
import re
from typing import List, Optional
from pathlib import Path

from models import ScriptInfo, TaskInfo, WorkspaceInfo, Mode


class WorkspaceScanner:
    """Workspace扫描器"""

    # 常见的脚本名称模式
    TRAIN_SCRIPT_NAMES = ["train.py"]
    PLAY_SCRIPT_NAMES = ["play.py"]

    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self._scripts_dir = None

    def scan(self) -> WorkspaceInfo:
        """扫描workspace，返回完整信息"""
        info = WorkspaceInfo(
            path=self.workspace_path,
            name=os.path.basename(self.workspace_path)
        )

        # 检查目录是否存在
        if not os.path.isdir(self.workspace_path):
            return info

        # 扫描脚本
        info.train_scripts = self._find_scripts(Mode.TRAIN)
        info.play_scripts = self._find_scripts(Mode.PLAY)

        # 扫描任务
        info.tasks = self._find_tasks()

        return info

    def _find_scripts(self, script_type: Mode) -> List[ScriptInfo]:
        """查找指定类型的脚本"""
        scripts = []
        script_names = self.TRAIN_SCRIPT_NAMES if script_type == Mode.TRAIN else self.PLAY_SCRIPT_NAMES
        scripts_dir = os.path.join(self.workspace_path, "scripts")

        if not os.path.isdir(scripts_dir):
            return scripts

        # 递归搜索scripts目录
        for root, dirs, files in os.walk(scripts_dir):
            for file in files:
                if file in script_names:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.workspace_path)

                    # 计算脚本目录名（相对于scripts的路径）
                    script_dir = os.path.dirname(os.path.relpath(full_path, scripts_dir))
                    if script_dir == ".":
                        script_dir = "scripts"
                    else:
                        script_dir = f"scripts/{script_dir}"

                    scripts.append(ScriptInfo(
                        name=file,
                        path=full_path,
                        script_type=script_type
                    ))

        return scripts

    def _find_tasks(self) -> List[TaskInfo]:
        """查找所有注册的任务

        通过解析source目录下的__init__.py文件中的gym.register调用
        """
        tasks = []
        source_dir = os.path.join(self.workspace_path, "source")

        if not os.path.isdir(source_dir):
            return tasks

        # 遍历source目录下的所有项目
        for project_name in os.listdir(source_dir):
            project_dir = os.path.join(source_dir, project_name)
            if not os.path.isdir(project_dir):
                continue

            # 查找项目内的Python包
            for item in os.listdir(project_dir):
                pkg_dir = os.path.join(project_dir, item)
                if os.path.isdir(pkg_dir):
                    # 递归搜索所有__init__.py文件
                    tasks.extend(self._scan_for_gym_registers(pkg_dir))

        return tasks

    def _scan_for_gym_registers(self, directory: str) -> List[TaskInfo]:
        """扫描目录下的__init__.py文件，解析gym.register调用"""
        tasks = []

        for root, dirs, files in os.walk(directory):
            # 检查__init__.py
            init_file = os.path.join(root, "__init__.py")
            if os.path.isfile(init_file):
                tasks.extend(self._parse_gym_registers(init_file))

        return tasks

    def _parse_gym_registers(self, file_path: str) -> List[TaskInfo]:
        """解析文件中的gym.register调用"""
        tasks = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            return tasks

        # 匹配gym.register调用的模式
        # gym.register(id="Template-Spiderbot-v0", ...)
        pattern = r'gym\.register\s*\(\s*id\s*=\s*["\']([^"\']+)["\']'

        for match in re.finditer(pattern, content):
            task_id = match.group(1)
            tasks.append(TaskInfo(
                task_id=task_id,
                entry_point="",  # 可以后续解析entry_point
                config_path=file_path
            ))

        return tasks

    def get_script_by_dir(self, script_dir: str) -> tuple:
        """根据脚本目录获取训练和播放脚本

        Args:
            script_dir: 脚本目录，如 "scripts/rsl_rl"

        Returns:
            (train_script, play_script) 元组
        """
        full_dir = os.path.join(self.workspace_path, script_dir)

        train_script = None
        play_script = None

        if os.path.isdir(full_dir):
            for file in os.listdir(full_dir):
                if file in self.TRAIN_SCRIPT_NAMES:
                    train_script = ScriptInfo(
                        name=file,
                        path=os.path.join(full_dir, file),
                        script_type=Mode.TRAIN
                    )
                elif file in self.PLAY_SCRIPT_NAMES:
                    play_script = ScriptInfo(
                        name=file,
                        path=os.path.join(full_dir, file),
                        script_type=Mode.PLAY
                    )

        return train_script, play_script

    def find_script_dirs(self) -> List[str]:
        """查找所有包含训练/播放脚本的目录"""
        dirs = set()
        scripts_dir = os.path.join(self.workspace_path, "scripts")

        if not os.path.isdir(scripts_dir):
            return []

        for root, dirs_list, files in os.walk(scripts_dir):
            has_train = any(f in self.TRAIN_SCRIPT_NAMES for f in files)
            has_play = any(f in self.PLAY_SCRIPT_NAMES for f in files)

            if has_train or has_play:
                rel_path = os.path.relpath(root, self.workspace_path)
                dirs.add(rel_path)

        return sorted(list(dirs))

    @staticmethod
    def is_valid_workspace(path: str) -> bool:
        """检查是否是有效的Isaac Lab workspace"""
        if not os.path.isdir(path):
            return False

        # 检查是否有scripts目录
        scripts_dir = os.path.join(path, "scripts")
        if not os.path.isdir(scripts_dir):
            return False

        # 检查是否有source目录（包含任务定义）
        source_dir = os.path.join(path, "source")
        if not os.path.isdir(source_dir):
            return False

        return True