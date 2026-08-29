"""Configuration loader: merges config.toml with CLI arguments and defaults."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.config.defaults import (
    AppConfig,
    AudioConfig,
    BootConfig,
    DisplayConfig,
    GameConfig,
    SystemConfig,
)

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]


def _merge_section(dataclass_instance: object, toml_section: dict) -> None:
    """Overwrite dataclass fields from a TOML dict, ignoring unknown keys."""
    for key, value in toml_section.items():
        if hasattr(dataclass_instance, key):
            setattr(dataclass_instance, key, value)


def load_toml(path: Path) -> dict:
    """Load a TOML file and return its contents as a dict."""
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)

def save_config(path: Path, config: AppConfig) -> None:
    """Save the current AppConfig state back to a TOML file."""
    import dataclasses
    
    sections = {
        "display": dataclasses.asdict(config.display),
        "boot": dataclasses.asdict(config.boot),
        "game": dataclasses.asdict(config.game),
        "audio": dataclasses.asdict(config.audio),
        "system": dataclasses.asdict(config.system),
    }
    
    lines = []
    for section_name, section_dict in sections.items():
        lines.append(f"[{section_name}]")
        for k, v in section_dict.items():
            if isinstance(v, bool):
                lines.append(f"{k} = {'true' if v else 'false'}")
            elif isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            elif isinstance(v, (int, float)):
                lines.append(f"{k} = {v}")
        lines.append("")
        
    with open(path, "w") as f:
        f.write("\n".join(lines))


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="RobCo Industries Terminal Greeter"
    )
    parser.add_argument(
        "--development",
        action="store_true",
        help="Run in development mode (windowed, no system actions)",
    )
    parser.add_argument(
        "--mock-auth",
        action="store_true",
        help="Enable mock authentication (development only)",
    )
    parser.add_argument(
        "--no-crt",
        action="store_true",
        help="Disable all CRT visual effects",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config.toml",
    )
    parser.add_argument(
        "--skip-boot",
        action="store_true",
        help="Skip the boot animation",
    )
    return parser.parse_args(argv)


def load_config(argv: list[str] | None = None) -> AppConfig:
    """Build the final AppConfig from defaults → TOML file → CLI overrides."""
    args = parse_cli_args(argv)
    cfg = AppConfig()

    # Determine config file path
    if args.config:
        config_path = Path(args.config)
    else:
        # Look next to the package first, then cwd
        pkg_dir = Path(__file__).resolve().parent.parent.parent
        config_path = pkg_dir / "config.toml"
        if not config_path.exists():
            config_path = Path.cwd() / "config.toml"

    # Load and merge TOML
    toml_data = load_toml(config_path)
    if "game" in toml_data:
        _merge_section(cfg.game, toml_data["game"])
    if "display" in toml_data:
        _merge_section(cfg.display, toml_data["display"])
    if "boot" in toml_data:
        _merge_section(cfg.boot, toml_data["boot"])
    if "audio" in toml_data:
        _merge_section(cfg.audio, toml_data["audio"])
    if "system" in toml_data:
        _merge_section(cfg.system, toml_data["system"])

    # CLI overrides (highest priority)
    if args.development:
        cfg.system.development_mode = True
    if args.mock_auth:
        cfg.system.mock_auth = True
    if args.no_crt:
        cfg.display.crt_effects = False
        cfg.display.scanlines = False
        cfg.display.screen_flicker = False
        cfg.display.phosphor_glow = False
        cfg.display.noise = False
        cfg.display.curvature = False
    if args.skip_boot:
        cfg.boot.show_animation = False

    # Safety: mock auth requires development mode
    if cfg.system.mock_auth and not cfg.system.development_mode:
        print(
            "ERROR: --mock-auth requires --development mode",
            file=sys.stderr,
        )
        sys.exit(1)

    return cfg
