"""
Configuration management for VoiceType.
Loads settings from config.yaml and environment variables.
"""

import os
import platform
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


DEFAULT_CONFIG = {
    "hotkey": "alt+v",
    "model_size": "small",      # small | base
    "clipboard_protection": True,
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
        "dtype": "int16",
    },
    "logging": {
        "level": "INFO",
    },
    "model_path": None,         # None = download default
    " Ollama": {
        "enabled": False,
        "base_url": "http://localhost:11434",
        "model": "whisper-base",
    },
}


@dataclass
class Config:
    hotkey: str = "alt+v"
    model_size: str = "small"
    clipboard_protection: bool = True
    sample_rate: int = 16000
    channels: int = 1
    audio_dtype: str = "int16"
    log_level: str = "INFO"
    model_path: Optional[str] = None
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "whisper-base"

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from config.yaml or use defaults."""
        cfg = cls()

        # Allow environment variable overrides
        if os.environ.get("VOICE_TYPE_HOTKEY"):
            cfg.hotkey = os.environ["VOICE_TYPE_HOTKEY"]
        if os.environ.get("VOICE_TYPE_MODEL_SIZE"):
            cfg.model_size = os.environ["VOICE_TYPE_MODEL_SIZE"]
        if os.environ.get("VOICE_TYPE_CLIPBOARD_PROTECTION"):
            val = os.environ["VOICE_TYPE_CLIPBOARD_PROTECTION"].lower()
            cfg.clipboard_protection = val in ("1", "true", "yes")
        if os.environ.get("VOICE_TYPE_OLLAMA_ENABLED"):
            val = os.environ["VOICE_TYPE_OLLAMA_ENABLED"].lower()
            cfg.ollama_enabled = val in ("1", "true", "yes")
        if os.environ.get("VOICE_TYPE_OLLAMA_URL"):
            cfg.ollama_base_url = os.environ["VOICE_TYPE_OLLAMA_URL"]

        return cfg


@dataclass
class AppPaths:
    """Platform-aware paths."""
    config_dir: Path
    model_cache_dir: Path
    log_dir: Path
    temp_dir: Path

    @classmethod
    def discover(cls) -> "AppPaths":
        if platform.system() != "Windows":
            raise RuntimeError("VoiceType is designed for Windows only")

        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        root = base / "VoiceType"

        return cls(
            config_dir=root / "config",
            model_cache_dir=root / "models",
            log_dir=root / "logs",
            temp_dir=root / "temp",
        )
