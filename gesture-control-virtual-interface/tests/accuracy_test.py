# tests/accuracy_test.py
"""
准确率实验工具 (Accuracy Test)
论文对应：系统测试 - 识别准确率测试

提供交互式界面，指导用户按提示摆出特定手势，
记录成功/失败次数，并输出混淆矩阵数据（供论文图表使用）。
"""

import sys
import os
import time
import cv2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.camera import Camera
from modules.preprocessor import Preprocessor
from modules.hand_detector import HandDetector
from modules.gesture_classifier import GestureClassifier
from config import PREPROCESS_CONFIG, RECOGNITION_CONFIG

TEST_GESTURES = ["fist", "palm", "index", "victory"]
TEST_SAMPLES_PER_GESTURE = 10

def run_accuracy_test():
    print("=== 手势识别准确率实验 ===")
    print(f"将测试 {len(TEST_GESTURES)} 种手势，每种 {TEST_SAMPLES_PER_GESTURE} 次。")
    print("按任意键开始，测试中按 'q' 可提前中止。")
    input(">> 按回车键继续...")

    camera = Camera()
    preprocessor = Preprocessor(PREPROCESS_CONFIG)
    detector = HandDetector()
    classifier = GestureClassifier(RECOGNITION_CONFIG)
    
    results_matrix = {g: {res_g: 0 for res_g in TEST_GESTURES + ["unknown"]} for g in TEST_GESTURES}
    
    cv2.namedWindow("Accuracy Test")
    
    for target in TEST_GESTURES:
        print(f"\n======================================")
        print(f"准备测试手势: ** {target.upper()} **")
        print(f"======================================")
        
        for i in range(TEST_SAMPLES_PER_GESTURE):
            success = False
            detected_gesture = "unknown"
            
            # 每轮测试前有 2 秒准备时间
            start_prep = time.time()
            while time.time() - start_prep < 2.0:
                frame = camera.read()
                cv2.putText(frame, f"Prepare: {target.upper()}", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 165, 255), 3)
                cv2.putText(frame, f"Sample {i+1}/{TEST_SAMPLES_PER_GESTURE}", (50, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                cv2.imshow("Accuracy Test", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    camera.release()
                    cv2.destroyAllWindows()
                    sys.exit(0)
            
            # 捕获一帧进行测试（取 10 帧过滤防抖）
            captures = []
            start_test = time.time()
            while time.time() - start_test < 1.0:
                frame = camera.read()
                processed = preprocessor.process(frame)
                res = detector.process(processed)
                detector.draw(frame, res)
                
                curr_gest = "unknown"
                if res.multi_hand_landmarks:
                    for hl in res.multi_hand_landmarks:
                        g, c, _ = classifier.classify(hl)
                        curr_gest = g
                
                captures.append(curr_gest)
                
                cv2.putText(frame, f"Testing: {target.upper()} ({i+1}/{TEST_SAMPLES_PER_GESTURE})", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                cv2.imshow("Accuracy Test", frame)
                cv2.waitKey(1)
            
            # 取出现次数最多的手势作为此次判定结果
            if captures:
                detected_gesture = max(set(captures), key=captures.count)
            else:
                detected_gesture = "unknown"
                
            results_matrix[target][detected_gesture] += 1
            
            print(f"样本 {i+1:2d}: 目标={target.ljust(8)} | 识别={detected_gesture.ljust(8)} | {'✅' if target == detected_gesture else '❌'}")
    
    camera.release()
    cv2.destroyAllWindows()
    
    # 打印混淆矩阵
    print("\n\n=== 实验结果 (混淆矩阵) ===")
    print(f"{'Target \\ Pred':<15} | " + " | ".join([g.ljust(8) for g in TEST_GESTURES + ["unknown"]]))
    print("-" * 80)
    
    for target in TEST_GESTURES:
        row = f"{target:<15} | "
        total_tests = sum(results_matrix[target].values())
        correct = results_matrix[target][target]
        accuracy = (correct / total_tests) * 100 if total_tests > 0 else 0
        
        for pred in TEST_GESTURES + ["unknown"]:
            row += f"{results_matrix[target][pred]:<8} | "
        
        row += f" -> Acc: {accuracy:.1f}%"
        print(row)

if __name__ == "__main__":
    run_accuracy_test()
