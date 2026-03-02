import logging

# ======================== 手势映射（按照开题报告） ========================
GESTURE_MAP = {
    "fist":    {"ppt": "left",      "music": "volumedown"},
    "palm":    {"ppt": "space",     "music": "playpause"},
    "index":   {"ppt": "right",     "music": "volumeup"},
    "victory": {"ppt": "esc",       "music": "esc"}
}

MODES = ["ppt", "music"]
DEFAULT_MODE = "ppt"

# ======================== 防抖参数（可调） ========================
DEBOUNCE_FRAMES = 5          # 连续5帧相同才确认
COOLDOWN_SECONDS = 0.5       # 触发后冷却0.5秒
MODE_SWITCH_HOLD_FRAMES = 45 # victory保持约1.5秒（30fps）切换模式
CONFIDENCE_THRESHOLD = 0.6   # FSM 置信度门槛（低于此值不进入状态机）
TRANSITION_SUPPRESS_FRAMES = 3  # 过渡态抑制：最近N帧中有多种手势则抑制

# ======================== 图像预处理配置 ========================
PREPROCESS_CONFIG = {
    "gaussian_ksize": 5,          # 高斯滤波核大小
    "clahe_clip_limit": 2.0,      # CLAHE 对比度裁剪限制
    "clahe_grid_size": 8,         # CLAHE 网格大小
    "morph_kernel_size": 5,       # 形态学操作核大小
    "adaptive_block_size": 11,    # 自适应阈值块大小
    "adaptive_c": 2,              # 自适应阈值常数
}

# ======================== 肤色检测配置 ========================
SKIN_CONFIG = {
    "ycrcb_lower": [0, 133, 77],      # YCrCb 下界
    "ycrcb_upper": [255, 173, 127],    # YCrCb 上界
    "hsv_lower": [0, 30, 60],          # HSV 下界
    "hsv_upper": [20, 150, 255],       # HSV 上界
    "min_area_ratio": 0.01,            # 最小面积比率（相对总面积）
    "morph_kernel_size": 7,            # 形态学核大小
}

# ======================== 手势识别配置 ========================
RECOGNITION_CONFIG = {
    "finger_straight_angle": 160,    # 手指伸直角度阈值（> 此值 = 伸直）
    "finger_bent_angle": 100,        # 手指弯曲角度阈值（< 此值 = 弯曲）
    "palm_z_threshold": 0.1,         # 手掌朝向 z 差值阈值
    "min_confidence": 0.5,           # 最低有效置信度
}

# ======================== 调试与显示 ========================
ENABLE_PREPROCESSING = True   # 是否启用预处理管道（可关闭用于对比实验）
ENABLE_SKIN_DETECTION = True  # 是否启用肤色检测 ROI 显示
DEBUG_MODE = False             # 调试模式：显示预处理各步骤窗口

# ======================== 日志配置 ========================
logging.basicConfig(
    filename='logs/gesture.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)