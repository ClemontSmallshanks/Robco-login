"""Audio playback for terminal events using QSoundEffect."""

from pathlib import Path
from PyQt6.QtCore import QUrl
try:
    from PyQt6.QtMultimedia import QSoundEffect
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False
    
from app.config.defaults import AppConfig


class AudioPlayer:
    """Handles playback of terminal sound effects."""

    def __init__(self, config: AppConfig):
        self._config = config
        self._effects = {}  # dict[str, Any]
        self._audio_dir = Path(__file__).resolve().parent.parent.parent / "assets" / "audio"
        
        if config.audio.enabled and HAS_MULTIMEDIA:
            self._load_sounds()

    def _load_sounds(self) -> None:
        """Load available WAV files from the assets directory."""
        if not self._audio_dir.exists():
            self._audio_dir.mkdir(parents=True, exist_ok=True)
            
        # Expected files:
        # ui_terminal_boot.wav
        # ui_terminal_keypress.wav
        # ui_terminal_password_correct.wav
        # ui_terminal_password_incorrect.wav
        # ui_terminal_lockout.wav
        
        for wav_file in self._audio_dir.glob("*.wav"):
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(wav_file)))
            effect.setVolume(self._config.audio.volume)
            self._effects[wav_file.stem] = effect

    def play(self, sound_name: str) -> None:
        """Play a loaded sound effect by name (e.g. 'ui_terminal_boot')."""
        if not self._config.audio.enabled or not HAS_MULTIMEDIA:
            return
            
        effect = self._effects.get(sound_name)
        if effect:
            if effect.isPlaying():
                effect.stop()
            effect.play()

    def update_volume(self) -> None:
        """Apply volume changes to all loaded effects."""
        vol = self._config.audio.volume
        for effect in self._effects.values():
            effect.setVolume(vol)
