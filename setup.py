#!/usr/bin/env python3
"""
Setup script for File Organization Assistant.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="fileorganizer",
    version="1.5.0",
    description="A practical tool for organizing cluttered computer files with caching and undo support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="File Organization Assistant",
    python_requires=">=3.7",
    packages=find_packages(),
    install_requires=[
        "PyYAML>=6.0",
    ],
    entry_points={
        'console_scripts': [
            'fileorganizer=fileorganizer.cli_v1_5:main',
            'fileorganizer-v1=fileorganizer.cli:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: System :: Filesystems",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="file organization, duplicate files, file management, archiving, undo, caching",
)
