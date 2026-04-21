"""
Auto-paste module: Three-level fallback text injection for Windows.

Level 1 — UI Automation SetValue:  For UWP / Electron / modern apps with
          accessibility API (VS Code, Slack, Teams, Word Online, etc.)

Level 2 — WM_SETTEXT via pywin32:  For standard Win32 Edit / RichEdit
          controls (Notepad, browser address bars, old Win32 apps).

Level 3 — SendInput Ctrl+V:        Clipboard + simulated paste. Universally
          compatible but clobbers the clipboard (protected).

The paster tries L1 → L2 → L3 in order and stops at the first success.
"""

import ctypes
import ctypes.wintypes as wintypes
import logging
import time
from typing import Optional

import pyperclip
import win32gui
import win32con

log = logging.getLogger("voice_type")


# ─── Win32 constants ───────────────────────────────────────────────────────────

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_V = 0x56

WM_SETTEXT = 0x000C
EM_REPLACESEL = 0x00C2

# ─── SendInput low-level structures ───────────────────────────────────────────

class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",        wintypes.WORD),
        ("wScan",      wintypes.WORD),
        ("dwFlags",    wintypes.DWORD),
        ("time",       wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",         wintypes.c_long),
        ("dy",         wintypes.c_long),
        ("mouseData",  wintypes.DWORD),
        ("dwFlags",    wintypes.DWORD),
        ("time",       wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", _KEYBDINPUT),
        ("mi", _MOUSEINPUT),
    ]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type",  wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


_user32 = ctypes.windll.user32


def _send_key(vk: int, flags: int = 0) -> None:
    """Send a single key event via SendInput."""
    inp = _INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = 0
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = None
    _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def _ctrl_v() -> None:
    """Simulate Ctrl+V using SendInput."""
    _send_key(VK_CONTROL)
    _send_key(VK_V)
    _send_key(VK_V, KEYEVENTF_KEYUP)
    _send_key(VK_CONTROL, KEYEVENTF_KEYUP)


# ─── Level 1: UI Automation ───────────────────────────────────────────────────

def _try_uiautomation(text: str) -> bool:
    """
    Level 1: Use uiautomation SetValue on the focused element.
    Returns True if the app accepted the text, False otherwise.
    """
    try:
        import uiautomation as ua

        # Get the element with keyboard focus
        focus = ua.GetFocusedElement()
        if focus is None:
            return False

        # Try SetValue (works for Edit / TextBox controls in UWP / Electron)
        try:
            focus.SetValue(text)
            log.debug("L1 (UIAutomation) succeeded")
            return True
        except Exception:
            pass

        # Try ValuePattern as fallback
        try:
            vp = focus.GetPattern(ua.ValuePatternId)
            if vp:
                vp.SetValue(text)
                log.debug("L1 (ValuePattern) succeeded")
                return True
        except Exception:
            pass

        return False
    except ImportError:
        log.debug("uiautomation not installed, skipping L1")
        return False
    except Exception as e:
        log.debug("L1 uiautomation failed: %s", e)
        return False


# ─── Level 2: WM_SETTEXT via pywin32 ────────────────────────────────────────

def _try_wm_settext(text: str) -> bool:
    """
    Level 2: Send WM_SETTEXT directly to the focused window's edit control.
    Works for standard Win32 Edit / RichEdit controls.
    Returns True if the message was sent successfully, False otherwise.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False

        # WM_SETTEXT requires a pointer to a null-terminated wide string in memory
        text_ptr = ctypes.wstring_at(text)
        result = _user32.SendMessageW(hwnd, WM_SETTEXT, 0, text_ptr)

        if result == 1:  # 1 = success (MR_RESULT), 0 = failure
            log.debug("L2 (WM_SETTEXT) succeeded on hwnd=%s", hwnd)
            return True

        return False
    except Exception as e:
        log.debug("L2 WM_SETTEXT failed: %s", e)
        return False


# ─── Level 3: Clipboard + Ctrl+V ──────────────────────────────────────────────

def _ctrl_v_fallback(text: str) -> bool:
    """
    Level 3: Copy text to clipboard and simulate Ctrl+V.
    Most universal but modifies the clipboard (protected by ClipboardProtection).
    """
    try:
        pyperclip.copy(text)
        time.sleep(0.05)
        _ctrl_v()
        log.debug("L3 (Ctrl+V) succeeded")
        return True
    except Exception as e:
        log.debug("L3 Ctrl+V failed: %s", e)
        return False


# ─── Clipboard Protection ──────────────────────────────────────────────────────

class ClipboardProtection:
    """
    Saves clipboard content before we overwrite it and restores it afterwards.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._saved: Optional[str] = None

    def save(self) -> None:
        if not self.enabled:
            return
        try:
            self._saved = pyperclip.paste()
        except Exception:
            self._saved = None

    def restore(self) -> None:
        if not self.enabled or self._saved is None:
            return
        try:
            pyperclip.copy(self._saved)
        except Exception:
            pass
        finally:
            self._saved = None


# ─── TextPaster ────────────────────────────────────────────────────────────────

class TextPaster:
    """
    Pastes transcribed text into the active window using three-level fallback:

      L1: UIAutomation SetValue  → UWP / Electron apps
      L2: WM_SETTEXT             → Win32 Edit controls
      L3: Clipboard + Ctrl+V     → universal fallback

    Clipboard protection is automatically applied around the paste operation.
    """

    def __init__(self, clipboard_protection: bool = True):
        self._cp = ClipboardProtection(clipboard_protection)

    def paste_text(self, text: str) -> bool:
        """
        Attempt to paste text using L1 → L2 → L3 fallback.
        Returns True if any level succeeded, False if all failed.
        """
        if not text:
            return False

        # L1: UI Automation
        if _try_uiautomation(text):
            return True

        # L2: WM_SETTEXT
        if _try_wm_settext(text):
            return True

        # L3: Clipboard + Ctrl+V (with protection)
        self._cp.save()
        try:
            success = _ctrl_v_fallback(text)
        finally:
            self._cp.restore()

        return success


# ─── Module-level convenience ─────────────────────────────────────────────────

def paste_text(text: str, clipboard_protection: bool = True) -> bool:
    """
    Convenience function: paste text into the active window with three-level
    fallback and optional clipboard protection.
    Returns True if any level succeeded.
    """
    paster = TextPaster(clipboard_protection=clipboard_protection)
    return paster.paste_text(text)
