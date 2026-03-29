#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tmux会话管理器"""

import subprocess
import re
from typing import Optional, List
from models import SessionInfo, Mode


class TmuxManager:
    """tmux会话管理器"""

    def __init__(self):
        self._check_tmux_available()

    def _check_tmux_available(self) -> None:
        """检查tmux是否可用"""
        try:
            result = subprocess.run(
                ["tmux", "-V"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError("tmux is not available")
        except FileNotFoundError:
            raise RuntimeError("tmux is not installed")

    def create_session(self, session_name: str, width: int = 192, attach: bool = False) -> bool:
        """创建新的tmux会话

        Args:
            session_name: 会话名称
            width: 窗口宽度（字符数）
            attach: 是否立即附加到会话

        Returns:
            是否成功创建
        """
        # 检查会话是否已存在
        if self.session_exists(session_name):
            return False

        try:
            # 创建 session
            cmd = ["tmux", "new-session", "-d", "-s", session_name, "-x", str(width)]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return False

            # 设置全局 history-limit（影响后续创建的session）
            subprocess.run(
                ["tmux", "set-option", "-g", "history-limit", "50000"],
                capture_output=True, text=True
            )

            # 设置当前窗口的 history-limit（确保当前session生效）
            subprocess.run(
                ["tmux", "set-option", "-t", f"{session_name}:0", "history-limit", "50000"],
                capture_output=True, text=True
            )

            return True
        except Exception as e:
            print(f"Error creating tmux session: {e}")
            return False

    def resize_window(self, session_name: str, width: int) -> bool:
        """调整tmux窗口宽度

        Args:
            session_name: 会话名称
            width: 新的窗口宽度（字符数）

        Returns:
            是否成功
        """
        if not self.session_exists(session_name):
            return False

        cmd = ["tmux", "resize-window", "-t", session_name, "-x", str(width)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"Error resizing tmux window: {e}")
            return False

    def send_command(self, session_name: str, command: str, enter: bool = True) -> bool:
        """向tmux会话发送命令

        Args:
            session_name: 会话名称
            command: 要执行的命令
            enter: 是否自动发送回车

        Returns:
            是否成功发送
        """
        if not self.session_exists(session_name):
            return False

        # 发送命令
        cmd = ["tmux", "send-keys", "-t", session_name, command]
        if enter:
            cmd.append("Enter")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"Error sending command to tmux: {e}")
            return False

    def send_keys(self, session_name: str, keys: str) -> bool:
        """向tmux会话发送按键

        Args:
            session_name: 会话名称
            keys: 按键序列

        Returns:
            是否成功发送
        """
        if not self.session_exists(session_name):
            return False

        cmd = ["tmux", "send-keys", "-t", session_name, keys]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"Error sending keys to tmux: {e}")
            return False

    def kill_session(self, session_name: str) -> bool:
        """终止tmux会话

        Args:
            session_name: 会话名称

        Returns:
            是否成功终止
        """
        if not self.session_exists(session_name):
            return True

        cmd = ["tmux", "kill-session", "-t", session_name]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"Error killing tmux session: {e}")
            return False

    def session_exists(self, session_name: str) -> bool:
        """检查会话是否存在

        Args:
            session_name: 会话名称

        Returns:
            是否存在
        """
        cmd = ["tmux", "has-session", "-t", session_name]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def has_active_process(self, session_name: str) -> bool:
        """检查会话中是否有活跃进程

        Args:
            session_name: 会话名称

        Returns:
            是否有活跃进程
        """
        if not self.session_exists(session_name):
            return False

        # 检查 pane 当前命令
        cmd_cmd = ["tmux", "display-message", "-t", session_name, "-p", "#{pane_current_command}"]
        try:
            result = subprocess.run(cmd_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                current_cmd = result.stdout.strip().lower()
                # 如果当前命令是 shell，说明没有运行程序
                shell_cmds = ["bash", "zsh", "sh", "fish", "dash", "-bash", "-zsh"]
                if current_cmd in shell_cmds:
                    return False
                # 如果是 python 或其他程序，说明有进程在运行
                return True
        except Exception:
            pass

        # 备用方法：检查子进程
        cmd = ["tmux", "list-panes", "-t", session_name, "-F", "#{pane_pid}"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return True  # 无法确定，假设有进程

            pane_pid = result.stdout.strip()
            if not pane_pid:
                return True  # 无法确定，假设有进程

            # 检查该PID下是否有子进程
            try:
                ps_cmd = ["ps", "--ppid", pane_pid, "-o", "pid=", "--no-headers"]
                ps_result = subprocess.run(ps_cmd, capture_output=True, text=True)
                children = ps_result.stdout.strip()
                return bool(children)
            except Exception:
                return True  # 无法确定，假设有进程

        except Exception:
            return True  # 无法确定，假设有进程

    def capture_output(self, session_name: str, lines: int = -1) -> str:
        """捕获tmux会话的输出

        Args:
            session_name: 会话名称
            lines: 捕获的行数，-1 表示捕获全部历史

        Returns:
            会话输出内容（包含ANSI颜色代码）
        """
        if not self.session_exists(session_name):
            return ""

        # 添加 -e 标志来保留ANSI转义序列
        # -S - 表示从历史开始处捕获（全部历史）
        if lines == -1:
            cmd = ["tmux", "capture-pane", "-t", session_name, "-p", "-e", "-S", "-"]
        else:
            cmd = ["tmux", "capture-pane", "-t", session_name, "-p", "-e", "-S", f"-{lines}"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout
        except Exception as e:
            print(f"Error capturing tmux output: {e}")
            return ""

    def list_sessions(self, prefix: Optional[str] = None) -> List[str]:
        """列出所有tmux会话

        Args:
            prefix: 会话名称前缀过滤

        Returns:
            会话名称列表
        """
        cmd = ["tmux", "list-sessions", "-F", "#{session_name}"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return []

            sessions = result.stdout.strip().split("\n")
            sessions = [s for s in sessions if s]

            if prefix:
                sessions = [s for s in sessions if s.startswith(prefix)]

            return sessions
        except Exception:
            return []

    def get_session_info(self, session_name: str) -> Optional[SessionInfo]:
        """获取会话信息

        Args:
            session_name: 会话名称

        Returns:
            SessionInfo对象，如果会话不存在则返回None
        """
        if not self.session_exists(session_name):
            return None

        # 获取会话的窗口列表
        cmd = ["tmux", "list-windows", "-t", session_name, "-F",
               "#{window_index}:#{window_name}:#{window_active}"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return None

            return SessionInfo(
                session_name=session_name,
                workspace_path="",
                task_id="",
                mode=Mode.TRAIN,
                script_path="",
                status="running"
            )
        except Exception:
            return None

    def set_working_directory(self, session_name: str, directory: str) -> bool:
        """设置会话的工作目录

        Args:
            session_name: 会话名称
            directory: 工作目录路径

        Returns:
            是否成功
        """
        return self.send_command(session_name, f"cd {directory}")

    def run_command_in_session(
        self,
        session_name: str,
        command: str,
        working_dir: Optional[str] = None,
        env_activation: Optional[str] = None
    ) -> bool:
        """在tmux会话中运行命令

        Args:
            session_name: 会话名称
            command: 要执行的命令
            working_dir: 工作目录
            env_activation: 环境激活命令

        Returns:
            是否成功
        """
        # 检查/创建会话
        if not self.session_exists(session_name):
            if not self.create_session(session_name):
                return False

        # 设置工作目录
        if working_dir:
            if not self.send_command(session_name, f"cd {working_dir}"):
                return False

        # 激活环境
        if env_activation:
            if not self.send_command(session_name, env_activation):
                return False

        # 执行命令
        return self.send_command(session_name, command)

    def send_interrupt(self, session_name: str) -> bool:
        """发送中断信号(Ctrl+C)

        Args:
            session_name: 会话名称

        Returns:
            是否成功
        """
        return self.send_keys(session_name, "C-c")

    def attach_to_session(self, session_name: str) -> None:
        """附加到tmux会话（需要在终端中运行）

        Args:
            session_name: 会话名称
        """
        os.system(f"tmux attach -t {session_name}")


# 单例实例
_tmux_manager: Optional[TmuxManager] = None


def get_tmux_manager() -> TmuxManager:
    """获取tmux管理器单例"""
    global _tmux_manager
    if _tmux_manager is None:
        _tmux_manager = TmuxManager()
    return _tmux_manager