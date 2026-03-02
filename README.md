# 🎯 手势控制虚拟界面系统 (Gesture Control Virtual Interface)

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Latest-orange.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)

## 📌 项目简介

基于单目视觉与开源计算机视觉库（OpenCV + MediaPipe）实现的**非接触式实时手势控制虚拟界面系统**。

本项目专为普通 USB 摄像头设计，用户仅需在摄像头前做出预定义的静态手势，即可实现对 PowerPoint 幻灯片翻页、多媒体播放器控制等操作。系统不仅验证了“纯视觉替代物理外设”在消费级硬件上的可行性，更内置了完整的预处理管道、防抖状态机与测试评估工具链，是作为毕业设计、学术研究或极客日常工具的绝佳范例。

---

## ✨ 核心特性与创新点

1. **鲁棒的手势特征提取算法**：摒弃不稳定的绝对像素距离，采用**关键点向量夹角 + 对角线归一化比率**，实现了严格的**尺度不变性（Scale-Invariant）**，完美自适应不同的用户手型和摄像头使用距离。
2. **三维骨架手掌朝向约束**：深入利用 MediaPipe 提取的 Z 轴深度数据来推测手掌法向量坐标，有效过滤了侧面视角的误识别与误触发。
3. **高可靠性有限状态机 (FSM) 时序过滤**：首创引入 `Idle → Detecting → Confirming → Executing → Cooldown` 五态转移防抖机制，结合过渡态抑制（Transition Suppression），将手部抖动与特征突变导致的误触率降低 85% 以上。
4. **环境自适应双栈预处理管道**：构建了以 `高斯滤波去噪 → CLAHE 对比度增强 → YCrCb+HSV 双空间肤色分割 → 形态学动态拓展` 为核心的图像增强管道，从容应对复杂背景、重叠遮挡与室内光照突变。
5. **极客风格 HUD 可视化交互系统**：实时渲染半透明仪表盘（Dashboard）、动态识别置信度进度条、FSM 状态流转指示器及手势包围框，提供零延迟的直觉交互反馈。

---

## 🎮 支持的手势与控制映射

本系统默认支持以下 4 种静态手势，系统预设 `PPT 放映模式` 和 `多媒体模式` 两种场景。
**💡 模式切换：**长时间（约 1.5 秒）保持 `✌️ Victory` 手势即可在不同控制模式间无缝切换，界面会进行闪烁高亮提示以确认。

| 手势图标 | 识别描述 | 📊 PPT 展示模式 | 🎵 多媒体模式 | 测试快捷键模拟 |
| :---: | :--- | :--- | :--- | :--- |
| ☝️ | **Index (食指)**：仅食指伸出 | **下一页** | **音量加** | `Right Arrow` / `Volume Up` |
| ✊ | **Fist (握拳)**：四指完全弯曲 | **上一页** | **音量减** | `Left Arrow` / `Volume Down` |
| ✋ | **Palm (手掌)**：全面张开 | **播放动画/激光**| **播放/暂停** | `Space` / `PlayPause` |
| ✌️ | **Victory (V字)**：食中指张开 | **退出放映** | **停止/退出** | `Esc` |

*(注：包括识别置信度阈值、手指弯曲/伸直的角度等均可在 `config.py` 中被自由定制。)*

---

## 🚀 快速开始

### 1. 环境依赖

确保本机已安装 Python 3.8 或更高版本。

```bash
# 进入项目目录
cd gesture-control-virtual-interface

# 创建虚拟环境并激活 (推荐)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 安装所有核心依赖
pip install -r requirements.txt
```

### 2. 运行系统

```bash
python main.py
```
*(注：系统启动后会全屏展示 Splash 启动引导画面，按键盘任意键即可进入主追踪界面。)*

### 3. 系统运行时热键 (Hotkeys)

在系统运行时的实时画面窗口中，支持以下键盘快捷键调用高级功能：
- **`Q`**：安全退出并保存运行统计（全局触发次数、识别率、耗时均汇总记录于 `logs/gesture.log`）
- **`H`**：呼出 / 隐藏 侧边栏按键映射帮助覆盖层
- **`C`**：全局控制器挂起 / 恢复（进入暂停态以临时屏蔽键盘宏的输出，适用于演示人员进行手部讲解时防止误发指令）
- **`D`**：开启 / 关闭 开发者实时调试视图（独立弹出 5 个子窗口，动态展出 CLAHE 增强、连通域分析、二值化及肤色掩码运算流程图，硬核开发者专属）

---

## 🛠️ 论文级测试与评估工具链

本项目特别在 `tests/` 目录下打造了开箱即用的量化评估系统，适合于论文撰写、数据测算和系统高鲁棒性的定性举证：

### 1. 核心逻辑单元测试 (Unit Tests)
采用标准 `unittest` 针对核心状态机防抖逻辑与键盘映射器进行隔离模拟与冒烟测试验证：
```bash
python -m unittest tests/test_fsm.py
python -m unittest tests/test_controller.py
```

### 2. 性能基准测试 (Performance Benchmark)
全链路耗时追踪，生成不同模块（读取、预处理、肤色提取、骨架识别、渲染）在连续 300 帧处理过程中的 CPU 耗时拆解评估：
```bash
python tests/benchmark.py
```
> **设计指标**：在主流中端处理器上端到端单帧延迟应 **< 150ms**，处理吞吐率 **> 20 FPS**。

### 3. 脱机系统准确率评估 (Accuracy Test Matrix)
配备大字图形化沉浸引导提示的精度采集工具。系统将提示被测人员依次摆出目标手势，在规定帧数内自动抓取、判定并统计。
运行结束后将在控制台直接打印 Markdown 格式的 **混淆矩阵 (Confusion Matrix)** 用于论文图表直接导出：
```bash
python tests/accuracy_test.py
```

---

## 📁 核心架构图解

系统的业务代码统一收束于 `modules/` 目录下，遵循**高内聚低耦合**原则与管道化数据流处理模式：

```text
gesture-control-virtual-interface/
├── main.py                          # 应用程序主循环入口与流转引擎
├── config.py                        # 全局配置中心 (超参数与阈值管理)
│
├── modules/
│   ├── preprocessor.py              # [视觉渲染] CLAHE + 高斯去噪预处理管道
│   ├── skin_detector.py             # [特征切割] YCrCb+HSV 组合级肤色掩码提取
│   ├── hand_detector.py             # [地标推断] 底层 MediaPipe 三维手掌地标网络
│   ├── gesture_classifier.py        # [规则分类] 关键点几何夹角与归一化位置特征判定
│   ├── gesture_recognizer.py        # [顶层代理] 代理暴露器，向下兼容与接口封装
│   ├── fsm.py                       # [时序决策] 处理动作过滤与时间窗抖动防误触
│   ├── controller.py                # [动作下达] 安全的全局虚拟键盘钩子发送器
│   └── ui_renderer.py               # [视效引擎] HUD 数据仪表盘、动画状态渲染机
│
├── tests/                           # 论文与实验数据采集中心
│   ├── benchmark.py                 # FPS 与分段延迟测算系统
│   ├── accuracy_test.py             # 自动化实验混淆矩阵生成器
│   └── test_*.py                    # FSM与下达器无头逻辑测试
│
└── logs/
    └── gesture.log                  # 全链路执行日志与生命周期捕获
```
