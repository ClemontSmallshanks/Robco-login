import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtCore import QUrl
from app.system.audio import AudioPlayer
from app.config.defaults import AppConfig

@pytest.fixture
def mock_multimedia(monkeypatch):
    monkeypatch.setattr('app.system.audio.HAS_MULTIMEDIA', True)
    
    mock_effect = MagicMock()
    mock_player = MagicMock()
    mock_output = MagicMock()
    
    monkeypatch.setattr('app.system.audio.QSoundEffect', MagicMock(return_value=mock_effect))
    monkeypatch.setattr('app.system.audio.QMediaPlayer', MagicMock(return_value=mock_player))
    monkeypatch.setattr('app.system.audio.QAudioOutput', MagicMock(return_value=mock_output))
    
    return mock_effect, mock_player, mock_output

def test_audio_initialization(mock_multimedia, tmp_path, monkeypatch):
    mock_effect, mock_player, mock_output = mock_multimedia
    config = AppConfig()
    
    # Mock the audio directory so we can control what files exist
    monkeypatch.setattr(AudioPlayer, "__init__", lambda self, cfg, parent=None: None)
    audio = AudioPlayer(config)
    audio._config = config
    audio._parent = None
    audio._effects = {}
    audio._ambience_player = None
    audio._audio_output = None
    audio._audio_dir = tmp_path
    audio._last_key_time = 0
    audio._key_cooldown = 0
    audio._mappings = {
        "menu_nav": ["menu/nav.wav"],
        "ambience_terminal": ["ambience/terminal_lp.wav"]
    }
    
    # Create fake files
    (tmp_path / "menu").mkdir()
    (tmp_path / "menu" / "nav.wav").touch()
    
    audio._load_sounds()
    
    assert "menu_nav" in audio._effects
    assert len(audio._effects["menu_nav"]) == 1

def test_missing_asset_handling(mock_multimedia, tmp_path, monkeypatch):
    mock_effect, mock_player, mock_output = mock_multimedia
    config = AppConfig()
    
    monkeypatch.setattr(AudioPlayer, "__init__", lambda self, cfg, parent=None: None)
    audio = AudioPlayer(config)
    audio._config = config
    audio._parent = None
    audio._effects = {}
    audio._audio_dir = tmp_path
    audio._mappings = {
        "menu_nav": ["menu/missing.wav"],
    }
    
    audio._load_sounds()
    
    # Empty list because the file didn't exist
    assert len(audio._effects["menu_nav"]) == 0
    
    # Playing missing sound shouldn't crash
    audio.play("menu_nav")
    audio.play("invalid_key")

def test_sound_disabled(mock_multimedia):
    mock_effect, mock_player, mock_output = mock_multimedia
    config = AppConfig()
    config.audio.enabled = False
    
    audio = AudioPlayer(config)
    audio._effects = {"menu_nav": [mock_effect]}
    
    audio.play("menu_nav")
    mock_effect.play.assert_not_called()

def test_volume_handling(mock_multimedia):
    mock_effect, mock_player, mock_output = mock_multimedia
    config = AppConfig()
    config.audio.volume = 0.5
    
    audio = AudioPlayer(config)
    audio._effects = {"menu_nav": [mock_effect]}
    audio._audio_output = mock_output
    
    audio.update_volume()
    mock_effect.setVolume.assert_called_with(0.5)
    mock_output.setVolume.assert_called_with(0.25) # Ambience is half volume

def test_randomized_key_sound_selection(mock_multimedia, monkeypatch):
    mock_effect1 = MagicMock()
    mock_effect2 = MagicMock()
    
    config = AppConfig()
    audio = AudioPlayer(config)
    audio._effects = {"terminal_key": [mock_effect1, mock_effect2]}
    audio._last_key_time = 0
    audio._key_cooldown = 0
    
    # Mock random.choice to always pick the first one
    monkeypatch.setattr('app.system.audio.random.choice', lambda x: x[0])
    audio.play("terminal_key")
    mock_effect1.play.assert_called_once()
    mock_effect2.play.assert_not_called()

def test_no_multimedia_fails_gracefully(monkeypatch):
    # Simulate missing QtMultimedia
    monkeypatch.setattr('app.system.audio.HAS_MULTIMEDIA', False)
    config = AppConfig()
    audio = AudioPlayer(config)
    
    # Play should return silently
    audio.play("menu_nav")
    audio.update_volume()
    audio.stop_ambience()
