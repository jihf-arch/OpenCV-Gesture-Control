# modules/skin_detector.py
"""
肤色检测模块
功能：YCrCb + HSV 双空间肤色分割、形态学优化、面积过滤、手部 ROI 提取
论文对应：关键技术 - 肤色检测与手部区域定位

技术原理：
  - 肤色在 YCrCb 空间的 Cr/Cb 分量上聚类性好，受亮度影响较小
  - 同时结合 HSV 空间的 H 分量进行交叉验证，提升鲁棒性
  - 双空间取交集可以有效排除与肤色相近的背景干扰
"""

import cv2
import numpy as np


class SkinDetector:
    """基于 YCrCb + HSV 双颜色空间的肤色检测器"""

    def __init__(self, config=None):
        """
        Args:
            config: 配置字典，可包含以下键：
                - ycrcb_lower: YCrCb 下界 (默认 [0, 133, 77])
                - ycrcb_upper: YCrCb 上界 (默认 [255, 173, 127])
                - hsv_lower: HSV 下界 (默认 [0, 30, 60])
                - hsv_upper: HSV 上界 (默认 [20, 150, 255])
                - min_area_ratio: 最小面积比率，相对于总面积 (默认 0.01)
                - morph_kernel_size: 形态学核大小 (默认 7)
        """
        cfg = config or {}

        # YCrCb 肤色阈值范围
        self.ycrcb_lower = np.array(cfg.get("ycrcb_lower", [0, 133, 77]))
        self.ycrcb_upper = np.array(cfg.get("ycrcb_upper", [255, 173, 127]))

        # HSV 肤色阈值范围
        self.hsv_lower = np.array(cfg.get("hsv_lower", [0, 30, 60]))
        self.hsv_upper = np.array(cfg.get("hsv_upper", [20, 150, 255]))

        # 最小面积比率（小于此比率的连通域将被过滤）
        self.min_area_ratio = cfg.get("min_area_ratio", 0.01)

        # 形态学核
        ksize = cfg.get("morph_kernel_size", 7)
        self.morph_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (ksize, ksize)
        )

    def _ycrcb_mask(self, frame):
        """YCrCb 颜色空间肤色分割"""
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        return cv2.inRange(ycrcb, self.ycrcb_lower, self.ycrcb_upper)

    def _hsv_mask(self, frame):
        """HSV 颜色空间肤色分割"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)

    def _morphology_optimize(self, mask):
        """形态学优化：开运算去噪 + 闭运算填充"""
        # 开运算：去除小噪点
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.morph_kernel, iterations=2)
        # 闭运算：填充手部空洞
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, self.morph_kernel, iterations=2)
        # 额外的高斯模糊平滑边缘
        smoothed = cv2.GaussianBlur(closed, (5, 5), 0)
        # 重新二值化
        _, result = cv2.threshold(smoothed, 127, 255, cv2.THRESH_BINARY)
        return result

    def _filter_by_area(self, mask):
        """面积阈值过滤：剔除面积过小的连通域"""
        total_area = mask.shape[0] * mask.shape[1]
        min_area = total_area * self.min_area_ratio

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        filtered = np.zeros_like(mask)
        valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
        if valid_contours:
            cv2.drawContours(filtered, valid_contours, -1, 255, cv2.FILLED)

        return filtered, valid_contours

    def detect(self, frame):
        """
        完整肤色检测流程
        Args:
            frame: BGR 帧（建议已做高斯滤波预处理）
        Returns:
            result: dict {
                "mask":      最终肤色掩膜 (二值图),
                "roi":       手部 ROI 边界框 (x, y, w, h) 或 None,
                "contours":  有效轮廓列表,
                "detected":  是否检测到手部 (bool)
            }
        """
        # Step 1: 双空间肤色分割
        ycrcb_mask = self._ycrcb_mask(frame)
        hsv_mask = self._hsv_mask(frame)

        # Step 2: 双空间取交集（或取并集，按需选择）
        # 取并集以提高召回率；若误检多可改为 cv2.bitwise_and
        combined_mask = cv2.bitwise_or(ycrcb_mask, hsv_mask)

        # Step 3: 形态学优化
        optimized = self._morphology_optimize(combined_mask)

        # Step 4: 面积过滤
        final_mask, valid_contours = self._filter_by_area(optimized)

        # Step 5: 提取最大连通域作为手部 ROI
        roi = None
        if valid_contours:
            largest = max(valid_contours, key=cv2.contourArea)
            roi = cv2.boundingRect(largest)

        return {
            "mask": final_mask,
            "roi": roi,
            "contours": valid_contours,
            "detected": len(valid_contours) > 0
        }

    def draw_roi(self, frame, roi, color=(0, 255, 0), thickness=2):
        """在帧上绘制手部 ROI 矩形框"""
        if roi is not None:
            x, y, w, h = roi
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
            cv2.putText(frame, "Hand ROI", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    def get_debug_views(self, frame):
        """
        返回各检测步骤的可视化（供论文截图 / 调试用）
        Returns:
            dict: {
                "original":     原图,
                "ycrcb_mask":   YCrCb 掩膜,
                "hsv_mask":     HSV 掩膜,
                "combined":     双空间合并掩膜,
                "final_mask":   最终掩膜（形态学 + 面积过滤后）,
                "result":       标注 ROI 的结果图
            }
        """
        ycrcb_mask = self._ycrcb_mask(frame)
        hsv_mask = self._hsv_mask(frame)
        combined = cv2.bitwise_or(ycrcb_mask, hsv_mask)
        optimized = self._morphology_optimize(combined)
        final_mask, valid_contours = self._filter_by_area(optimized)

        # 标注结果图
        result_frame = frame.copy()
        if valid_contours:
            largest = max(valid_contours, key=cv2.contourArea)
            roi = cv2.boundingRect(largest)
            self.draw_roi(result_frame, roi)
            # 绘制轮廓
            cv2.drawContours(result_frame, valid_contours, -1, (0, 255, 255), 2)

        return {
            "original": frame.copy(),
            "ycrcb_mask": cv2.cvtColor(ycrcb_mask, cv2.COLOR_GRAY2BGR),
            "hsv_mask": cv2.cvtColor(hsv_mask, cv2.COLOR_GRAY2BGR),
            "combined": cv2.cvtColor(combined, cv2.COLOR_GRAY2BGR),
            "final_mask": cv2.cvtColor(final_mask, cv2.COLOR_GRAY2BGR),
            "result": result_frame,
        }
