#!/usr/bin/env python3
"""
VoiceType v2.0 — Main entry point
Global hotkey: Alt+V
Features: faster-whisper local STT, auto-paste, clipboard protection
"""

import sys
import os
import threading
import time
import traceback
import logging
from pathlib import Path
from typing import Optional

# Ensure we're running on Windows
if sys.platform != "win32":
    print("ERROR: VoiceType is designed for Windows only.")
    print(f"Current platform: {sys.platform}")
    sys.exit(1)

# Ensure Python 3.10+
if sys.version_info < (3, 10):
    print("ERROR: Python 3.10+ required.")
    sys.exit(1)

from voice_type.config import Config
from voice_type.recorder import AudioRecorder
from voice_type.transcriber import Transcriber, OllamaTranscriber, TranscriptionError
from voice_type.paster import TextPaster
from voice_type.ui import OverlayWindow, State, TrayManager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("voice_type")


class VoiceTypeApp:
    """
    Main application class that orchestrates:
    hotkey → recorder → transcriber → paster → UI update
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.recorder = AudioRecorder(
            sample_rate=cfg.sample_rate,
            channels=cfg.channels,
            dtype=cfg.audio_dtype,
        )
        self.paster = TextPaster(clipboard_protection=cfg.clipboard_protection)

        if cfg.ollama_enabled:
            self.transcriber = OllamaTranscriber(
                base_url=cfg.ollama_base_url,
                model=cfg.ollama_model,
            )
            log.info("Using Ollama backend at %s", cfg.ollama_base_url)
        else:
            self.transcriber = Transcriber(
                model_size=cfg.model_size,
                model_path=cfg.model_path,
            )
            log.info("Using faster-whisper (%s model)", cfg.model_size)

        self.overlay: Optional[OverlayWindow] = None
        self.tray: Optional[TrayManager] = None
        self._hotkey_thread: Optional[threading.Thread] = None
        self._running = False

    def _update_state(self, state: State, message: Optional[str] = None) -> None:
        """Update both overlay and tray icon to reflect current state."""
        self.overlay.set_state(state, message)
        if self.tray:
            self.tray.set_state(state)

    def _hotkey_loop(self) -> None:
        """Background thread that listens for Alt+V presses."""
        import keyboard

        log.info("Hotkey listener started (Alt+V)")

        while self._running:
            try:
                # Block until Alt+V is pressed
                keyboard.wait("alt+v", suppress=True)
                if not self._running:
                    break

                # Alt+V pressed — start/stop toggle
                self._on_hotkey_pressed()

                # Debounce: wait for key release
                time.sleep(0.3)

            except Exception as e:
                log.error("Hotkey loop error: %s", e)
                time.sleep(1)

    def _on_hotkey_pressed(self) -> None:
        """Handle Alt+V press — toggle recording state."""
        if self.recorder.is_recording:
            # Stop recording and process
            self._stop_and_paste()
        else:
            # Start recording
            self._start_recording()

    def _start_recording(self) -> None:
        """Start audio recording."""
        log.info("Recording started")
        self._update_state(State.RECORDING)
        try:
            self.recorder.start()
        except Exception as e:
            log.error("Failed to start recording: %s", e)
            self._update_state(State.ERROR, str(e))

    def _stop_and_paste(self) -> None:
        """Stop recording, transcribe, and paste the result."""
        log.info("Recording stopped, transcribing...")
        self._update_state(State.TRANSCRIBING)

        try:
            audio = self.recorder.stop()
            if len(audio) == 0:
                log.warning("No audio recorded")
                self._update_state(State.READY)
                return

            log.info("Audio duration: %.1fs", len(audio) / self.cfg.sample_rate)

            # Transcribe
            text = self.transcriber.transcribe(
                audio,
                sample_rate=self.cfg.sample_rate,
            )

            if not text:
                log.warning("Transcription returned empty")
                self._update_state(State.READY)
                return

            log.info("Transcribed: %s", text[:80])

            # Paste into active window
            self._update_state(State.DONE, "Pasting...")
            success = self.paster.paste_text(text)
            if success:
                log.info("Text pasted successfully")
            else:
                log.warning("All paste methods failed — text may not have been inserted")
                self._update_state(State.ERROR, "Paste failed")

            # Brief "done" state, then return to ready
            def reset_state():
                time.sleep(2)
                if self._running:
                    self._update_state(State.READY)

            threading.Thread(target=reset_state, daemon=True).start()

        except TranscriptionError as e:
            log.error("Transcription error: %s", e)
            self._update_state(State.ERROR, str(e))
        except Exception as e:
            log.error("Unexpected error: %s", e)
            traceback.print_exc()
            self._update_state(State.ERROR, str(e))

    def run(self) -> None:
        """Start the application (blocking)."""
        self._running = True
        log.info("VoiceType v2.0 starting...")
        log.info("  Hotkey: %s", self.cfg.hotkey)
        log.info("  Model: %s", self.cfg.model_size)
        log.info("  Clipboard protection: %s", self.cfg.clipboard_protection)

        # Create and start overlay in main thread
        self.overlay = OverlayWindow(on_close=self.stop)
        self._update_state(State.READY)

        # Start system tray
        self.tray = TrayManager(self.overlay)
        self.tray.start()
        log.info("System tray started")

        # Start hotkey listener in background thread
        self._hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self._hotkey_thread.start()

        log.info("VoiceType ready. Press Alt+V to start voice typing.")

        try:
            self.overlay.run()
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Stop the application cleanly."""
        log.info("Shutting down VoiceType...")
        self._running = False

        if self.recorder.is_recording:
            try:
                self.recorder.stop()
            except Exception:
                pass

        if self.overlay:
            try:
                self.overlay.root.destroy()
            except Exception:
                pass

        import keyboard
        keyboard.unhook_all()

        log.info("VoiceType stopped.")


def main() -> None:
    """Entry point."""
    cfg = Config.load()

    try:
        app = VoiceTypeApp(cfg)
        app.run()
    except Exception as e:
        log.error("Fatal error: %s", e)
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
