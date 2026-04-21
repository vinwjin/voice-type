"""
Audio recording module using sounddevice.
Records mono 16kHz PCM audio from default microphone.
"""

import threading
import numpy as np
from typing import Optional
import sounddevice as sd


class AudioRecorder:
    """
    Records audio from the default input device.
    Uses a ring buffer for continuous recording, extracts on stop.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1, dtype: str = "int16"):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype

        self._frames: list[np.ndarray] = []
        self._recording = False
        self._stream: Optional[sd.InputStream] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start recording in a background thread."""
        if self._recording:
            return

        self._frames = []
        self._recording = True

        def callback(indata: np.ndarray, frames: int, time, status: sd.CallbackFlags) -> None:
            if status:
                # Log but don't stop for minor dropouts
                pass
            with self._lock:
                if self._recording:
                    # Copy to avoid the buffer being reused
                    self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            blocksize=1024,
            device=None,  # default input
            callback=callback,
        )
        self._stream.start()
        self._thread = threading.current_thread()

    def stop(self) -> np.ndarray:
        """
        Stop recording and return the full audio as a numpy array.
        Returns dtype=int16 mono audio.
        """
        with self._lock:
            self._recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._frames:
            return np.array([], dtype=np.int16)

        audio = np.concatenate(self._frames)
        # Flatten if multi-channel
        if audio.ndim > 1:
            audio = audio[:, 0]
        return audio.astype(np.int16)

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._recording
