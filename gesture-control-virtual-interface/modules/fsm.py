# modules/fsm.py
"""
手势有限状态机（Finite State Machine）
论文对应：系统实现 - 手势到控制命令的映射模块

状态转移图：
  [Idle] ──检测到手部──→ [Detecting]
  [Detecting] ──手势连续N帧一致──→ [Confirming]
  [Detecting] ──手部丢失──→ [Idle]
  [Confirming] ──置信度达标──→ [Executing]
  [Confirming] ──手势不一致──→ [Detecting]
  [Executing] ──执行命令──→ [Cooldown]
  [Cooldown] ──冷却结束──→ [Idle]

防抖原理：
  - 时序逻辑防抖：连续 N 帧识别结果一致才确认
  - 过渡态抑制：检测到手势快速变化时，直接丢弃中间帧
  - 冷却机制：触发命令后锁定，避免重复触发
"""

import time
from enum import Enum
from config import (
    DEBOUNCE_FRAMES, COOLDOWN_SECONDS, MODE_SWITCH_HOLD_FRAMES,
    CONFIDENCE_THRESHOLD, TRANSITION_SUPPRESS_FRAMES, MODES
)
from utils.logger import get_logger

logger = get_logger()


class FSMState(Enum):
    """FSM 状态枚举"""
    IDLE = "idle"               # 空闲：无手部检测
    DETECTING = "detecting"     # 检测中：手部出现，正在识别手势
    CONFIRMING = "confirming"   # 确认中：手势连续出现，等待防抖确认
    EXECUTING = "executing"     # 执行中：手势确认，触发动作
    COOLDOWN = "cooldown"       # 冷却中：指令已发，等待冷却


