# VoiceType — 需求规格说明书

> 本文档是开发过程中的需求记录、关键决策和可性行验证总结。

---

## 1. 项目背景

**用户需求：** 在 Windows 上寻找一款代替手打字的软件，能够调用本地 Ollama 语音模型，通过键盘快捷键控制录入说话内容，然后在聊天框/输入框内自动输入文字。

**核心诉求：**
- 彻底解放双手，不用手打字
- 语音模型必须本地运行（隐私、离线可用）
- 快捷键触发，在任意应用都能用
- 不依赖特定应用（微信、Telegram、浏览器等通用）

---

## 2. 功能需求

### 2.1 P0 必须（Must Have）

| 需求 | 描述 | 优先级 |
|------|------|--------|
| 全局热键录音 | 按住某个键开始录音，松开停止，无需在软件窗口内操作 | P0 |
| 本地 STT | 使用本地语音识别模型，不上传数据，保护隐私 | P0 |
| 自动打字 | 识别结果自动输入到当前焦点窗口的输入框中 | P0 |
| 任意应用通用 | 微信、Telegram、浏览器、记事本等所有输入场景 | P0 |

### 2.2 P1 应该有（Should Have）

| 需求 | 描述 | 优先级 |
|------|------|--------|
| 悬浮状态条 | 显示当前状态（Ready/Recording/Processing） | P1 |
| 系统托盘 | 常驻托盘，图标颜色反映状态 | P1 |
| 剪贴板保护 | 操作前后保存/恢复剪贴板内容 | P1 |

### 2.3 P2 最好有（Nice to Have）

| 需求 | 描述 | 优先级 |
|------|------|--------|
| Ollama 集成 | 可选使用 Ollama 作为 STT 后端 | P2 |
| 模型大小选择 | base/small 等不同精度模型 | P2 |

---

## 3. 技术方案

### 3.1 关键决策

#### STT 引擎选择

| 方案 | 优点 | 缺点 |
|------|------|------|
| faster-whisper | 本地运行、CPU优化、PyTorch生态 | 模型文件较大（small~140MB） |
| whisper.cpp | 纯C++、极轻量 | Python集成复杂 |
| Ollama | 用户已有、本地运行 | 速度慢、需额外API服务 |
| Vosk | 离线、轻量 | 中文支持一般 |

**结论：采用 `faster-whisper small` 模型**
- 查证确认：sounddevice + faster-whisper 可在 Windows 正常运行
- faster-whisper 无 PyTorch 依赖（用 CTranslate2），打包体积可控
- 模型约 140MB，首次运行自动下载

#### 打包方案选择

| 方案 | 问题 |
|------|------|
| PyInstaller + PyTorch | exe 体积 2GB+，实测打包失败 |
| PyInstaller + faster-whisper | 体积约 300-500MB，可接受 ✅ |
| Nuitka | 未验证 |

**结论：采用 PyInstaller + faster-whisper**

#### 自动打字方案（三层降级）

| 层级 | 方案 | 适用场景 |
|------|------|----------|
| L1 | UI Automation SetValue | 有辅助功能 API 的应用（UWP、部分 Electron） |
| L2 | WM_SETTEXT | 标准 Win32 Edit/Control |
| L3 | SendInput Ctrl+V | 剪贴板+模拟粘贴，最广泛兼容 |

**结论：L3 作为主要方案（L1/L2 作为增强）**
- 查证确认：`uiautomation.SetValue()` 可用于 EditControl
- 剪贴板方案已知有风险，所以加了剪贴板保护

#### 热键方案

| 方案 | 管理员权限 | 结论 |
|------|-----------|------|
| keyboard 库 | 不需要 | ✅ 选这个 |
| pynput | 不需要 | 备选 |
| Win32 RegisterHotKey | 需要 | 不用 |

**查证确认：`keyboard` 库全局热键不需要管理员权限，可绑定 Alt+V**

### 3.2 技术栈

```
录音:       sounddevice (pure Python, WASAPI)
STT:        faster-whisper small (~140MB, CTranslate2)
热键:       keyboard (全局, 不需admin)
打字:       pywin32 (SendInput/Ctrl+V) + uiautomation (SetValue)
UI:         tkinter (悬浮条) + pystray (系统托盘)
打包:       PyInstaller --onefile --windowed
```

---

## 4. 已知问题与限制

1. **PyInstaller 打包体积**：约 300-500MB，比一般工具大
2. **首次下载模型**：需要网络下载 ~140MB 模型文件
3. **剪贴板污染**：L3 方案会修改剪贴板，已做保护但仍有边界情况
4. **非英文识别**：faster-whisper small 模型中文识别尚可，但不是最优

---

## 5. GitHub 发布流程

```bash
# 1. 代码推送
git push origin master:main

# 2. 打 tag 触发 CI
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# 3. GitHub Actions 自动：
#    - 安装依赖
#    - PyInstaller 打包
#    - softprops/action-gh-release 上传 exe 到 Release

# 4. 用户下载
https://github.com/vinwjin/voice-type/releases/download/vX.Y.Z/VoiceType.exe
```

### CI 权限配置

`softprops/action-gh-release` 需要 `permissions: contents: write`，否则 403。

---

## 6. 验收标准

- [ ] Alt+V 按住录音，松开后文字自动出现在微信/Telegram 输入框
- [ ] 全局热键在任意应用都生效（不需要管理员权限）
- [ ] 完全离线运行（首次下载模型后）
- [ ] 悬浮条状态正确显示（Ready/Recording/Processing）
- [ ] 剪贴板内容在操作后恢复
- [ ] exe 体积不超过 600MB
