# modules/gesture_recognizer.py
"""
手势识别模块 — 对外统一接口
委托给 GestureClassifier 完成实际分类

保持 recognize_gesture(landmarks) → (gesture, confidence) 的接口不变，
确保 main.py 和 fsm.py 的调用代码无需修改。
"""

from modules.gesture_classifier import GestureClassifier
from config import RECOGNITION_CONFIG
from utils.logger import get_logger

logger = get_logger()

# 模块级别的分类器实例（单例，避免重复创建）
_classifier = GestureClassifier(RECOGNITION_CONFIG)


def recognize_gesture(landmarks):
    """
    手势识别统一入口
    Args:
        landmarks: MediaPipe HandLandmarks 对象
    Returns:
        gesture: 手势名称 (str) 或 None
        confidence: 置信度 (float, 0-1)
    """
    if not landmarks:
        return None, 0.0

    gesture, confidence, details = _classifier.classify(landmarks)

    if gesture == "unknown":
        return None, 0.0

    logger.debug(
        f"Gesture: {gesture} | Confidence: {confidence:.2f} | "
        f"Fingers: {details['finger_states']} | "
        f"Facing: {details['facing_camera']}"
    )

    return gesture, confidence


def get_classifier():
    """获取分类器实例（供外部访问详细特征信息）"""
    return _classifier