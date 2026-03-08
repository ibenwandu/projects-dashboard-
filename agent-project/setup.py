"""
Setup script for Agent Ecosystem

This script handles the installation and setup of the agent ecosystem package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="agent-ecosystem",
    version="1.0.0",
    author="Agent Ecosystem Team",
    author_email="team@agent-ecosystem.com",
    description="A sophisticated multi-agent system for coordinated task execution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/agent-ecosystem/agent-ecosystem",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "myst-parser>=0.18.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "agent-ecosystem=src.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json"],
    },
    keywords=[
        "agents",
        "multi-agent",
        "artificial-intelligence",
        "workflow",
        "automation",
        "research",
        "analysis",
        "writing",
        "quality-control",
    ],
    project_urls={
        "Bug Reports": "https://github.com/agent-ecosystem/agent-ecosystem/issues",
        "Source": "https://github.com/agent-ecosystem/agent-ecosystem",
        "Documentation": "https://agent-ecosystem.readthedocs.io/",
    },
)














