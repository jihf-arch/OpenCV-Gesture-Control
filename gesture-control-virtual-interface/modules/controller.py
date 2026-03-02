# modules/controller.py
"""
控制命令执行模块
论文对应：系统实现 - 虚拟界面控制应用模块

功能：
  - 将手势映射为键盘/媒体按键事件
  - 返回结构化执行结果
  - 完整日志记录
  - 全局启停开关
"""

import time
import pyautogui
from config import GESTURE_MAP
from utils.logger import get_logger

logger = get_logger()

pyautogui.FAILSAFE = False  # 防止移动鼠标到角落退出
pyautogui.PAUSE = 0.05      # 按键间隔最小化，减少延迟


class CommandResult:
    """命令执行结果（结构化）"""

    def __init__(self, gesture, mode, key, success, error=None):
        self.gesture = gesture
        self.mode = mode
        self.key = key
        self.success = success
        self.error = error
        self.timestamp = time.time()

    def __repr__(self):
        status = "OK" if self.success else f"FAIL({self.error})"
        return f"[{status}] {self.gesture} → {self.key} ({self.mode})"


class Controller:
    """命令控制器（支持启停、日志、统计）"""

    def __init__(self):
        self.enabled = True         # 全局启停开关
        self.total_executed = 0
        self.total_failed = 0
        self.execution_log = []     # 最近执行记录（最多保留 50 条）
        self._max_log_size = 50

        logger.info("Controller initialized")

    def execute(self, gesture, mode):
        """
        执行控制命令

        Args:
            gesture: 手势名称 (str)
            mode: 当前模式 ("ppt" / "music")

        Returns:
            CommandResult: 执行结果对象
        """
        # 开关检查
        if not self.enabled:
            result = CommandResult(gesture, mode, None, False, "controller disabled")
            logger.debug(f"Controller disabled, skipping: {gesture}")
            return result

        # 映射检查
        if gesture not in GESTURE_MAP:
            result = CommandResult(gesture, mode, None, False, "unknown gesture")
            logger.warning(f"Unknown gesture: {gesture}")
            return result

        if mode not in GESTURE_MAP[gesture]:
            result = CommandResult(gesture, mode, None, False, "invalid mode")
            logger.warning(f"Invalid mode '{mode}' for gesture '{gesture}'")
            return result

        key = GESTURE_MAP[gesture][mode]

        # 执行按键
        try:
            pyautogui.press(key)
            result = CommandResult(gesture, mode, key, True)
            self.total_executed += 1
            logger.info(f"Executed: {gesture} → {key} (mode={mode}) [#{self.total_executed}]")

        except Exception as e:
            result = CommandResult(gesture, mode, key, False, str(e))
            self.total_failed += 1
            logger.error(f"Execution failed: {gesture} → {key} | Error: {e}")

        # 记录日志
        self.execution_log.append(result)
        if len(self.execution_log) > self._max_log_size:
            self.execution_log.pop(0)

        return result

    def toggle(self):
        """切换启停状态"""
        self.enabled = not self.enabled
        status = "ENABLED" if self.enabled else "DISABLED"
        logger.info(f"Controller {status}")
        return self.enabled

    def get_stats(self):
        """获取执行统计信息"""
        return {
            "enabled": self.enabled,
            "total_executed": self.total_executed,
            "total_failed": self.total_failed,
            "success_rate": (
                self.total_executed / (self.total_executed + self.total_failed)
                if (self.total_executed + self.total_failed) > 0
                else 1.0
            ),
            "last_action": str(self.execution_log[-1]) if self.execution_log else None,
        }

    def get_recent_log(self, n=5):
        """获取最近 n 条执行记录"""
        return self.execution_log[-n:]


# 保持向后兼容的函数接口（供旧代码调用）
_default_controller = Controller()


def execute_command(gesture, mode):
    """向后兼容函数：委托给默认 Controller 实例"""
    result = _default_controller.execute(gesture, mode)
    return result.success


def get_controller():
    """获取默认控制器实例"""
    return _default_controller