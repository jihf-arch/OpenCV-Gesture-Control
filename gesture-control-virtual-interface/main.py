import cv2
import time
from modules.camera import Camera
from modules.preprocessor import Preprocessor
from modules.skin_detector import SkinDetector
from modules.hand_detector import HandDetector
from modules.gesture_recognizer import recognize_gesture, get_classifier
from modules.fsm import GestureFSM
from modules.controller import Controller
from modules.ui_renderer import UIRenderer
from utils.logger import get_logger
from config import (
    PREPROCESS_CONFIG, SKIN_CONFIG,
    ENABLE_PREPROCESSING, ENABLE_SKIN_DETECTION, DEBUG_MODE
)

logger = get_logger()


def main():
    # ==================== 初始化所有模块 ====================
    camera = Camera()
    preprocessor = Preprocessor(PREPROCESS_CONFIG)
    skin_detector = SkinDetector(SKIN_CONFIG)
    detector = HandDetector()
    fsm = GestureFSM()
    controller = Controller()
    ui = UIRenderer()

    prev_time = time.time()

    # ==================== 启动画面 ====================
    splash_shown = True
    while splash_shown:
        frame = camera.read()
        if frame is None:
            return
        splash = ui.render_splash(frame)
        cv2.imshow("Gesture Control System", splash)
        key = cv2.waitKey(1) & 0xFF
        if key != 255:  # 任意键退出启动画面
            splash_shown = False

    # ==================== 主循环 ====================
    while True:
        frame = camera.read()
        if frame is None:
            break

        # 1. 图像预处理
        processed = preprocessor.process(frame) if ENABLE_PREPROCESSING else frame.copy()

        # 2. 肤色检测 & ROI
        if ENABLE_SKIN_DETECTION:
            skin_result = skin_detector.detect(processed)
            if skin_result["detected"]:
                skin_detector.draw_roi(frame, skin_result["roi"])

        # 3. 手部检测
        results = detector.process(processed)
        detector.draw(frame, results)

        # 4. 手势识别
        gesture, confidence, facing_camera = None, 0.0, True
        if results.multi_hand_landmarks:
            classifier = get_classifier()
            for hand_lm in results.multi_hand_landmarks:
                gesture, confidence = recognize_gesture(hand_lm)
                _, _, details = classifier.classify(hand_lm)
                facing_camera = details.get("facing_camera", True)

        # 5. FSM 防抖
        action = fsm.update(gesture, confidence)

        # 6. 执行控制
        if action == "mode_switch":
            ui.flash_mode_switch()
        elif action:
            result = controller.execute(action, fsm.current_mode)
            if result.success:
                ui.flash_action(f"{action.upper()} -> {result.key}")

        # 7. 计算 FPS
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if curr_time != prev_time else 0
        prev_time = curr_time

        # 8. 渲染 UI
        hand_detected = results.multi_hand_landmarks is not None
        fsm_info = fsm.get_state_info()

        if ui.show_help:
            ui.render_help(frame)
        else:
            ui.render_hud(frame, fps, gesture, confidence, facing_camera,
                          hand_detected, fsm_info, controller.enabled)

        # 9. 调试模式
        if DEBUG_MODE:
            h, w = frame.shape[:2]
            small = (w // 3, h // 3)
            for name, img in preprocessor.get_debug_views(frame).items():
                cv2.imshow(f"[Pre] {name}", cv2.resize(img, small))
            for name, img in skin_detector.get_debug_views(processed).items():
                cv2.imshow(f"[Skin] {name}", cv2.resize(img, small))

        cv2.imshow("Gesture Control System", frame)

        # 10. 快捷键处理
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('h'):
            ui.toggle_help()
        elif key == ord('d'):
            import config
            config.DEBUG_MODE = not config.DEBUG_MODE
            if not config.DEBUG_MODE:
                cv2.destroyAllWindows()
        elif key == ord('c'):
            controller.toggle()

    # ==================== 退出统计 ====================
    stats = controller.get_stats()
    fsm_final = fsm.get_state_info()
    logger.info(
        f"Session: triggers={fsm_final['total_triggers']} "
        f"suppressed={fsm_final['total_suppressed']} "
        f"executed={stats['total_executed']} failed={stats['total_failed']}"
    )
    camera.release()
    cv2.destroyAllWindows()
    logger.info("Program exited normally")


if __name__ == "__main__":
    main()