"""Tests for the configuration loader."""

import os
import tempfile
from pathlib import Path

from app.config.defaults import AppConfig, GameConfig
from app.config.settings import load_config, load_toml, parse_cli_args


class TestParseCliArgs:
    def test_defaults(self):
        args = parse_cli_args([])
        assert not args.development
        assert not args.mock_auth
        assert not args.no_crt
        assert not args.skip_boot
        assert args.config is None

    def test_development(self):
        args = parse_cli_args(["--development"])
        assert args.development

    def test_mock_auth(self):
        args = parse_cli_args(["--mock-auth"])
        assert args.mock_auth

    def test_no_crt(self):
        args = parse_cli_args(["--no-crt"])
        assert args.no_crt

    def test_skip_boot(self):
        args = parse_cli_args(["--skip-boot"])
        assert args.skip_boot

    def test_config_path(self):
        args = parse_cli_args(["--config", "/tmp/test.toml"])
        assert args.config == "/tmp/test.toml"


class TestLoadToml:
    def test_nonexistent_file(self):
        result = load_toml(Path("/nonexistent/path.toml"))
        assert result == {}

    def test_valid_toml(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".toml", delete=False
        ) as f:
            f.write('[game]\nnum_candidates = 8\n')
            f.flush()
            result = load_toml(Path(f.name))
            assert result["game"]["num_candidates"] == 8
            os.unlink(f.name)


class TestLoadConfig:
    def test_defaults(self):
        cfg = load_config(["--development", "--mock-auth"])
        assert isinstance(cfg, AppConfig)
        assert cfg.game.initial_attempts == 4
        assert cfg.game.num_candidates == 12

    def test_development_flag(self):
        cfg = load_config(["--development", "--mock-auth"])
        assert cfg.system.development_mode
        assert cfg.system.mock_auth

    def test_no_crt_disables_all(self):
        cfg = load_config(["--development", "--mock-auth", "--no-crt"])
        assert not cfg.display.crt_effects
        assert not cfg.display.scanlines
        assert not cfg.display.screen_flicker
        assert not cfg.display.phosphor_glow
        assert not cfg.display.noise
        assert not cfg.display.curvature

    def test_skip_boot(self):
        cfg = load_config(["--development", "--mock-auth", "--skip-boot"])
        assert not cfg.boot.show_animation

    def test_toml_override(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".toml", delete=False
        ) as f:
            f.write('[game]\nnum_candidates = 6\ninitial_attempts = 3\n')
            f.flush()
            cfg = load_config([
                "--development", "--mock-auth", "--config", f.name
            ])
            assert cfg.game.num_candidates == 6
            assert cfg.game.initial_attempts == 3
            os.unlink(f.name)

    def test_mock_auth_requires_development(self):
        import pytest
        with pytest.raises(SystemExit):
            load_config(["--mock-auth"])
