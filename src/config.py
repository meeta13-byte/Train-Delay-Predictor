"""Central configuration for the Indian Railways Train Delay Analytics project."""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config() -> dict:
    """Load and return the YAML configuration."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def get_path(config: dict, key: str, default: str = None) -> Path:
    """Resolve a configured path relative to the project root."""
    value = config.get("paths", {}).get(key, default)
    if value is None:
        raise KeyError(f"Missing path key: {key}")
    return PROJECT_ROOT / value
