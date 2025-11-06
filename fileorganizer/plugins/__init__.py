"""
Plugin system for extensible file organization.
"""

from .base import Plugin, PluginManager
from .builtin import InvoiceOrganizerPlugin, PhotoOrganizerPlugin

__all__ = ['Plugin', 'PluginManager', 'InvoiceOrganizerPlugin', 'PhotoOrganizerPlugin']
