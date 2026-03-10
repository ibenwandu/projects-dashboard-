# C:\Users\user\projects\personal\tests\vault_config_test.py
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, r'C:\Users\user\.claude\scripts')
from vault_config import get_vault_path, save_vault_config, validate_vault_path

def test_get_vault_path_from_config():
    """Should read vault path from vault_config.json"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "vault_config.json"
        config_file.write_text(json.dumps({"vault_path": r"C:\Users\user\My Knowledge Base"}))

        path = get_vault_path(config_file=config_file)
        assert path == Path(r"C:\Users\user\My Knowledge Base")

def test_get_vault_path_fallback_to_default():
    """Should use default vault path if config missing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "vault_config.json"

        path = get_vault_path(config_file=config_file)
        assert path == Path.home() / "My Knowledge Base"

def test_save_vault_config():
    """Should save vault path to config file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "vault_config.json"
        test_path = Path(r"C:\Users\user\Custom Vault")

        save_vault_config(test_path, config_file=config_file)

        assert config_file.exists()
        data = json.loads(config_file.read_text())
        assert data["vault_path"] == str(test_path)

def test_validate_vault_path_requires_subdirs():
    """Should fail if required subdirectories missing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "incomplete_vault"
        vault_path.mkdir()  # Create vault but no subdirs

        is_valid, error = validate_vault_path(vault_path)
        assert not is_valid
        assert "required directories" in error.lower()

def test_validate_vault_path_valid_vault():
    """Should validate vault with all required directories"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "valid_vault"
        vault_path.mkdir()
        (vault_path / "Projects").mkdir()
        (vault_path / "Trading-Journal").mkdir()
        (vault_path / "Ideas").mkdir()

        is_valid, error = validate_vault_path(vault_path)
        assert is_valid
        assert error is None

def test_get_vault_path_corrupted_json():
    """Should fall back to default if config JSON is corrupted"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "vault_config.json"
        config_file.write_text("{invalid json content")  # Corrupted JSON

        path = get_vault_path(config_file=config_file)
        assert path == Path.home() / "My Knowledge Base"
