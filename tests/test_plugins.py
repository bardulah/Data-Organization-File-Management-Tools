"""
Tests for plugin system.
"""

import pytest
from pathlib import Path

from fileorganizer.plugins.base import Plugin, PluginManager
from fileorganizer.plugins.builtin import InvoiceOrganizerPlugin, PhotoOrganizerPlugin


class TestPlugin:
    """Test plugin base class."""

    def test_invoice_plugin_detection(self):
        """Test invoice plugin detects invoice files."""
        plugin = InvoiceOrganizerPlugin()

        # Should detect invoice files
        assert plugin.should_process(Path('invoice_2024.pdf'), {})
        assert plugin.should_process(Path('inv-12345.pdf'), {})
        assert plugin.should_process(Path('receipt.pdf'), {})

        # Should not detect non-invoice files
        assert not plugin.should_process(Path('photo.jpg'), {})
        assert not plugin.should_process(Path('document.pdf'), {})

    def test_photo_plugin_detection(self):
        """Test photo plugin detects photo files."""
        plugin = PhotoOrganizerPlugin()

        # Should detect photo files
        assert plugin.should_process(Path('IMG_1234.jpg'), {})
        assert plugin.should_process(Path('photo.png'), {})
        assert plugin.should_process(Path('image.gif'), {})

        # Should not detect non-photo files
        assert not plugin.should_process(Path('document.pdf'), {})
        assert not plugin.should_process(Path('video.mp4'), {})

    def test_photo_plugin_organization(self, tmp_path):
        """Test photo plugin organizes by date."""
        plugin = PhotoOrganizerPlugin()

        file_path = Path('/photos/IMG_1234.jpg')
        metadata = {
            'smart_date': '2024-03-15T10:30:00'
        }

        target_path = plugin.get_target_path(file_path, metadata, tmp_path)

        # Should organize as Photos/2024/03/15/IMG_1234.jpg
        assert 'Photos' in str(target_path)
        assert '2024' in str(target_path)
        assert '03' in str(target_path)
        assert '15' in str(target_path)

    def test_plugin_manager_loading(self, tmp_path):
        """Test plugin manager loads builtin plugins."""
        manager = PluginManager(plugin_dir=tmp_path)

        # Should load builtin plugins
        assert len(manager.plugins) >= 2

        plugins = manager.list_plugins()
        plugin_names = [p['name'] for p in plugins]

        assert 'InvoiceOrganizer' in plugin_names or 'PhotoOrganizer' in plugin_names

    def test_plugin_manager_file_routing(self, tmp_path):
        """Test plugin manager routes files to correct plugin."""
        manager = PluginManager(plugin_dir=tmp_path)

        # Invoice file should be routed to invoice plugin
        invoice_plugin = manager.get_plugin_for_file(
            Path('invoice_2024.pdf'),
            {}
        )
        assert invoice_plugin is not None
        assert 'Invoice' in invoice_plugin.name

        # Photo file should be routed to photo plugin
        photo_plugin = manager.get_plugin_for_file(
            Path('IMG_1234.jpg'),
            {}
        )
        assert photo_plugin is not None
        assert 'Photo' in photo_plugin.name
