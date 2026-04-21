"""
Auto-paste module: copies transcribed text to clipboard and simulates Ctrl+V
using Win32 SendInput API to type into the active window.

This is the most compatible way to inject text into arbitrary applications
on Windows, including WeChat, Telegram, browser inputs, etc.
"""

import ctypes
import ctypes.wintypes as wintypes
import time
from typing import Optional

import pyperclip


# Win32 constants
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_V = 0x56
VK_SHIFT = 0x10
VK_LEFT = 0x25

# Clipboard notification messages
WM_CLIPBOARDUPDATE = 0x031D


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", _KEYBDINPUT),
        ("mi", _MOUSEINPUT),
    ]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


user32 = ctypes.windll.user32


def _send_key(vk: int, flags: int = 0) -> None:
    """Send a single key event using Win32 SendInput."""
    inp = _INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = 0
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = None
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def _ctrl_v() -> None:
    """Simulate Ctrl+V (paste) using SendInput."""
    _send_key(VK_CONTROL)                  # Ctrl down
    _send_key(VK_V)                         # V down
    _send_key(VK_V, KEYEVENTF_KEYUP)       # V up
    _send_key(VK_CONTROL, KEYEVENTF_KEYUP)  # Ctrl up


class ClipboardProtection:
    """
    Saves the clipboard content before recording and restores it afterwards.
    Only activates when clipboard_protection is enabled.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._saved: Optional[str] = None

    def save(self) -> None:
        """Save current clipboard content."""
        if not self.enabled:
            return
        try:
            self._saved = pyperclip.paste()
        except Exception:
            self._saved = None

    def restore(self) -> None:
        """Restore saved clipboard content."""
        if not self.enabled or self._saved is None:
            return
        try:
            pyperclip.copy(self._saved)
        except Exception:
            pass
        finally:
            self._saved = None


class TextPaster:
    """
    Pastes transcribed text into the active window using Ctrl+V.
    Handles clipboard protection automatically.
    """

    def __init__(self, clipboard_protection: bool = True):
        self.clipboard_protection_obj = ClipboardProtection(clipboard_protection)

    def paste_text(self, text: str) -> None:
        """
        Copy text to clipboard and paste into active window via Ctrl+V.
        Restores original clipboard content after pasting if protection is enabled.
        """
        # Save clipboard before we overwrite it
        self.clipboard_protection_obj.save()

        try:
            # Copy to clipboard
            pyperclip.copy(text)
            time.sleep(0.05)  # Small delay for clipboard to settle

            # Simulate Ctrl+V
            _ctrl_v()

            # No extra wait needed - paste happens synchronously
        finally:
            # Restore original clipboard if protection is enabled
            self.clipboard_protection_obj.restore()


def paste_text(text: str, clipboard_protection: bool = True) -> None:
    """
    Convenience function: paste text into the active window.
    Handles clipboard protection automatically.
    """
    paster = TextPaster(clipboard_protection=clipboard_protection)
    paster.paste_text(text)
