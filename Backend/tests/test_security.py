"""
Security tests — path traversal, upload limits, extension validation.
Uses FastAPI's TestClient so no real server is needed.
"""
import sys
import os
from pathlib import Path
from io import BytesIO

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

# Ensure no API key is required for tests
os.environ.pop("API_KEY", None)
os.environ["DEV_MODE"] = "1"

from main import app, _sanitize_filename

client = TestClient(app)


class TestSanitizeFilename:
    def test_strips_directory_components(self):
        assert _sanitize_filename("../../etc/passwd") == "passwd"

    def test_simple_filename_unchanged(self):
        assert _sanitize_filename("report.docx") == "report.docx"

    def test_nested_path_stripped(self):
        assert _sanitize_filename("a/b/c/file.pdf") == "file.pdf"

    def test_backslash_path_rejected(self):
        """On POSIX, backslash isn't a path separator, but filenames with
        backslashes are suspicious — _sanitize_filename rejects them."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _sanitize_filename("a\\b\\file.txt")


class TestUploadSecurity:
    def test_traversal_filename_neutralized(self):
        """A filename like ../../etc/passwd should be stripped to just 'passwd'
        and then rejected for unsupported extension."""
        resp = client.post(
            "/upload",
            files=[("files", ("../../etc/passwd", b"malicious content", "application/octet-stream"))],
        )
        # Should be rejected (no valid extension)
        assert resp.status_code == 400
        assert "Unsupported file extension" in resp.json()["detail"]

    def test_unsupported_extension_rejected(self):
        resp = client.post(
            "/upload",
            files=[("files", ("script.exe", b"binary", "application/octet-stream"))],
        )
        assert resp.status_code == 400

    def test_valid_extension_accepted(self):
        content = b"Hello world"
        resp = client.post(
            "/upload",
            files=[("files", ("test.txt", content, "text/plain"))],
        )
        assert resp.status_code == 200
        assert "file_paths" in resp.json()

    def test_oversized_file_rejected(self):
        # Generate content just over 25MB
        big_content = b"x" * (26 * 1024 * 1024)
        resp = client.post(
            "/upload",
            files=[("files", ("big.txt", big_content, "text/plain"))],
        )
        assert resp.status_code == 413


class TestDownloadSecurity:
    def test_traversal_in_download_rejected(self):
        resp = client.get("/download/../../etc/passwd")
        # FastAPI might return 400 (our sanitizer) or 404 (file not found)
        assert resp.status_code in (400, 404)

    def test_nonexistent_file_404(self):
        resp = client.get("/download/nonexistent_file.docx")
        assert resp.status_code == 404
