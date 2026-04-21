"""
UI module: Tkinter-based overlay window + system tray.
Provides a compact status bar and system tray icon for VoiceType.
"""

import threading
import sys
from enum import Enum
from typing import Optional

import tkinter as tk
import pystray
from PIL import Image, ImageDraw


class State(Enum):
    READY = "ready"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    DONE = "done"
    ERROR = "error"


# Overlay bar colors
STATE_COLORS = {
    State.READY: "#808080",        # gray
    State.RECORDING: "#FF4444",    # red
    State.TRANSCRIBING: "#4488FF",  # blue
    State.DONE: "#44BB44",         # green
    State.ERROR: "#FF8800",        # orange
}

# Tray icon colors (RGB tuples)
TRAY_COLORS = {
    State.READY: (128, 128, 128),
    State.RECORDING: (255, 68, 68),
    State.TRANSCRIBING: (68, 136, 255),
    State.DONE: (68, 187, 68),
    State.ERROR: (255, 136, 0),
}


class OverlayWindow:
    """
    A compact, semi-transparent, always-on-top floating bar
    showing the current VoiceType state. Draggable.
    Can be shown/hidden without destroying the window.
    """

    def __init__(self, on_close=None):
        self.on_close = on_close
        self.state = State.READY
        self._visible = True

        # Build the window
        self.root = tk.Tk()
        self.root.overrideredirect(True)          # no decorations
        self.root.attributes("-topmost", True)     # always on top
        self.root.attributes("-alpha", 0.9)        # semi-transparent
        self.root.configure(bg="#1e1e2e")

        # Make window draggable
        self._drag_data = {"x": 0, "y": 0}

        title_bar = tk.Frame(self.root, bg="#1e1e2e", cursor="fleur")
        title_bar.pack(fill="x")
        title_bar.bind("<Button-1>", self._on_drag_start)
        title_bar.bind("<B1-Motion>", self._on_drag_motion)

        # Close button — hide instead of destroy (let tray manage exit)
        close_btn = tk.Label(
            title_bar, text="✕", bg="#1e1e2e", fg="#aaaaaa",
            font=("Segoe UI", 10), cursor="hand2", padx=8
        )
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.hide())

        # Title label
        self.title_label = tk.Label(
            title_bar, text="🎤 VoiceType",
            bg="#1e1e2e", fg="#ffffff",
            font=("Segoe UI", 11, "bold"), pady=6, padx=10
        )
        self.title_label.pack(side="left")

        # Status label
        self.status_label = tk.Label(
            self.root, text="Ready — Press Alt+V",
            bg="#1e1e2e", fg=STATE_COLORS[State.READY],
            font=("Segoe UI", 10), pady=4, padx=10
        )
        self.status_label.pack(fill="x")

        # Position at top-center of screen
        self.root.update_idletasks()
        w = 320
        h = 60
        x = (self.root.winfo_screenwidth() - w) // 2
        y = 20
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag_motion(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    def show(self) -> None:
        """Show the overlay window."""
        if self._visible:
            return
        self.root.deiconify()
        self._visible = True

    def hide(self) -> None:
        """Hide the overlay window (don't destroy)."""
        if not self._visible:
            return
        self.root.withdraw()
        self._visible = False

    def is_visible(self) -> bool:
        return self._visible

    def set_state(self, state: State, message: Optional[str] = None) -> None:
        """Update the displayed state and message."""
        self.state = state
        color = STATE_COLORS[state]
        msg = message or {
            State.READY: "Ready — Press Alt+V",
            State.RECORDING: "🔴 Recording... Release Alt+V to stop",
            State.TRANSCRIBING: "🔵 Transcribing...",
            State.DONE: "✅ Done! Text pasted.",
            State.ERROR: f"❌ Error: {message or 'unknown'}",
        }[state]

        def _update():
            self.status_label.config(text=msg, fg=color)

        try:
            self.root.after(0, _update)
        except Exception:
            pass

    def run(self) -> None:
        """Start the Tkinter main loop (blocking)."""
        self.root.mainloop()


class TrayManager:
    """
    System tray icon for VoiceType.
    Allows show/hide of the overlay window and clean exit.
    """

    def __init__(self, overlay: OverlayWindow):
        self._overlay = overlay
        self._state = State.READY
        self._icon: Optional[pystray.Icon] = None
        self._hidden_by_close = False

    def _create_image(self, color: tuple) -> Image.Image:
        """Create a solid-color circular icon image."""
        img = Image.new("RGB", (64, 64), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, 60, 60], fill=color)
        return img

    def _on_click(self, icon: pystray.Icon, event) -> None:
        """Toggle overlay visibility on left click."""
        if self._overlay.is_visible():
            self._overlay.hide()
        else:
            self._overlay.show()
        self._update_menu()

    def _on_show_hide(self, icon=None, event=None) -> None:
        """Show/hide from menu item."""
        if self._overlay.is_visible():
            self._overlay.hide()
        else:
            self._overlay.show()
        self._update_menu()

    def _on_quit(self, icon=None, event=None) -> None:
        """Quit the entire application."""
        if self._icon:
            self._icon.stop()
        try:
            self._overlay.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def _update_menu(self) -> None:
        if not self._icon:
            return
        is_visible = self._overlay.is_visible()
        label = "隐藏悬浮条" if is_visible else "显示悬浮条"
        self._icon.menu = pystray.Menu(
            pystray.MenuItem(label, self._on_show_hide),
            pystray.MenuItem("退出", self._on_quit),
        )

    def set_state(self, state: State) -> None:
        """Update tray icon color to reflect current state."""
        self._state = state
        if self._icon:
            color = TRAY_COLORS[state]
            self._icon.image = self._create_image(color)
            self._update_menu()

    def start(self) -> None:
        """Start the tray icon (non-blocking, runs in background thread)."""
        color = TRAY_COLORS[self._state]
        self._icon = pystray.Icon(
            "voice_type",
            self._create_image(color),
            "VoiceType",
            pystray.Menu(
                pystray.MenuItem("显示/隐藏悬浮条", self._on_show_hide),
                pystray.MenuItem("退出", self._on_quit),
            ),
        )
        threading.Thread(target=self._icon.run, daemon=True, name="tray").start()
