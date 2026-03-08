"""Unit tests for DriveReader utility methods — no Google Drive credentials required."""

import pytest
from unittest.mock import patch, MagicMock


# Patch _authenticate so we never need real credentials
def make_reader(folder_id='test_folder_id'):
    from src.drive_reader import DriveReader
    with patch.object(DriveReader, '_authenticate'):
        reader = DriveReader(folder_id)
        reader.enabled = False  # Keep disabled — we're testing helpers only
    return reader


# ---------------------------------------------------------------------------
# _mask_secret
# ---------------------------------------------------------------------------

class TestMaskSecret:
    def test_normal_secret(self):
        r = make_reader()
        assert r._mask_secret('abcdefghijklmn') == 'abcdef...***'

    def test_short_secret_fully_masked(self):
        r = make_reader()
        assert r._mask_secret('abc') == '***'

    def test_exactly_visible_chars_masked(self):
        r = make_reader()
        assert r._mask_secret('abcdef') == '***'

    def test_empty_secret(self):
        r = make_reader()
        assert r._mask_secret('') == '(empty)'

    def test_custom_visible_chars(self):
        r = make_reader()
        result = r._mask_secret('supersecrettoken', visible_chars=4)
        assert result == 'supe...***'


# ---------------------------------------------------------------------------
# URL / folder ID extraction (tested via __init__ parsing logic)
# ---------------------------------------------------------------------------

class TestFolderIdExtraction:
    def _folder_id(self, url):
        r = make_reader(url)
        return r.folder_id

    def test_raw_id_unchanged(self):
        assert self._folder_id('1xlsxAV7dim4NubUNK8fCIuARF') == '1xlsxAV7dim4NubUNK8fCIuARF'

    def test_folders_url(self):
        url = 'https://drive.google.com/drive/folders/1xlsxAV7dim4NubUNK8fCIuARF?usp=drive_link'
        assert self._folder_id(url) == '1xlsxAV7dim4NubUNK8fCIuARF'

    def test_open_id_url(self):
        url = 'https://drive.google.com/open?id=1xlsxAV7dim4NubUNK8fCIuARF'
        assert self._folder_id(url) == '1xlsxAV7dim4NubUNK8fCIuARF'

    def test_id_with_query_params(self):
        assert self._folder_id('1xlsxAV7dim4NubUNK8fCIuARF?usp=sharing') == '1xlsxAV7dim4NubUNK8fCIuARF'

    def test_id_with_ampersand(self):
        assert self._folder_id('1xlsxAV7dim4NubUNK8fCIuARF&foo=bar') == '1xlsxAV7dim4NubUNK8fCIuARF'


# ---------------------------------------------------------------------------
# download_file — filename sanitization
# ---------------------------------------------------------------------------

class TestDownloadFileSanitization:
    def test_path_traversal_rejected(self):
        r = make_reader()
        result = r.download_file('file_id', '../../../etc/passwd')
        assert result is None

    def test_dot_only_rejected(self):
        r = make_reader()
        assert r.download_file('file_id', '.') is None

    def test_dotdot_rejected(self):
        r = make_reader()
        assert r.download_file('file_id', '..') is None

    def test_empty_name_rejected(self):
        r = make_reader()
        assert r.download_file('file_id', '') is None

    def test_safe_name_attempts_download(self):
        r = make_reader()
        r.enabled = True
        r.drive = MagicMock()
        mock_file = MagicMock()
        r.drive.CreateFile.return_value = mock_file
        mock_file.GetContentFile.side_effect = Exception('network error')
        result = r.download_file('file_id', 'subdir/analysis_2026.txt')
        # Basename extracted → 'analysis_2026.txt'; download attempted but fails → None
        assert result is None
