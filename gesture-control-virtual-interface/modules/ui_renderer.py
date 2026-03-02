# modules/ui_renderer.py
"""
UI 渲染引擎
功能：统一管理所有 OpenCV 画面渲染，包括信息面板、进度条、状态提示、
      启动画面、帮助覆盖层等，使 main.py 保持精简。
论文对应：系统实现 - 用户交互界面设计
"""

import cv2
import time
import numpy as np

# 手势信息（用于帮助页面和启动画面）
GESTURE_INFO = {
    "fist":    {"label": "Fist",        "ppt": "Prev Page",     "music": "Vol Down",   "icon": "✊"},
    "palm":    {"label": "Palm",        "ppt": "Play/Pause",    "music": "Play/Pause", "icon": "✋"},
    "index":   {"label": "Index",       "ppt": "Next Page",     "music": "Vol Up",     "icon": "☝"},
    "victory": {"label": "Victory",     "ppt": "Exit (Esc)",    "music": "Exit (Esc)", "icon": "✌"},
}

# 颜色常量 (BGR)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (0, 0, 255)
COLOR_ORANGE = (0, 165, 255)
COLOR_CYAN = (0, 255, 255)
COLOR_YELLOW = (0, 255, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (180, 180, 180)
COLOR_DARK_GRAY = (60, 60, 60)
COLOR_BG = (20, 20, 20)


class UIRenderer:
    """
    UI 渲染器

    将所有画面渲染逻辑集中管理，main.py 只需调用：
      - render_splash()    启动画面
      - render_hud()       主界面 HUD
      - render_help()      帮助覆盖层
    """

    def __init__(self):
        self.show_help = False          # 帮助页面开关
        self.action_flash_time = 0      # 动作触发闪光时间
        self.action_flash_text = ""     # 闪光文字内容
        self.mode_switch_flash = 0      # 模式切换闪光

    # ======================== 基础绘制工具 ========================

    @staticmethod
    def _draw_panel(frame, x, y, w, h, alpha=0.55):
        """绘制半透明深色面板"""
        overlay = frame.copy()
        # 面板带圆角效果（用矩形近似）
        cv2.rectangle(overlay, (x, y), (x + w, y + h), COLOR_BG, cv2.FILLED)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        # 边框
        cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 50), 1)

    @staticmethod
    def _draw_progress_bar(frame, x, y, w, h, progress, color, bg_color=COLOR_DARK_GRAY):
        """绘制进度条"""
        progress = max(0.0, min(1.0, progress))
        cv2.rectangle(frame, (x, y), (x + w, y + h), bg_color, cv2.FILLED)
        fill_w = int(w * progress)
        if fill_w > 0:
            cv2.rectangle(frame, (x, y), (x + fill_w, y + h), color, cv2.FILLED)
        # 边框
        cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 80, 80), 1)

    @staticmethod
    def _put_text(frame, text, x, y, scale=0.7, color=COLOR_WHITE, thickness=2):
        """便捷文字绘制"""
        cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)

    # ======================== 启动画面 ========================

    def render_splash(self, frame):
        """
        渲染启动画面
        Args:
            frame: 摄像头帧（作为背景）
        Returns:
            splash_frame: 叠加了启动画面的帧
        """
        h, w = frame.shape[:2]
        splash = frame.copy()

        # 半透明全屏覆盖
        overlay = np.zeros_like(splash)
        overlay[:] = (30, 30, 40)
        cv2.addWeighted(overlay, 0.85, splash, 0.15, 0, splash)

        # 标题
        title = "Gesture Control System"
        title_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
        tx = (w - title_size[0]) // 2
        self._put_text(splash, title, tx, h // 4, 1.5, COLOR_CYAN, 3)

        # 副标题
        subtitle = "Vision-Based Virtual Interface Controller"
        sub_size = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        sx = (w - sub_size[0]) // 2
        self._put_text(splash, subtitle, sx, h // 4 + 45, 0.7, COLOR_GRAY, 1)

        # 技术栈
        tech = "Python  |  OpenCV  |  MediaPipe"
        tech_size = cv2.getTextSize(tech, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
        self._put_text(splash, tech, (w - tech_size[0]) // 2, h // 4 + 80, 0.6, (100, 180, 255), 1)

        # 手势说明表格
        table_y = h // 2 - 20
        table_x = w // 2 - 250
        col_w = 170

        # 表头
        self._draw_panel(splash, table_x - 10, table_y - 30, 520, 200, 0.4)
        self._put_text(splash, "Gesture", table_x, table_y, 0.65, COLOR_CYAN, 2)
        self._put_text(splash, "PPT Mode", table_x + col_w, table_y, 0.65, (255, 200, 0), 2)
        self._put_text(splash, "Music Mode", table_x + col_w * 2, table_y, 0.65, (200, 100, 255), 2)
        cv2.line(splash, (table_x, table_y + 8), (table_x + 500, table_y + 8), (80, 80, 80), 1)

        row_y = table_y + 38
        for gesture_id, info in GESTURE_INFO.items():
            self._put_text(splash, f"{info['icon']}  {info['label']}", table_x, row_y, 0.6, COLOR_WHITE, 1)
            self._put_text(splash, info["ppt"], table_x + col_w, row_y, 0.55, (200, 200, 200), 1)
            self._put_text(splash, info["music"], table_x + col_w * 2, row_y, 0.55, (200, 200, 200), 1)
            row_y += 35

        # 底部提示
        hint = "Press any key to start  |  Q: Quit  |  H: Help  |  D: Debug  |  C: Control ON/OFF"
        hint_size = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0]
        hx = (w - hint_size[0]) // 2
        # 闪烁效果
        if int(time.time() * 2) % 2 == 0:
            self._put_text(splash, hint, hx, h - 50, 0.55, COLOR_GREEN, 1)

        return splash

    # ======================== 主界面 HUD ========================

    def render_hud(self, frame, fps, gesture, confidence, facing_camera,
                   hand_detected, fsm_info, controller_enabled):
        """
        渲染主界面 HUD（Head-Up Display）
        在帧上叠加所有状态信息
        """
        h, w = frame.shape[:2]

        # ---- 左侧信息面板 ----
        panel_w, panel_h = 420, 290
        self._draw_panel(frame, 8, 8, panel_w, panel_h)

        x0 = 20
        y = 38
        line_h = 32
        bar_x, bar_w, bar_h = 175, 200, 14

        # FPS
        fps_color = COLOR_GREEN if fps >= 15 else COLOR_ORANGE
        self._put_text(frame, f"FPS: {int(fps)}", x0, y, 0.85, fps_color, 2)
        y += line_h

        # 模式
        mode = fsm_info["mode"]
        mode_color = (255, 200, 0) if mode == "ppt" else (200, 100, 255)
        mode_label = "PPT" if mode == "ppt" else "MUSIC"
        self._put_text(frame, f"Mode: {mode_label}", x0, y, 0.85, mode_color, 2)
        # 模式指示灯
        dot_x = 200
        cv2.circle(frame, (dot_x, y - 6), 8, mode_color, cv2.FILLED)
        y += line_h

        # 手势
        gesture_text = gesture if gesture else "..."
        self._put_text(frame, f"Gesture: {gesture_text}", x0, y, 0.75, COLOR_ORANGE, 2)
        y += line_h

        # 置信度 + 进度条
        self._put_text(frame, f"Conf: {confidence:.2f}", x0, y, 0.65, COLOR_CYAN, 2)
        conf_color = COLOR_GREEN if confidence >= 0.6 else COLOR_ORANGE if confidence >= 0.3 else COLOR_RED
        self._draw_progress_bar(frame, bar_x, y - bar_h, bar_w, bar_h, confidence, conf_color)
        y += line_h

        # FSM 状态 + 防抖进度条
        state = fsm_info["state"]
        state_colors = {
            "idle": (128, 128, 128),
            "detecting": (0, 200, 255),
            "confirming": (255, 255, 0),
            "executing": COLOR_GREEN,
            "cooldown": COLOR_RED,
        }
        state_color = state_colors.get(state, COLOR_GRAY)
        self._put_text(frame, f"FSM: {state.upper()}", x0, y, 0.65, state_color, 2)
        self._draw_progress_bar(frame, bar_x, y - bar_h, bar_w, bar_h,
                                fsm_info["debounce_progress"], (0, 200, 200))
        y += line_h

        # 控制器状态 + 触发次数
        ctrl_color = COLOR_GREEN if controller_enabled else COLOR_RED
        ctrl_label = "ON" if controller_enabled else "OFF"
        self._put_text(frame, f"Control: {ctrl_label}", x0, y, 0.6, ctrl_color, 2)
        self._put_text(frame, f"Triggered: {fsm_info['total_triggers']}", 200, y, 0.6, COLOR_GRAY, 1)
        y += line_h

        # 上次动作
        if fsm_info["last_action"]:
            self._put_text(frame, f"Last: {fsm_info['last_action']}", x0, y, 0.55, COLOR_GRAY, 1)
        y += line_h

        # 手部状态
        if hand_detected:
            if not facing_camera:
                self._put_text(frame, "Please face camera", x0, y, 0.65, COLOR_ORANGE, 2)
            else:
                self._put_text(frame, "Hand OK", x0, y, 0.65, COLOR_GREEN, 2)
        else:
            self._put_text(frame, "No hand", x0, y, 0.65, COLOR_RED, 2)

        # ---- 右上角状态指示 ----

        # 冷却倒计时
        if fsm_info["is_cooldown"]:
            cd = fsm_info["cooldown_remaining"]
            self._draw_panel(frame, w - 260, 8, 250, 35, 0.5)
            self._put_text(frame, f"Cooldown: {cd:.1f}s", w - 250, 33, 0.7, COLOR_RED, 2)

        # Victory 模式切换进度
        vp = fsm_info["victory_progress"]
        if vp > 0.1:
            self._draw_panel(frame, w - 310, 48, 300, 40, 0.5)
            self._put_text(frame, f"Mode Switch: {int(vp * 100)}%", w - 300, 78, 0.75, (200, 100, 255), 2)
            self._draw_progress_bar(frame, w - 300, 82, 280, 6, vp, (200, 100, 255))

        # ---- 底部中间提示 ----

        # 手掌朝向警告（大字）
        if hand_detected and not facing_camera:
            warn = "Please face the camera"
            ws = cv2.getTextSize(warn, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
            wx = (w - ws[0]) // 2
            self._draw_panel(frame, wx - 15, h - 65, ws[0] + 30, 45, 0.6)
            self._put_text(frame, warn, wx, h - 30, 1.0, COLOR_ORANGE, 2)

        # ---- 动作触发闪光效果 ----
        if time.time() - self.action_flash_time < 0.5:
            flash_text = self.action_flash_text
            fs = cv2.getTextSize(flash_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0]
            fx = (w - fs[0]) // 2
            fy = h // 2
            self._draw_panel(frame, fx - 20, fy - 40, fs[0] + 40, 60, 0.5)
            self._put_text(frame, flash_text, fx, fy, 1.2, COLOR_GREEN, 3)

        # 模式切换闪光
        if time.time() - self.mode_switch_flash < 1.0:
            ms_text = "Mode Switched!"
            ms_s = cv2.getTextSize(ms_text, cv2.FONT_HERSHEY_SIMPLEX, 1.3, 3)[0]
            mx = (w - ms_s[0]) // 2
            self._put_text(frame, ms_text, mx, 60, 1.3, COLOR_CYAN, 3)

        # ---- 快捷键提示（底部） ----
        keys_hint = "Q:Quit  H:Help  D:Debug  C:Control"
        self._put_text(frame, keys_hint, 10, h - 10, 0.45, (100, 100, 100), 1)

    def flash_action(self, action_text):
        """触发动作闪光效果"""
        self.action_flash_time = time.time()
        self.action_flash_text = action_text

    def flash_mode_switch(self):
        """触发模式切换闪光效果"""
        self.mode_switch_flash = time.time()

    # ======================== 帮助覆盖层 ========================

    def render_help(self, frame):
        """渲染帮助覆盖层（按 H 键切换显示）"""
        h, w = frame.shape[:2]

        # 半透明覆盖
        overlay = np.zeros_like(frame)
        overlay[:] = (20, 20, 30)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

        # 标题
        title = "HELP  -  Gesture Reference"
        ts = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
        self._put_text(frame, title, (w - ts[0]) // 2, 60, 1.0, COLOR_CYAN, 2)

        # 分割线
        cv2.line(frame, (w // 4, 80), (w * 3 // 4, 80), (60, 60, 60), 1)

        # 手势说明
        y = 130
        col1_x = w // 2 - 280
        col2_x = w // 2 - 60
        col3_x = w // 2 + 140

        # 表头
        self._put_text(frame, "Gesture", col1_x, y, 0.7, COLOR_CYAN, 2)
        self._put_text(frame, "PPT Mode", col2_x, y, 0.7, (255, 200, 0), 2)
        self._put_text(frame, "Music Mode", col3_x, y, 0.7, (200, 100, 255), 2)
        y += 15
        cv2.line(frame, (col1_x, y), (col3_x + 180, y), (60, 60, 60), 1)
        y += 30

        for gesture_id, info in GESTURE_INFO.items():
            self._put_text(frame, f"{info['icon']}  {info['label']}", col1_x, y, 0.65, COLOR_WHITE, 2)
            self._put_text(frame, info["ppt"], col2_x, y, 0.6, (200, 200, 200), 1)
            self._put_text(frame, info["music"], col3_x, y, 0.6, (200, 200, 200), 1)
            y += 40

        # 快捷键说明
        y += 20
        cv2.line(frame, (w // 4, y), (w * 3 // 4, y), (60, 60, 60), 1)
        y += 35
        self._put_text(frame, "Keyboard Shortcuts", (w - 280) // 2, y, 0.8, COLOR_CYAN, 2)
        y += 40

        shortcuts = [
            ("Q", "Quit application"),
            ("H", "Toggle this help"),
            ("D", "Toggle debug view"),
            ("C", "Toggle control ON/OFF"),
        ]
        for key, desc in shortcuts:
            self._put_text(frame, f"[{key}]", col1_x + 40, y, 0.65, COLOR_GREEN, 2)
            self._put_text(frame, desc, col1_x + 120, y, 0.6, COLOR_GRAY, 1)
            y += 35

        # 模式切换说明
        y += 15
        self._put_text(frame, "Hold Victory gesture ~1.5s to switch mode", col1_x, y, 0.55, COLOR_ORANGE, 1)

        # 关闭提示
        close_text = "Press H to close"
        cs = cv2.getTextSize(close_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
        self._put_text(frame, close_text, (w - cs[0]) // 2, h - 40, 0.6, COLOR_GRAY, 1)

    def toggle_help(self):
        """切换帮助页面显示"""
        self.show_help = not self.show_help
        return self.show_help
