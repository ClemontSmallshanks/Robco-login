"""Default configuration values for the RobCo greeter."""

from dataclasses import dataclass, field


@dataclass
class GameConfig:
    min_word_length: int = 7
    max_word_length: int = 10
    num_candidates: int = 12
    initial_attempts: int = 4
    max_attempts: int = 4


@dataclass
class DisplayConfig:
    scheme: str = "green"  # green, amber, blue
    uppercase: bool = True
    crt_effects: bool = True
    scanlines: bool = True
    screen_flicker: bool = True
    phosphor_glow: bool = True
    text_defocus: float = 0.5  # 0.0 to 1.0 blur strength
    noise: bool = True
    curvature: bool = True
    animation_speed: float = 1.0
    font_size: int = 18
    font_family: str = "Share Tech Mono"


@dataclass
class BootConfig:
    show_animation: bool = True
    animation_delay_ms: int = 50


@dataclass
class AudioConfig:
    enabled: bool = True
    volume: float = 0.7


@dataclass
class SystemConfig:
    development_mode: bool = False
    mock_auth: bool = False
    username: str = ""


@dataclass
class AppConfig:
    game: GameConfig = field(default_factory=GameConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    boot: BootConfig = field(default_factory=BootConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
