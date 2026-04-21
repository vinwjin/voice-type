"""
UI module: Tkinter-based overlay window + system tray.
Provides a compact status bar and system tray icon for VoiceType.
"""

import tkinter as tk
import threading
import sys
import platform
from enum import Enum
from typing import Optional


class State(Enum):
    READY = "ready"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    DONE = "done"
    ERROR = "error"


STATE_COLORS = {
    State.READY: "#808080",       # gray
    State.RECORDING: "#FF4444",   # red
    State.TRANSCRIBING: "#4488FF", # blue
    State.DONE: "#44BB44",        # green
    State.ERROR: "#FF8800",       # orange
}


class OverlayWindow:
    """
    A compact, semi-transparent, always-on-top floating bar
    showing the current VoiceType state. Draggable.
    """

    def __init__(self, on_close=None):
        self.on_close = on_close
        self.state = State.READY

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

        # Close button
        close_btn = tk.Label(
            title_bar, text="✕", bg="#1e1e2e", fg="#aaaaaa",
            font=("Segoe UI", 10), cursor="hand2", padx=8
        )
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self._handle_close())

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

    def _handle_close(self):
        if self.on_close:
            self.on_close()
        self.root.destroy()

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
