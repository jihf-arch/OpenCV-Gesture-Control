# tests/test_controller.py
"""
控制器 (Controller) 单元测试
论文对应：系统测试 - 逻辑控制模块测试
"""

import sys
import os
import unittest
from unittest.mock import patch

# 确保可以导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.controller import Controller
from config import GESTURE_MAP

class TestController(unittest.TestCase):
    def setUp(self):
        self.controller = Controller()

    @patch('pyautogui.press')
    def test_execute_valid_gesture(self, mock_press):
        """测试执行有效手势"""
        result = self.controller.execute("fist", "ppt")
        
        self.assertTrue(result.success)
        self.assertEqual(result.key, GESTURE_MAP["fist"]["ppt"])
        mock_press.assert_called_once_with(GESTURE_MAP["fist"]["ppt"])
        self.assertEqual(self.controller.total_executed, 1)

    @patch('pyautogui.press')
    def test_execute_invalid_gesture(self, mock_press):
        """测试执行无效手势"""
        result = self.controller.execute("unknown", "ppt")
        
        self.assertFalse(result.success)
        self.assertEqual(result.error, "unknown gesture")
        mock_press.assert_not_called()
        self.assertEqual(self.controller.total_executed, 0)

    @patch('pyautogui.press')
    def test_toggle_controller(self, mock_press):
        """测试控制器启停开关"""
        # 关闭控制器
        self.controller.toggle()
        self.assertFalse(self.controller.enabled)
        
        result = self.controller.execute("palm", "ppt")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "controller disabled")
        mock_press.assert_not_called()

    @patch('pyautogui.press')
    def test_pyautogui_error(self, mock_press):
        """测试 GUI 操作异常情况"""
        mock_press.side_effect = Exception("GUI Error")
        
        result = self.controller.execute("index", "ppt")
        
        self.assertFalse(result.success)
        self.assertEqual(self.controller.total_failed, 1)
        self.assertIn("GUI Error", result.error)

if __name__ == "__main__":
    unittest.main()