class GestureFSM:
    """
    基于显式状态的手势有限状态机

    特性：
      - 显式状态转移（5 种状态）
      - 置信度过滤
      - 时序防抖 + 过渡态抑制
      - 冷却机制
      - 完整日志记录
      - 模式切换（victory 长按）
    """

    def __init__(self):
        self.state = FSMState.IDLE
        self.current_mode = "ppt"

        # 防抖相关
        self.history = []                      # 手势历史队列
        self.confidence_history = []           # 置信度历史
        self.stable_gesture = None             # 当前稳定手势
        self.stable_count = 0                  # 稳定手势连续计数

        # 冷却相关
        self.last_trigger_time = 0
        self.last_action = None

        # 模式切换
        self.victory_hold_count = 0

        # 过渡态抑制
        self.transition_count = 0              # 手势变化计数

        # 统计信息
        self.total_triggers = 0
        self.total_suppressed = 0

        logger.info("FSM initialized: state=IDLE, mode=ppt")

    def _change_state(self, new_state, reason=""):
        """状态转换（带日志记录）"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            logger.info(f"FSM: {old_state.value} → {new_state.value} | {reason}")

    def _is_in_cooldown(self):
        """检查是否仍在冷却期"""
        return time.time() - self.last_trigger_time < COOLDOWN_SECONDS

    def _check_transition_suppression(self, gesture):
        """
        过渡态抑制：检测手势是否在快速变化
        如果最近几帧手势不一致，说明用户在切换手势，应该抑制
        """
        if len(self.history) < 2:
            return False

        recent = self.history[-TRANSITION_SUPPRESS_FRAMES:]
        unique_gestures = set(recent)

        # 如果最近几帧中出现了 2 种以上不同手势，判定为过渡态
        if len(unique_gestures) >= 2:
            self.transition_count += 1
            return True

        self.transition_count = 0
        return False

    def _switch_mode(self):
        """模式切换逻辑"""
        mode_idx = MODES.index(self.current_mode)
        self.current_mode = MODES[(mode_idx + 1) % len(MODES)]
        self.victory_hold_count = 0
        logger.info(f"FSM: Mode switched to {self.current_mode.upper()}")
        return "mode_switch"

    def update(self, gesture, confidence=0.0):
        """
        FSM 主更新函数 — 每帧调用

        Args:
            gesture: 识别到的手势名称 (str 或 None)
            confidence: 置信度 (float, 0-1)

        Returns:
            action: 触发的动作 (str) 或 None
                    - "mode_switch": 模式切换信号
                    - "fist" / "palm" / "index" / "victory": 手势动作
                    - None: 无动作
        """

        # ===================== 冷却状态检查 =====================
        if self.state == FSMState.COOLDOWN:
            if self._is_in_cooldown():
                return None
            else:
                self._change_state(FSMState.IDLE, "cooldown expired")

        # ===================== 无手势 → 回到 IDLE =====================
        if gesture is None:
            if self.state != FSMState.IDLE:
                self._change_state(FSMState.IDLE, "no gesture detected")
            self.history.clear()
            self.confidence_history.clear()
            self.stable_gesture = None
            self.stable_count = 0
            self.victory_hold_count = 0
            self.transition_count = 0
            return None

        # ===================== 置信度过滤 =====================
        if confidence < CONFIDENCE_THRESHOLD:
            # 低置信度手势不进入状态机
            self.total_suppressed += 1
            return None

        # ===================== 更新历史队列 =====================
        self.history.append(gesture)
        self.confidence_history.append(confidence)
        # 限制队列长度
        max_len = max(DEBOUNCE_FRAMES, TRANSITION_SUPPRESS_FRAMES) + 2
        if len(self.history) > max_len:
            self.history.pop(0)
            self.confidence_history.pop(0)

        # ===================== 过渡态抑制 =====================
        if self._check_transition_suppression(gesture):
            if self.state == FSMState.CONFIRMING:
                self._change_state(FSMState.DETECTING, "transition suppressed")
                self.stable_count = 0
            self.total_suppressed += 1
            return None

        # ===================== IDLE → DETECTING =====================
        if self.state == FSMState.IDLE:
            self._change_state(FSMState.DETECTING, f"gesture={gesture}")

        # ===================== Victory 长按模式切换 =====================
        if gesture == "victory":
            self.victory_hold_count += 1
            if self.victory_hold_count >= MODE_SWITCH_HOLD_FRAMES:
                result = self._switch_mode()
                self._change_state(FSMState.COOLDOWN, "mode switch triggered")
                self.last_trigger_time = time.time()
                self.history.clear()
                self.confidence_history.clear()
                return result
        else:
            self.victory_hold_count = 0

        # ===================== DETECTING → CONFIRMING =====================
        if gesture == self.stable_gesture:
            self.stable_count += 1
        else:
            self.stable_gesture = gesture
            self.stable_count = 1
            if self.state == FSMState.CONFIRMING:
                self._change_state(FSMState.DETECTING, f"gesture changed to {gesture}")

        if self.stable_count >= DEBOUNCE_FRAMES and self.state == FSMState.DETECTING:
            self._change_state(FSMState.CONFIRMING, f"stable {gesture} x{self.stable_count}")

        # ===================== CONFIRMING → EXECUTING =====================
        if self.state == FSMState.CONFIRMING:
            # 检查连续帧的平均置信度
            recent_confs = self.confidence_history[-DEBOUNCE_FRAMES:]
            avg_conf = sum(recent_confs) / len(recent_confs) if recent_confs else 0

            if avg_conf >= CONFIDENCE_THRESHOLD:
                # 触发动作
                self._change_state(FSMState.EXECUTING, f"avg_conf={avg_conf:.2f}")
                action = self.stable_gesture
                self.total_triggers += 1

                # 立刻转入冷却
                self.last_trigger_time = time.time()
                self.last_action = action
                self._change_state(FSMState.COOLDOWN, f"action={action}")
                self.stable_count = 0

                logger.info(
                    f"FSM TRIGGER: gesture={action} mode={self.current_mode} "
                    f"conf={avg_conf:.2f} total_triggers={self.total_triggers}"
                )
                return action

        return None

    def get_state_info(self):
        """
        获取 FSM 当前状态信息（供 UI 显示和调试）
        Returns:
            dict: FSM 状态摘要
        """
        return {
            "state": self.state.value,
            "mode": self.current_mode,
            "stable_gesture": self.stable_gesture,
            "stable_count": self.stable_count,
            "debounce_progress": min(1.0, self.stable_count / DEBOUNCE_FRAMES),
            "cooldown_remaining": max(0, COOLDOWN_SECONDS - (time.time() - self.last_trigger_time)),
            "victory_hold": self.victory_hold_count,
            "victory_progress": min(1.0, self.victory_hold_count / MODE_SWITCH_HOLD_FRAMES),
            "is_cooldown": self._is_in_cooldown() and self.state == FSMState.COOLDOWN,
            "total_triggers": self.total_triggers,
            "total_suppressed": self.total_suppressed,
            "last_action": self.last_action,
        }

    def reset(self):
        """重置 FSM 到初始状态"""
        self.state = FSMState.IDLE
        self.history.clear()
        self.confidence_history.clear()
        self.stable_gesture = None
        self.stable_count = 0
        self.victory_hold_count = 0
        self.transition_count = 0
        self.last_trigger_time = 0
        self.last_action = None
        logger.info("FSM reset to IDLE")