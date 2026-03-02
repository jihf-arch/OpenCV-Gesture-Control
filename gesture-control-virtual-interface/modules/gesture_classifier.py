# modules/gesture_classifier.py
"""
手势分类器模块（查表 + 阈值结构）
论文对应：关键技术 - 手势特征提取与分类

核心改进（相比原版 gesture_recognizer.py）：
  1. 角度特征替代像素距离 → 尺度不变性
  2. 归一化比率特征 → 适应不同手型大小和距离
  3. 3D 骨架约束 → 手掌朝向检测，抑制侧面误识别
  4. 查表式分类结构 → 便于扩展新手势
  5. 综合置信度计算 → 更可靠的识别评估
"""

import math
import numpy as np
from utils.logger import get_logger

logger = get_logger()

# ======================== MediaPipe 关键点索引定义 ========================
# 参考：https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker
#
#   手指          MCP(根部)   PIP(中间)   DIP    TIP(指尖)
#   拇指            1          2         3       4
#   食指            5          6         7       8
#   中指            9         10        11      12
#   无名指         13         14        15      16
#   小指           17         18        19      20
#   手腕 = 0

# 每根手指的关键点索引: (MCP, PIP, DIP, TIP)
FINGER_JOINTS = {
    "thumb":  (1, 2, 3, 4),
    "index":  (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring":   (13, 14, 15, 16),
    "pinky":  (17, 18, 19, 20),
}

# 手势规则表：每种手势期望哪些手指伸直/弯曲
# fingers_up: [thumb, index, middle, ring, pinky], 1=伸直, 0=弯曲, -1=不关心
GESTURE_RULES = {
    "fist": {
        "fingers_up": [-1, 0, 0, 0, 0],  # 四指弯曲，拇指不关心
        "description": "握拳",
    },
    "palm": {
        "fingers_up": [1, 1, 1, 1, 1],    # 五指全部伸直
        "description": "手掌张开",
    },
    "index": {
        "fingers_up": [-1, 1, 0, 0, 0],   # 只有食指伸直
        "description": "食指伸出",
    },
    "victory": {
        "fingers_up": [-1, 1, 1, 0, 0],   # 食指+中指伸直
        "v_angle_range": (15, 150),         # V 字夹角范围（度）
        "description": "V字手势",
    },
}


class GestureClassifier:
    """基于角度特征和归一化比率的手势分类器"""

    def __init__(self, config=None):
        """
        Args:
            config: 配置字典，可包含：
                - finger_straight_angle: 手指伸直的角度阈值 (默认 160°)
                - finger_bent_angle: 手指弯曲的角度阈值 (默认 100°)
                - palm_z_threshold: 手掌朝向 z 差值阈值 (默认 0.1)
                - min_confidence: 最低有效置信度 (默认 0.5)
        """
        cfg = config or {}
        self.straight_angle = cfg.get("finger_straight_angle", 160)
        self.bent_angle = cfg.get("finger_bent_angle", 100)
        self.palm_z_threshold = cfg.get("palm_z_threshold", 0.1)
        self.min_confidence = cfg.get("min_confidence", 0.5)

    # ======================== 几何计算工具 ========================

    @staticmethod
    def _vector_angle(v1, v2):
        """计算两个向量之间的夹角（度数）"""
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
        mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)

        if mag1 == 0 or mag2 == 0:
            return 0

        cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
        return math.degrees(math.acos(cos_angle))

    @staticmethod
    def _three_point_angle(p1, p2, p3):
        """
        计算三点夹角（以 p2 为顶点）
        即 p1→p2 与 p3→p2 两个向量的夹角
        """
        v1 = (p1[0] - p2[0], p1[1] - p2[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        return GestureClassifier._vector_angle(v1, v2)

    @staticmethod
    def _distance(p1, p2):
        """两点间欧氏距离"""
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    # ======================== 特征提取 ========================

    def _extract_landmarks_2d(self, landmarks):
        """提取 21 个关键点的 2D 坐标列表"""
        return [(lm.x, lm.y) for lm in landmarks.landmark]

    def _extract_landmarks_3d(self, landmarks):
        """提取 21 个关键点的 3D 坐标列表"""
        return [(lm.x, lm.y, lm.z) for lm in landmarks.landmark]

    def _finger_bend_angle(self, lm, finger_name):
        """
        计算手指弯曲角度（MCP → PIP → TIP 三点夹角）
        角度越大 = 越伸直（~180° = 完全伸直）
        角度越小 = 越弯曲（~60°  = 完全弯曲）
        """
        mcp, pip, dip, tip = FINGER_JOINTS[finger_name]
        # 使用 MCP-PIP-TIP 计算弯曲程度
        return self._three_point_angle(lm[mcp], lm[pip], lm[tip])

    def _thumb_is_up(self, lm):
        """
        拇指伸直判定（特殊处理，因为拇指运动平面不同）
        使用拇指指尖(4)与拇指IP关节(3)和掌根(2)的角度
        同时考虑拇指指尖相对于食指根部的横向位置
        """
        # 方法1：角度判定
        angle = self._three_point_angle(lm[1], lm[2], lm[4])

        # 方法2：横向距离判定
        # 判断是左手还是右手（通过手腕和中指根部的相对位置粗略推断）
        # 拇指外展时，tip(4) 应远离食指根(5)
        thumb_tip = lm[4]
        index_mcp = lm[5]
        wrist = lm[0]

        # 拇指尖到食指根的距离 vs 手腕到食指根的距离（归一化）
        dist_thumb_to_index = self._distance(thumb_tip, index_mcp)
        dist_wrist_to_index = self._distance(wrist, index_mcp)

        if dist_wrist_to_index == 0:
            return False, 0.5

        ratio = dist_thumb_to_index / dist_wrist_to_index
        is_up = angle > 140 or ratio > 0.7

        confidence = min(1.0, max(0.0, (angle - 100) / 80))  # 100°→0, 180°→1
        return is_up, confidence

    def _get_finger_states(self, lm):
        """
        获取五根手指的伸直/弯曲状态及角度
        Returns:
            states: [thumb, index, middle, ring, pinky]  1=伸直, 0=弯曲
            angles: 对应的角度列表
            confidences: 每根手指判定的置信度
        """
        states = []
        angles = []
        confidences = []

        # 拇指特殊处理
        thumb_up, thumb_conf = self._thumb_is_up(lm)
        states.append(1 if thumb_up else 0)
        angles.append(0)  # 拇指角度用另一种方法
        confidences.append(thumb_conf)

        # 四指角度判定
        for name in ["index", "middle", "ring", "pinky"]:
            angle = self._finger_bend_angle(lm, name)
            is_straight = angle > self.straight_angle
            is_bent = angle < self.bent_angle

            if is_straight:
                states.append(1)
                # 越接近 180° 置信度越高
                conf = min(1.0, (angle - self.straight_angle) / 20 + 0.7)
            elif is_bent:
                states.append(0)
                conf = min(1.0, (self.bent_angle - angle) / 40 + 0.7)
            else:
                # 中间态：倾向于判定为弯曲，但低置信度
                states.append(0)
                conf = 0.4

            angles.append(angle)
            confidences.append(conf)

        return states, angles, confidences

    def _palm_orientation(self, landmarks):
        """
        利用 MediaPipe 3D z 坐标推断手掌朝向
        Returns:
            facing_camera: 是否正面朝向摄像头
            orientation_confidence: 朝向的置信度
        """
        lm3d = self._extract_landmarks_3d(landmarks)

        # 手腕(0) 与中指根部(9) 的 z 差值
        # 正面手掌：手指 z < 手腕 z（手指更靠近相机）
        wrist_z = lm3d[0][2]
        middle_mcp_z = lm3d[9][2]
        z_diff = wrist_z - middle_mcp_z

        # 手掌法向量估算：用手腕(0)、食指根(5)、小指根(17)三点构成平面
        v1 = np.array([lm3d[5][0] - lm3d[0][0],
                        lm3d[5][1] - lm3d[0][1],
                        lm3d[5][2] - lm3d[0][2]])
        v2 = np.array([lm3d[17][0] - lm3d[0][0],
                        lm3d[17][1] - lm3d[0][1],
                        lm3d[17][2] - lm3d[0][2]])
        normal = np.cross(v1, v2)
        norm_mag = np.linalg.norm(normal)

        if norm_mag > 0:
            normal = normal / norm_mag
            # 法向量的 z 分量越大，说明手掌越正对相机
            z_component = abs(normal[2])
            facing_camera = z_component > 0.3
            orientation_confidence = min(1.0, z_component)
        else:
            facing_camera = True
            orientation_confidence = 0.5

        return facing_camera, orientation_confidence

    def _normalized_features(self, lm):
        """
        计算归一化特征（尺度不变）
        Returns:
            dict: {
                "bbox_diagonal": 手掌 BBox 对角线长度,
                "tip_to_palm_ratios": 各指尖到掌心距离 / BBox 对角线,
                "finger_spread": 手指间距比率
            }
        """
        xs = [p[0] for p in lm]
        ys = [p[1] for p in lm]
        bbox_w = max(xs) - min(xs)
        bbox_h = max(ys) - min(ys)
        diagonal = math.sqrt(bbox_w ** 2 + bbox_h ** 2)

        if diagonal == 0:
            diagonal = 1e-6

        # 掌心近似为手腕(0)和中指根(9)的中点
        palm_center = ((lm[0][0] + lm[9][0]) / 2, (lm[0][1] + lm[9][1]) / 2)

        # 各指尖到掌心距离 / BBox 对角线
        tip_indices = [4, 8, 12, 16, 20]
        tip_ratios = []
        for tip_idx in tip_indices:
            dist = self._distance(lm[tip_idx], palm_center)
            tip_ratios.append(dist / diagonal)

        return {
            "bbox_diagonal": diagonal,
            "tip_to_palm_ratios": tip_ratios,
        }

    # ======================== 分类逻辑 ========================

    def classify(self, landmarks):
        """
        完整手势分类流程
        Args:
            landmarks: MediaPipe HandLandmarks 对象
        Returns:
            gesture_name: 手势名称 (str) 或 "unknown"
            confidence: 综合置信度 (float, 0-1)
            details: 特征详情字典 (供调试/日志)
        """
        lm2d = self._extract_landmarks_2d(landmarks)

        # Step 1: 手掌朝向检测（3D 约束）
        facing_camera, orient_conf = self._palm_orientation(landmarks)

        # Step 2: 获取手指状态
        finger_states, finger_angles, finger_confs = self._get_finger_states(lm2d)

        # Step 3: 归一化特征
        norm_features = self._normalized_features(lm2d)

        # 构建详情字典
        details = {
            "finger_states": finger_states,
            "finger_angles": finger_angles,
            "finger_confidences": finger_confs,
            "facing_camera": facing_camera,
            "orientation_confidence": orient_conf,
            "tip_ratios": norm_features["tip_to_palm_ratios"],
        }

        # 如果手掌大幅侧面，降低整体置信度
        orientation_penalty = 1.0 if facing_camera else 0.5

        # Step 4: 遍历规则表进行匹配
        best_gesture = "unknown"
        best_confidence = 0.0

        for gesture_name, rule in GESTURE_RULES.items():
            match, conf = self._match_rule(
                gesture_name, rule, finger_states, finger_confs,
                lm2d, finger_angles
            )
            if match and conf > best_confidence:
                best_gesture = gesture_name
                best_confidence = conf

        # 应用朝向惩罚
        best_confidence *= orientation_penalty

        # 低于最低置信度时判为 unknown
        if best_confidence < self.min_confidence:
            best_gesture = "unknown"
            best_confidence = 0.0

        logger.debug(
            f"Classified: {best_gesture} (conf={best_confidence:.2f}) "
            f"fingers={finger_states} orient={facing_camera}"
        )

        return best_gesture, best_confidence, details

    def _match_rule(self, name, rule, states, confs, lm, angles):
        """
        检查手指状态是否匹配某条规则
        Returns:
            match: 是否匹配 (bool)
            confidence: 匹配置信度 (float)
        """
        expected = rule["fingers_up"]
        conf_sum = 0.0
        match_count = 0

        for i, (exp, actual, c) in enumerate(zip(expected, states, confs)):
            if exp == -1:
                # 不关心此手指
                conf_sum += 0.8
                match_count += 1
                continue
            if exp == actual:
                conf_sum += c
                match_count += 1
            else:
                return False, 0.0  # 不匹配即失败

        base_confidence = conf_sum / len(expected) if len(expected) > 0 else 0.0

        # victory 手势额外检查 V 字张开角度
        if name == "victory" and "v_angle_range" in rule:
            v_min, v_max = rule["v_angle_range"]
            # 食指(8)、食指根(5)、中指(12) 构成 V 字
            v_angle = self._three_point_angle(lm[8], lm[5], lm[12])
            if not (v_min < v_angle < v_max):
                return False, 0.0
            # V 字角度越接近中间值（约 40-60°），置信度越高
            angle_center = (v_min + v_max) / 2
            angle_spread = (v_max - v_min) / 2
            angle_conf = 1.0 - abs(v_angle - angle_center) / angle_spread
            base_confidence = base_confidence * 0.7 + angle_conf * 0.3

        return True, min(1.0, base_confidence)
