"""
Speech-to-text transcription using faster-whisper.
Runs locally on CPU/GPU, no internet required.
"""

import os
from pathlib import Path
from typing import Optional
import numpy as np


class TranscriptionError(Exception):
    """Raised when transcription fails."""
    pass


class Transcriber:
    """
    Handles speech-to-text using faster-whisper.
    Downloads small model on first run if not cached.
    """

    def __init__(self, model_size: str = "small", model_path: Optional[str] = None):
        self.model_size = model_size
        self.model_path = model_path
        self._model = None

    def _load_model(self):
        """Lazy-load the whisper model."""
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise TranscriptionError(
                "faster-whisper not installed. Run: pip install faster-whisper"
            )

        # faster-whisper auto-downloads to ~/.cache/huggingface/...
        compute_type = "float16"  # use float16 for GPU; change to "int8" for CPU-only

        try:
            self._model = WhisperModel(
                self.model_size,
                device="auto",        # auto-select GPU/CPU
                compute_type=compute_type,
                download_root=self.model_path,
            )
        except Exception as e:
            raise TranscriptionError(f"Failed to load whisper model: {e}")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio array to text.
        audio: int16 numpy array, mono, 16kHz
        Returns: transcribed text string
        """
        self._load_model()

        try:
            segments, info = self._model.transcribe(
                audio,
                language=None,        # auto-detect
                beam_size=5,
                vad_filter=True,       # voice activity detection
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            # Collect all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            result = " ".join(text_parts)
            return result.strip()

        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}")

    def transcribe_file(self, audio_path: str | Path) -> str:
        """Transcribe a local audio file."""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise TranscriptionError("faster-whisper not installed")

        try:
            # For file transcription we can use the utility directly
            import tempfile
            import numpy as np
            import soundfile as sf

            audio, sr = sf.read(str(audio_path), dtype="int16")
            if audio.ndim > 1:
                audio = audio[:, 0]

            return self.transcribe(audio, sr)
        except Exception as e:
            raise TranscriptionError(f"File transcription failed: {e}")


class OllamaTranscriber(Transcriber):
    """
    Optional Ollama backend for transcription.
    Uses Ollama's Whisper API endpoint if user prefers Ollama.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "whisper-base"):
        self.base_url = base_url
        self.model = model
        self._session = None

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        import requests
        import base64
        import io
        import numpy as np

        # Convert int16 audio to WAV bytes
        wav_buffer = io.BytesIO()
        import soundfile as sf
        sf.write(wav_buffer, audio, sample_rate, format="WAV")
        wav_bytes = wav_buffer.getvalue()
        b64_audio = base64.b64encode(wav_bytes).decode()

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"AUDIO_BASE64:{b64_audio}",
                    "stream": False,
                },
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
            return result.get("response", "").strip()
        except requests.RequestException as e:
            raise TranscriptionError(f"Ollama transcription failed: {e}")
