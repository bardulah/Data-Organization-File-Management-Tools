"""
Base plugin system for extensible file organization.
"""

import importlib
import importlib.util
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class Plugin(ABC):
    """Base class for file organization plugins."""

    def __init__(self):
        """Initialize plugin."""
        self.name = self.__class__.__name__
        self.version = "1.0.0"
        self.enabled = True

    @abstractmethod
    def should_process(self, file_path: Path, metadata: Dict) -> bool:
        """
        Determine if this plugin should process the file.

        Args:
            file_path: Path to the file
            metadata: File metadata dictionary

        Returns:
            True if plugin should process this file
        """
        pass

    @abstractmethod
    def get_target_path(self, file_path: Path, metadata: Dict, target_root: Path) -> Path:
        """
        Determine target path for organizing the file.

        Args:
            file_path: Source file path
            metadata: File metadata
            target_root: Root directory for organized files

        Returns:
            Target path for the file
        """
        pass

    def get_new_filename(self, file_path: Path, metadata: Dict) -> Optional[str]:
        """
        Optionally provide a new filename for the file.

        Args:
            file_path: Original file path
            metadata: File metadata

        Returns:
            New filename or None to keep original
        """
        return None

    def post_process(self, source: Path, destination: Path, metadata: Dict):
        """
        Optional post-processing after file is organized.

        Args:
            source: Original file path
            destination: New file path
            metadata: File metadata
        """
        pass

    def get_info(self) -> Dict[str, str]:
        """Get plugin information."""
        return {
            'name': self.name,
            'version': self.version,
            'enabled': str(self.enabled)
        }


class PluginManager:
    """Manages loading and execution of plugins."""

    def __init__(self, plugin_dir: Optional[Path] = None):
        """
        Initialize plugin manager.

        Args:
            plugin_dir: Directory containing plugins (defaults to ~/.fileorganizer/plugins)
        """
        if plugin_dir is None:
            plugin_dir = Path.home() / '.fileorganizer' / 'plugins'

        self.plugin_dir = plugin_dir
        self.plugin_dir.mkdir(parents=True, exist_ok=True)

        self.plugins: List[Plugin] = []
        self._load_builtin_plugins()

    def _load_builtin_plugins(self):
        """Load built-in plugins."""
        try:
            from .builtin import InvoiceOrganizerPlugin, PhotoOrganizerPlugin

            self.plugins.append(InvoiceOrganizerPlugin())
            self.plugins.append(PhotoOrganizerPlugin())

            logger.info(f"Loaded {len(self.plugins)} built-in plugins")

        except Exception as e:
            logger.error(f"Failed to load built-in plugins: {e}")

    def load_plugin_file(self, plugin_path: Path):
        """
        Load a plugin from a Python file.

        Args:
            plugin_path: Path to plugin .py file
        """
        try:
            # Load module from file
            spec = importlib.util.spec_from_file_location("custom_plugin", plugin_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find Plugin subclasses in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, Plugin) and
                        attr is not Plugin):

                        plugin = attr()
                        self.plugins.append(plugin)
                        logger.info(f"Loaded plugin: {plugin.name} from {plugin_path}")

        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_path}: {e}")

    def load_plugins_from_directory(self):
        """Load all plugins from the plugin directory."""
        if not self.plugin_dir.exists():
            logger.info("Plugin directory doesn't exist, skipping custom plugins")
            return

        for plugin_file in self.plugin_dir.glob('*.py'):
            if not plugin_file.name.startswith('_'):
                self.load_plugin_file(plugin_file)

        logger.info(f"Total plugins loaded: {len(self.plugins)}")

    def get_plugin_for_file(self, file_path: Path, metadata: Dict) -> Optional[Plugin]:
        """
        Find the first plugin that should process this file.

        Args:
            file_path: Path to file
            metadata: File metadata

        Returns:
            Plugin instance or None
        """
        for plugin in self.plugins:
            if plugin.enabled and plugin.should_process(file_path, metadata):
                logger.debug(f"Plugin {plugin.name} will process {file_path}")
                return plugin

        return None

    def organize_file(
        self,
        file_path: Path,
        metadata: Dict,
        target_root: Path
    ) -> Optional[Dict]:
        """
        Organize a file using the appropriate plugin.

        Args:
            file_path: Source file path
            metadata: File metadata
            target_root: Root directory for organized files

        Returns:
            Dictionary with organization details or None
        """
        plugin = self.get_plugin_for_file(file_path, metadata)

        if not plugin:
            return None

        try:
            # Get target path from plugin
            target_path = plugin.get_target_path(file_path, metadata, target_root)

            # Get new filename if plugin provides one
            new_filename = plugin.get_new_filename(file_path, metadata)
            if new_filename:
                target_path = target_path.parent / new_filename

            result = {
                'plugin': plugin.name,
                'source': str(file_path),
                'target': str(target_path),
                'new_filename': new_filename
            }

            logger.debug(f"Plugin {plugin.name} organized: {file_path} -> {target_path}")
            return result

        except Exception as e:
            logger.error(f"Plugin {plugin.name} failed to process {file_path}: {e}")
            return None

    def list_plugins(self) -> List[Dict[str, str]]:
        """
        Get list of all loaded plugins.

        Returns:
            List of plugin information dictionaries
        """
        return [plugin.get_info() for plugin in self.plugins]

    def enable_plugin(self, plugin_name: str):
        """Enable a plugin by name."""
        for plugin in self.plugins:
            if plugin.name == plugin_name:
                plugin.enabled = True
                logger.info(f"Enabled plugin: {plugin_name}")
                return

        logger.warning(f"Plugin not found: {plugin_name}")

    def disable_plugin(self, plugin_name: str):
        """Disable a plugin by name."""
        for plugin in self.plugins:
            if plugin.name == plugin_name:
                plugin.enabled = False
                logger.info(f"Disabled plugin: {plugin_name}")
                return

        logger.warning(f"Plugin not found: {plugin_name}")
