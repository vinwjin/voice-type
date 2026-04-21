# VoiceType for Windows

> 按住 `Alt+V` 说话 → 自动打字进任意输入框

## 功能特性

| 特性 | 说明 |
|------|------|
| 🎤 全局热键 | `Alt+V` 触发，在任何应用都生效，无需管理员权限 |
| 🔇 本地 STT | 使用 `faster-whisper` 模型，全部离线运行，不上传任何数据 |
| 📋 自动打字 | 录音 → 转文字 → 自动粘贴到当前焦点窗口 |
| 🛡️ 剪贴板保护 | 录音前自动保存剪贴板内容，完成后恢复 |
| 🖥️ 悬浮状态条 | Xbox Game Bar 风格半透明悬浮条，显示当前状态 |
| 🟢 系统托盘 | 常驻托盘，图标颜色实时反映状态 |

## 系统要求

- Windows 10 / Windows 11
- Python 3.10+
- 麦克风

## 安装

### 方式一：直接运行（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/YOUR_USERNAME/voice-type.git
cd voice-type

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 3. 安装依赖
pip install -e .

# 4. 首次运行（自动下载 ~244MB 模型）
python -m voice_type
```

### 方式二：打包为 exe（便携版）

```bash
pip install pyinstaller
pyinstaller --onedir --windowed --name VoiceType --add-data "voice_type;voice_type" voice_type/__main__.py
```

## 使用方法

1. 运行 `voice-type`（或双击 exe）
2. 悬浮条出现在屏幕顶部，显示 "Ready"
3. **按住** `Alt+V` 开始录音，**松开** `Alt+V` 停止录音
4. 文字自动输入到当前焦点窗口（微信、Telegram、浏览器等）

## 配置

可通过环境变量覆盖默认配置：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `VOICE_TYPE_HOTKEY` | `alt+v` | 全局热键 |
| `VOICE_TYPE_MODEL_SIZE` | `small` | whisper 模型大小：`small` 或 `base` |
| `VOICE_TYPE_CLIPBOARD_PROTECTION` | `true` | 启用剪贴板保护 |
| `VOICE_TYPE_OLLAMA_ENABLED` | `false` | 使用 Ollama 代替 faster-whisper |
| `VOICE_TYPE_OLLAMA_URL` | `http://localhost:11434` | Ollama API 地址 |

## 项目结构

```
voice_type/
├── config.py        # 配置管理
├── hotkey.py        # 全局热键（keyboard 库）
├── recorder.py      # 音频录制（sounddevice）
├── transcriber.py   # 语音转文字（faster-whisper）
├── paster.py        # 自动粘贴（Win32 SendInput + 剪贴板）
├── ui.py            # 悬浮状态条（tkinter）
├── main.py          # 主程序入口
└── __init__.py
```

## 技术方案

- **热键**：`keyboard` 库，全局注册，无需 admin
- **录音**：`sounddevice`（纯 Python，WASAPI）
- **STT**：`faster-whisper` small（~244MB，CTranslate2 优化，CPU/GPU 通用）
- **打字**：Win32 `SendInput` 模拟 `Ctrl+V`，最广泛的兼容方案
- **UI**：`tkinter` 悬浮条 + 系统托盘

## License

MIT
