# tests/benchmark.py
"""
性能基准测试工具 (Performance Benchmark)
论文对应：系统测试 - 性能测试（帧率与延迟分析）

运行该脚本将不显示 GUI 界面，直接使用本地视频文件或摄像头运行 N 帧，
统计各模块的平均耗时，用于寻找性能瓶颈。
"""

import sys
import os
import time
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.camera import Camera
from modules.preprocessor import Preprocessor
from modules.skin_detector import SkinDetector
from modules.hand_detector import HandDetector
from modules.gesture_recognizer import get_classifier
from config import PREPROCESS_CONFIG, SKIN_CONFIG, RECOGNITION_CONFIG

def run_benchmark(num_frames=300):
    print(f"=== 开始性能基准测试 (运行 {num_frames} 帧) ===")
    
    # 模块初始化
    camera = Camera()
    preprocessor = Preprocessor(PREPROCESS_CONFIG)
    skin_detector = SkinDetector(SKIN_CONFIG)
    hand_detector = HandDetector()
    classifier = get_classifier()
    
    # 等待摄像头预热
    for _ in range(10):
        camera.read()

    times = {
        "read": [],
        "preprocess": [],
        "skin_detect": [],
        "mediapipe": [],
        "classify": [],
        "total": []
    }

    processed_frames = 0
    start_benchmark = time.time()

    while processed_frames < num_frames:
        t0 = time.time()
        
        # 1. 读取帧
        frame = camera.read()
        if frame is None:
            break
        t1 = time.time()
        times["read"].append(t1 - t0)
        
        # 2. 图像预处理
        processed = preprocessor.process(frame, enhance=True)
        t2 = time.time()
        times["preprocess"].append(t2 - t1)
        
        # 3. 肤色检测
        skin_result = skin_detector.detect(processed)
        t3 = time.time()
        times["skin_detect"].append(t3 - t2)
        
        # 4. MediaPipe 手部检测
        results = hand_detector.process(processed)
        t4 = time.time()
        times["mediapipe"].append(t4 - t3)
        
        # 5. 手势分类
        if results.multi_hand_landmarks:
            for hl in results.multi_hand_landmarks:
                classifier.classify(hl)
        t5 = time.time()
        times["classify"].append(t5 - t4)
        
        times["total"].append(t5 - t0)
        processed_frames += 1
        
        if processed_frames % 50 == 0:
            print(f"已处理 {processed_frames}/{num_frames} 帧...")

    end_benchmark = time.time()
    camera.release()

    # 打印统计结果
    print("\n=== 基准测试结果报告 ===")
    print(f"总计处理帧数: {processed_frames}")
    print(f"总体耗时: {end_benchmark - start_benchmark:.2f} 秒")
    print(f"平均帧率 (FPS): {processed_frames / (end_benchmark - start_benchmark):.1f}")
    
    print("\n各模块平均单帧耗时 (毫秒):")
    total_avg_ms = np.mean(times["total"]) * 1000
    for name, t_list in times.items():
        if name == "total":
            continue
        avg_ms = np.mean(t_list) * 1000
        percent = (avg_ms / total_avg_ms) * 100 if total_avg_ms > 0 else 0
        print(f"  - {name.ljust(12)}: {avg_ms:6.2f} ms ({percent:5.1f}%)")
        
    print(f"\n整体端到端单帧延迟: {total_avg_ms:.2f} 毫秒")

if __name__ == "__main__":
    run_benchmark(300)
