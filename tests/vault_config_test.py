# C:\Users\user\projects\personal\tests\vault_config_test.py
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, r'C:\Users\user\.claude\scripts')
from vault_config import get_vault_path, save_vault_config

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
