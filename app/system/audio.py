"""Audio playback for terminal events using QSoundEffect and QMediaPlayer."""

import random
import time
from pathlib import Path
from PyQt6.QtCore import QUrl
try:
    from PyQt6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False
    
from app.config.defaults import AppConfig


class AudioPlayer:
    """Handles playback of terminal sound effects and ambience."""

    def __init__(self, config: AppConfig, parent=None):
        self._config = config
        self._parent = parent
        self._effects = {}  # dict[str, QSoundEffect]
        self._ambience_player = None
        self._audio_output = None
        self._audio_dir = Path(__file__).resolve().parent.parent.parent / "app" / "assets" / "audio"
        
        self._last_key_time = 0.0
        self._key_cooldown = 0.04  # 40ms cooldown for rapid typing
        
        # Mappings from logical names to paths (relative to assets/audio)
        self._mappings = {
            "menu_nav": ["menu/nav.wav"],
            "menu_select": ["menu/ok.wav"],
            "menu_cancel": ["menu/cancel.wav"],
            "terminal_boot": ["terminal/boot.wav"],
            "terminal_key": ["terminal/key_01.wav", "terminal/key_02.wav", "terminal/key_03.wav"],
            "hacking_enter": ["hacking/enter.wav"],
            "hacking_dud": ["hacking/dud.wav"],
            "hacking_bracket": ["hacking/bracket.wav"],
            "hacking_success": ["hacking/success.wav"],
            "hacking_failure": ["hacking/failure.wav"],
            "access_granted": ["system/unlock.wav"],
            "access_denied": ["hacking/failure.wav"],
            "lockout": ["system/alarm.wav"],
            "ambience_terminal": ["ambience/terminal_lp.wav"]
        }

        if HAS_MULTIMEDIA:
            self._load_sounds()
            if self._config.audio.enabled and self._config.audio.terminal_ambience:
                self._start_ambience()

    def _load_sounds(self) -> None:
        """Preload short UI sounds."""
        if not self._audio_dir.exists():
            return

        for logical_name, paths in self._mappings.items():
            if logical_name.startswith("ambience"):
                continue  # Ambience is handled by QMediaPlayer
            
            self._effects[logical_name] = []
            for path_str in paths:
                wav_file = self._audio_dir / path_str
                if wav_file.exists():
                    effect = QSoundEffect(self._parent)
                    effect.setSource(QUrl.fromLocalFile(str(wav_file)))
                    effect.setVolume(self._config.audio.volume)
                    self._effects[logical_name].append(effect)

    def play(self, logical_name: str) -> None:
        """Play a loaded sound effect by logical name."""
        if not self._config.audio.enabled or not self._config.audio.terminal_sfx or not HAS_MULTIMEDIA:
            return
            
        effects = self._effects.get(logical_name)
        if not effects:
            return

        if logical_name == "terminal_key":
            now = time.time()
            if now - self._last_key_time < self._key_cooldown:
                return
            self._last_key_time = now
            
        effect = random.choice(effects)
        if effect.isPlaying():
            effect.stop()
        effect.play()

    def _start_ambience(self) -> None:
        """Start the looping background ambience."""
        ambience_path = self._audio_dir / self._mappings["ambience_terminal"][0]
        if not ambience_path.exists():
            return
            
        self._audio_output = QAudioOutput(self._parent)
        self._audio_output.setVolume(self._config.audio.volume * 0.5) # Subdued ambience
        
        self._ambience_player = QMediaPlayer(self._parent)
        self._ambience_player.setAudioOutput(self._audio_output)
        self._ambience_player.setSource(QUrl.fromLocalFile(str(ambience_path)))
        self._ambience_player.setLoops(QMediaPlayer.Loops.Infinite)
        self._ambience_player.play()

    def stop_ambience(self) -> None:
        """Stop the background ambience."""
        if self._ambience_player:
            self._ambience_player.stop()

    def update_volume(self) -> None:
        """Apply volume changes to all loaded effects and ambience."""
        if not HAS_MULTIMEDIA:
            return
            
        vol = self._config.audio.volume
        for effects_list in self._effects.values():
            for effect in effects_list:
                effect.setVolume(vol)
                
        if self._audio_output:
            self._audio_output.setVolume(vol * 0.5)
            
        if self._ambience_player:
            if self._config.audio.enabled and self._config.audio.terminal_ambience:
                if self._ambience_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                    self._ambience_player.play()
            else:
                self._ambience_player.stop()
