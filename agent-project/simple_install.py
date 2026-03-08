#!/usr/bin/env python3
"""
Simple Installation Script for Agent Ecosystem

This script handles the basic installation and setup of the agent ecosystem.
"""

import os
import sys
import subprocess
import venv
from pathlib import Path


def run_command(command, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{command}': {e}")
        print(f"Error output: {e.stderr}")
        return None


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required.")
        print(f"Current version: {sys.version}")
        return False
    print(f"Python version check passed: {sys.version}")
    return True


def create_virtual_environment(venv_path):
    """Create a virtual environment."""
    print(f"Creating virtual environment at {venv_path}")
    
    if venv_path.exists():
        print("Virtual environment already exists.")
        return True
    
    try:
        venv.create(venv_path, with_pip=True)
        print("Virtual environment created successfully.")
        return True
    except Exception as e:
        print(f"Error creating virtual environment: {e}")
        return False


def get_python_executable(venv_path):
    """Get the Python executable path for the virtual environment."""
    if os.name == 'nt':  # Windows
        return venv_path / "Scripts" / "python.exe"
    else:  # Unix/Linux/macOS
        return venv_path / "bin" / "python"


def install_dependencies(venv_path):
    """Install project dependencies."""
    print("Installing dependencies...")
    
    requirements_file = Path(__file__).parent / "requirements_simple.txt"
    
    if not requirements_file.exists():
        print("Error: requirements.txt not found.")
        return False
    
    # Upgrade pip and install setuptools first
    python_executable = get_python_executable(venv_path)
    upgrade_cmd = f'"{python_executable}" -m pip install --upgrade pip setuptools wheel'
    if not run_command(upgrade_cmd):
        return False
    
    # Install requirements
    install_cmd = f'"{python_executable}" -m pip install -r "{requirements_file}"'
    if not run_command(install_cmd):
        return False
    
    print("Dependencies installed successfully.")
    return True


def create_directories():
    """Create necessary directories."""
    print("Creating necessary directories...")
    
    directories = [
        "logs",
        "data",
        "templates",
        "output"
    ]
    
    for directory in directories:
        dir_path = Path(__file__).parent / directory
        dir_path.mkdir(exist_ok=True)
        print(f"Created directory: {dir_path}")


def create_environment_file():
    """Create a .env file with example environment variables."""
    env_file = Path(__file__).parent / ".env"
    
    if env_file.exists():
        print(".env file already exists.")
        return
    
    env_content = """# Agent Ecosystem Environment Variables

# API Keys (replace with your actual keys)
OPENAI_API_KEY=your_openai_api_key_here
NEWS_API_KEY=your_news_api_key_here
WEATHER_API_KEY=your_weather_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///data/agent_ecosystem.db

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/agent_ecosystem.log

# Agent Configuration
MAX_CONCURRENT_TASKS=5
DEFAULT_TIMEOUT=300
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("Created .env file with example environment variables.")


def test_installation(venv_path):
    """Test if the installation works by importing key modules."""
    print("Testing installation...")
    
    python_executable = get_python_executable(venv_path)
    project_dir = Path(__file__).parent
    
    # Test script
    test_script = """
import sys
sys.path.insert(0, 'src')

try:
    from agents import BaseAgent, PrimaryAgent
    from communication import MessageBus
    from utils import load_config
    print("All core modules imported successfully!")
    print("Installation test passed!")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)
"""
    
    test_file = project_dir / "test_import.py"
    with open(test_file, 'w') as f:
        f.write(test_script)
    
    test_cmd = f'"{python_executable}" "{test_file}"'
    result = run_command(test_cmd, cwd=project_dir)
    
    # Clean up test file
    test_file.unlink(missing_ok=True)
    
    if result is not None:
        print("Installation test completed successfully.")
        return True
    else:
        print("Installation test failed.")
        return False


def main():
    """Main installation function."""
    print("Agent Ecosystem Simple Installation")
    print("=" * 45)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Get project directory
    project_dir = Path(__file__).parent
    venv_path = project_dir / "venv"
    
    print(f"Project directory: {project_dir}")
    print(f"Virtual environment path: {venv_path}")
    
    # Create virtual environment
    if not create_virtual_environment(venv_path):
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies(venv_path):
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Create environment file
    create_environment_file()
    
    # Test installation
    test_installation(venv_path)
    
    print("\nInstallation completed successfully!")
    print("\nNext steps:")
    print("1. Activate the virtual environment:")
    if os.name == 'nt':  # Windows
        print(f"   {venv_path}\\Scripts\\activate")
    else:  # Unix/Linux/macOS
        print(f"   source {venv_path}/bin/activate")
    
    print("2. Update the .env file with your API keys")
    print("3. Run the example script:")
    print("   python example.py")
    print("4. Or run the main application:")
    print("   python -m src.main")


if __name__ == "__main__":
    main()
