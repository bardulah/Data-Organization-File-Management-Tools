"""
Configuration management for File Organization Assistant.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional


class Config:
    """Manage configuration for file organization tasks."""

    DEFAULT_CONFIG = {
        'exclude_dirs': ['.git', '.svn', 'node_modules', '__pycache__', '.venv'],
        'exclude_extensions': [],
        'include_hidden': False,
        'duplicate_detection': {
            'enabled': True,
            'keep_strategy': 'newest'
        },
        'organization': {
            'mode': 'type',
            'date_format': '%Y/%m',
            'custom_categories': {}
        },
        'archiving': {
            'old_files_threshold_days': 365,
            'compress': True,
            'cleanup_empty_dirs': True
        },
        'naming': {
            'template': '{date}_{name}',
            'lowercase': False,
            'replace_spaces': True,
            'space_replacement': '_'
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to configuration file (JSON or YAML)
        """
        self.config = self.DEFAULT_CONFIG.copy()

        if config_path:
            self.load(config_path)

    def load(self, config_path: str):
        """
        Load configuration from a file.

        Args:
            config_path: Path to configuration file
        """
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                loaded_config = yaml.safe_load(f)
            elif path.suffix == '.json':
                loaded_config = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration format: {path.suffix}")

        # Merge with defaults
        self._deep_update(self.config, loaded_config)

    def save(self, config_path: str, format: str = 'yaml'):
        """
        Save configuration to a file.

        Args:
            config_path: Path to save configuration
            format: Format to use ('yaml' or 'json')
        """
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            if format == 'yaml':
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            elif format == 'json':
                json.dump(self.config, f, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format}")

    def get(self, key: str, default=None):
        """
        Get a configuration value.

        Args:
            key: Configuration key (can use dot notation, e.g., 'duplicate_detection.enabled')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value):
        """
        Set a configuration value.

        Args:
            key: Configuration key (can use dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def _deep_update(self, base_dict: dict, update_dict: dict):
        """
        Recursively update a dictionary.

        Args:
            base_dict: Base dictionary to update
            update_dict: Dictionary with updates
        """
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def create_default_config(self, output_path: str, format: str = 'yaml'):
        """
        Create a default configuration file.

        Args:
            output_path: Path to save the configuration
            format: Format to use ('yaml' or 'json')
        """
        self.config = self.DEFAULT_CONFIG.copy()
        self.save(output_path, format)
