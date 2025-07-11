import yaml
from pathlib import Path

def load_config():
    """Loads the YAML configuration file from the project root."""
    # Use Path.cwd() to ensure the path is relative to the project root
    # where the script is executed.
    config_path = Path.cwd() / 'config.yaml'
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f) 