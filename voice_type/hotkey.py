"""
Global hotkey management using keyboard library.
Registers Alt+V as the voice typing trigger.
"""

import threading
import time
from typing import Callable, Optional


class HotkeyManager:
    """
    Manages global hotkey registration and callback dispatch.
    Uses 'keyboard' library for cross-app hotkey support on Windows.
    No admin privileges required.
    """

    def __init__(self, hotkey: str = "alt+v"):
        self.hotkey = hotkey
        self._pressed = False
        self._callback: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()

    def start(self, callback: Callable[[], None]) -> None:
        """
        Register the global hotkey and call callback on press.
        Non-blocking - runs hotkey listener in background thread.
        """
        import keyboard

        self._callback = callback

        def on_press(e: keyboard.KeyboardEvent) -> None:
            if e.name.lower() == self.hotkey.replace("alt+", "").replace("ctrl+", "").replace("shift+", ""):
                if e.event_type == keyboard.KEY_DOWN:
                    with self._lock:
                        was_pressed = self._pressed
                        self._pressed = True
                    if not was_pressed and self._callback:
                        try:
                            self._callback()
                        except Exception:
                            pass

                elif e.event_type == keyboard.KEY_UP:
                    with self._lock:
                        self._pressed = False

        # Register as blocking listener
        keyboard.on_press(on_press)
        # Block so the thread stays alive
        keyboard.wait(self.hotkey, suppress=True)

    def stop(self) -> None:
        """Unregister all hotkeys."""
        import keyboard
        keyboard.unhook_all()

    def is_pressed(self) -> bool:
        with self._lock:
            return self._pressed
