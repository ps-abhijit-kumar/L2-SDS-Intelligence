import pytest
from unittest.mock import patch, MagicMock
from src.security import (
    validate_url_safety,
    safe_fetch_document,
    SecurityError,
    is_ip_blocked,
    is_valid_url_syntax
)
import ipaddress

def test_is_valid_url_syntax():
    assert is_valid_url_syntax("https://www.sigmaaldrich.com/sds/acetone.pdf") is True
    assert is_valid_url_syntax("http://fishersci.com/doc") is True
    assert is_valid_url_syntax("ftp://ftp.example.com") is False
    assert is_valid_url_syntax("file:///etc/passwd") is False
    assert is_valid_url_syntax("http://localhost:8000") is False
    assert is_valid_url_syntax("http://127.0.0.1/admin") is False
    assert is_valid_url_syntax("http://internal.local/sds") is False
    assert is_valid_url_syntax("") is False

def test_validate_url_safety_valid_public():
    url, host, port = validate_url_safety("https://www.google.com/search")
    assert host == "www.google.com"
    assert port == 443

def test_reject_invalid_scheme():
    with pytest.raises(SecurityError, match="Invalid URL scheme"):
        validate_url_safety("file:///etc/passwd")

    with pytest.raises(SecurityError, match="Invalid URL scheme"):
        validate_url_safety("ftp://ftp.secure.com/sds.pdf")

    with pytest.raises(SecurityError, match="Invalid URL scheme"):
        validate_url_safety("gopher://evil.com")

def test_reject_loopback_and_localhost():
    with pytest.raises(SecurityError, match="Access to blocked internal/local hostname 'localhost' is denied."):
        validate_url_safety("http://localhost:8000/sds.pdf")

    with pytest.raises(SecurityError, match="Access to blocked internal/local hostname '127.0.0.1' is denied."):
        validate_url_safety("http://127.0.0.1/secret")

def test_reject_private_ip_networks():
    # 10.0.0.0/8
    with pytest.raises(SecurityError):
        validate_url_safety("http://10.1.2.3/api/secret")

    # 192.168.0.0/16
    with pytest.raises(SecurityError):
        validate_url_safety("http://192.168.1.1/admin")

    # 172.16.0.0/12
    with pytest.raises(SecurityError):
        validate_url_safety("http://172.20.5.10/doc")

def test_reject_cloud_metadata_ip():
    with pytest.raises(SecurityError):
        validate_url_safety("http://169.254.169.254/latest/meta-data/")

def test_reject_internal_domain_suffixes():
    with pytest.raises(SecurityError, match="Access to blocked internal/local hostname"):
        validate_url_safety("http://db.production.local/sds")

    with pytest.raises(SecurityError, match="Access to blocked internal/local hostname"):
        validate_url_safety("http://auth.corp/login")

def test_oversized_download_rejection():
    # Simulate a response stream larger than limit
    mock_response = MagicMock()
    mock_response.geturl.return_value = "https://www.valid-site.com/large.pdf"
    mock_response.headers = {"Content-Type": "application/pdf"}
    # Stream yields chunks exceeding 100 bytes when max_size=100
    mock_response.read.side_effect = [b"A" * 60, b"B" * 60, b""]

    with patch("src.security.validate_url_safety", return_value=("https://www.valid-site.com/large.pdf", "www.valid-site.com", 443)):
        with patch("urllib.request.build_opener") as mock_build_opener:
            mock_opener = MagicMock()
            mock_opener.open.return_value.__enter__.return_value = mock_response
            mock_build_opener.return_value = mock_opener

            with pytest.raises(SecurityError, match="exceeded maximum size limit"):
                safe_fetch_document("https://www.valid-site.com/large.pdf", max_size=100)
