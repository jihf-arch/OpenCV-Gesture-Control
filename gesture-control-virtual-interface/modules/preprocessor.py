# modules/preprocessor.py
"""
图像预处理管道模块
功能：高斯滤波去噪、直方图均衡化(CLAHE)、自适应阈值二值化、形态学操作
论文对应：系统实现 - 图像预处理管道
"""

import cv2
import numpy as np


class Preprocessor:
    """图像预处理管道，可通过 config 配置各项参数"""

    def __init__(self, config=None):
        """
        Args:
            config: 配置字典，可包含以下键：
                - gaussian_ksize: 高斯核大小 (默认 5)
                - clahe_clip_limit: CLAHE 对比度限制 (默认 2.0)
                - clahe_grid_size: CLAHE 网格大小 (默认 8)
                - morph_kernel_size: 形态学核大小 (默认 5)
                - adaptive_block_size: 自适应阈值块大小 (默认 11)
                - adaptive_c: 自适应阈值常数 (默认 2)
        """
        cfg = config or {}
        self.gaussian_ksize = cfg.get("gaussian_ksize", 5)
        self.clahe_clip = cfg.get("clahe_clip_limit", 2.0)
        self.clahe_grid = cfg.get("clahe_grid_size", 8)
        self.morph_ksize = cfg.get("morph_kernel_size", 5)
        self.adaptive_block = cfg.get("adaptive_block_size", 11)
        self.adaptive_c = cfg.get("adaptive_c", 2)

        # 创建 CLAHE 对象（自适应直方图均衡化）
        self.clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip,
            tileGridSize=(self.clahe_grid, self.clahe_grid)
        )

        # 形态学核
        self.morph_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.morph_ksize, self.morph_ksize)
        )

    def gaussian_blur(self, frame):
        """高斯滤波去噪"""
        k = self.gaussian_ksize
        return cv2.GaussianBlur(frame, (k, k), 0)

    def enhance_contrast(self, frame):
        """
        CLAHE 自适应直方图均衡化 —— 增强图像对比度
        对 LAB 颜色空间的 L 通道做均衡化，保持色彩不失真
        """
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        l_enhanced = self.clahe.apply(l_channel)
        lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
        return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

    def adaptive_threshold(self, gray):
        """
        自适应阈值二值化 —— 应对光照不均
        输入：灰度图
        输出：二值图
        """
        return cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            self.adaptive_block,
            self.adaptive_c
        )

    def morphology_clean(self, binary):
        """
        形态学操作 —— 开运算去小噪点 + 闭运算填充空洞
        输入/输出：二值图
        """
        # 开运算：先腐蚀后膨胀，去除小噪点
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, self.morph_kernel, iterations=2)
        # 闭运算：先膨胀后腐蚀，填充小空洞
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, self.morph_kernel, iterations=2)
        return closed

    def process(self, frame, enhance=True):
        """
        完整预处理管道
        Args:
            frame: BGR 原始帧
            enhance: 是否执行对比度增强（可关闭用于对比实验）
        Returns:
            processed: 预处理后的 BGR 帧（用于后续 MediaPipe 检测）
        """
        # Step 1: 高斯滤波去噪
        blurred = self.gaussian_blur(frame)

        # Step 2: CLAHE 对比度增强（可选）
        if enhance:
            processed = self.enhance_contrast(blurred)
        else:
            processed = blurred

        return processed

    def get_binary_mask(self, frame):
        """
        获取自适应二值化结果（用于调试展示、论文截图等）
        Args:
            frame: BGR 帧
        Returns:
            binary: 二值图
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        binary = self.adaptive_threshold(gray)
        cleaned = self.morphology_clean(binary)
        return cleaned

    def get_debug_views(self, frame):
        """
        返回各预处理步骤的可视化结果（供论文截图 / 调试用）
        Returns:
            dict: {
                "original": 原图,
                "blurred": 高斯滤波后,
                "enhanced": CLAHE 增强后,
                "binary": 二值化结果,
                "morphology": 形态学处理后
            }
        """
        blurred = self.gaussian_blur(frame)
        enhanced = self.enhance_contrast(blurred)
        gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
        binary = self.adaptive_threshold(gray)
        morphed = self.morphology_clean(binary)

        return {
            "original": frame.copy(),
            "blurred": blurred,
            "enhanced": enhanced,
            "binary": cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR),
            "morphology": cv2.cvtColor(morphed, cv2.COLOR_GRAY2BGR),
        }
