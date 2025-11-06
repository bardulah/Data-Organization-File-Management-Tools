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
    version="2.0.0",
    description="A comprehensive tool for organizing cluttered computer files and folders with undo, smart detection, and plugin support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="File Organization Assistant",
    python_requires=">=3.7",
    packages=find_packages(),
    install_requires=[
        "PyYAML>=6.0",
        "tqdm>=4.65.0",
        "Pillow>=10.0.0",
        "imagehash>=4.3.1",
        "PyPDF2>=3.0.0",
        "python-magic>=0.4.27",
        "schedule>=1.2.0",
        "Flask>=2.3.0",
        "Flask-CORS>=4.0.0",
        "click>=8.1.0",
        "rich>=13.0.0",
    ],
    extras_require={
        'dev': [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
        ]
    },
    entry_points={
        'console_scripts': [
            'fileorganizer=fileorganizer.cli_v2:main',
            'fileorganizer-v1=fileorganizer.cli:main',
            'fileorganizer-web=fileorganizer.web_api:run_server',
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
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
    keywords="file organization, duplicate files, file management, archiving, undo, smart detection, plugins, web interface",
)
