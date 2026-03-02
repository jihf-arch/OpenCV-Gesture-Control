# tests/test_fsm.py
"""
状态机 (FSM) 单元测试
论文对应：系统测试 - 逻辑控制模块测试
"""

import sys
import os
import time
import unittest

# 确保可以导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.fsm import GestureFSM, FSMState
from config import DEBOUNCE_FRAMES, CONFIDENCE_THRESHOLD, TRANSITION_SUPPRESS_FRAMES

class TestGestureFSM(unittest.TestCase):
    def setUp(self):
        self.fsm = GestureFSM()

    def test_initial_state(self):
        """测试初始状态"""
        self.assertEqual(self.fsm.state, FSMState.IDLE)
        self.assertEqual(self.fsm.current_mode, "ppt")

    def test_low_confidence_filtering(self):
        """测试低置信度过滤"""
        action = self.fsm.update("fist", CONFIDENCE_THRESHOLD - 0.1)
        self.assertIsNone(action)
        self.assertEqual(self.fsm.state, FSMState.IDLE)
        self.assertEqual(self.fsm.total_suppressed, 1)

    def test_debounce_and_trigger(self):
        """测试防抖确认和触发"""
        action = None
        # 连续输入高质量手势
        for _ in range(DEBOUNCE_FRAMES):
            action = self.fsm.update("palm", 0.9)
            
        self.assertEqual(action, "palm")
        self.assertEqual(self.fsm.state, FSMState.COOLDOWN)
        self.assertEqual(self.fsm.total_triggers, 1)

    def test_transition_suppression(self):
        """测试过渡态抑制（手势抖动）"""
        # 手指在伸缩过程中，手势在拳头和张开之间切换
        self.fsm.update("fist", 0.9)
        self.fsm.update("palm", 0.9)
        
        # 此时应该被过渡态抑制
        action = self.fsm.update("fist", 0.9)
        self.assertIsNone(action)
        self.assertTrue(self.fsm.transition_count > 0)
        
    def test_cooldown_mechanism(self):
        """测试冷却机制"""
        # 1. 触发一次
        for _ in range(DEBOUNCE_FRAMES):
            self.fsm.update("index", 0.9)
            
        self.assertEqual(self.fsm.state, FSMState.COOLDOWN)
        
        # 2. 冷却期间输入相同手势，不应该触发
        action = self.fsm.update("index", 0.9)
        self.assertIsNone(action)
        self.assertEqual(self.fsm.state, FSMState.COOLDOWN)
        
        # 3. 模拟时间流逝（冷却结束）
        self.fsm.last_trigger_time = 0
        self.fsm.update("index", 0.9)
        self.assertEqual(self.fsm.state, FSMState.DETECTING)

    def test_mode_switch(self):
        """测试长按 V 字切换模式"""
        from config import MODE_SWITCH_HOLD_FRAMES
        
        action = None
        for _ in range(MODE_SWITCH_HOLD_FRAMES):
            action = self.fsm.update("victory", 0.9)
            
        self.assertEqual(action, "mode_switch")
        self.assertEqual(self.fsm.current_mode, "music")
        self.assertEqual(self.fsm.state, FSMState.COOLDOWN)

if __name__ == "__main__":
    unittest.main()
