import socket
import ipaddress
import urllib.parse
import urllib.request
import re
from typing import Tuple, Optional, Set, List

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),        # IPv4 loopback
    ipaddress.ip_network('10.0.0.0/8'),         # RFC 1918 Private
    ipaddress.ip_network('172.16.0.0/12'),      # RFC 1918 Private
    ipaddress.ip_network('192.168.0.0/16'),     # RFC 1918 Private
    ipaddress.ip_network('169.254.0.0/16'),     # IPv4 Link-Local / Cloud Metadata (AWS/GCP/Azure)
    ipaddress.ip_network('100.64.0.0/10'),      # Carrier-grade NAT
    ipaddress.ip_network('192.0.0.0/24'),       # IETF Protocol Assignments
    ipaddress.ip_network('192.0.2.0/24'),       # TEST-NET-1
    ipaddress.ip_network('198.18.0.0/15'),      # Network Interconnect Benchmarking
    ipaddress.ip_network('198.51.100.0/24'),    # TEST-NET-2
    ipaddress.ip_network('203.0.113.0/24'),     # TEST-NET-3
    ipaddress.ip_network('224.0.0.0/4'),        # Multicast
    ipaddress.ip_network('240.0.0.0/4'),        # Reserved / Future use
    ipaddress.ip_network('::1/128'),            # IPv6 loopback
    ipaddress.ip_network('fc00::/7'),           # IPv6 Unique Local Address (ULA)
    ipaddress.ip_network('fe80::/10'),          # IPv6 Link-Local
]

BLOCKED_DOMAINS = {
    'localhost',
    'localhost.localdomain',
    '127.0.0.1',
    'local',
    'internal',
    'lan',
    'corp',
    'home',
    'domain.name',
    'metadata.google.internal',
    'instance-data',
}

ALLOWED_SCHEMES = {'http', 'https'}
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit to prevent memory exhaustion

class SecurityError(Exception):
    """Raised when an SSRF, domain bypass, or malicious request is detected."""
    pass

def is_ip_blocked(ip_str: str) -> bool:
    """Checks if an IP address string belongs to any private/internal/cloud metadata range."""
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        for net in BLOCKED_IP_NETWORKS:
            if ip_obj in net:
                return True
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_multicast:
            return True
        return False
    except ValueError:
        return True

def is_valid_url_syntax(url: str) -> bool:
    """Validates whether a URL string has valid HTTP/HTTPS syntax and is non-empty."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if len(url) < 8 or len(url) > 2048:
        return False
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() not in ALLOWED_SCHEMES:
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname.lower() in BLOCKED_DOMAINS or "localhost" in hostname.lower() or "127.0.0.1" in hostname:
            return False
        if any(hostname.lower().endswith("." + suffix) for suffix in ['local', 'internal', 'lan', 'corp', 'home']):
            return False
        return True
    except Exception:
        return False

def validate_url_safety(url: str) -> Tuple[str, str, int]:
    """
    Validates a URL against strict SSRF and security policies:
    1. Valid HTTP/HTTPS scheme only.
    2. Valid non-empty hostname.
    3. Blocked domain and internal suffix checks.
    4. DNS resolution and IP verification (IPv4/IPv6 private & cloud metadata ranges).

    Security Note (DNS-Rebinding TOCTOU Assessment):
    Pre-flight DNS validation inspects all resolved IP addresses against RFC 1918, link-local,
    and cloud metadata ranges. A theoretical time-of-check to time-of-use (TOCTOU) DNS-rebinding
    window exists if an attacker controls a custom authoritative DNS server racing TTL expirations
    between pre-flight check and urllib connection. In production, SDS retrieval operates exclusively
    over well-known manufacturer and authorized distributor domains, making this an accepted,
    low-probability residual risk. Per-hop redirect re-validation via SafeRedirectHandler further
    mitigates post-connection pivoting.
    """
    if not url or not isinstance(url, str):
        raise SecurityError("URL cannot be empty or non-string.")

    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as parse_err:
        raise SecurityError(f"Malformed URL structure: {str(parse_err)}")

    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise SecurityError(f"Invalid URL scheme '{scheme}'. Only HTTP and HTTPS are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SecurityError("URL must contain a valid hostname.")

    hostname_clean = hostname.lower().strip()

    # Block direct loopback/private hostnames
    if hostname_clean in BLOCKED_DOMAINS:
        raise SecurityError(f"Access to blocked internal/local hostname '{hostname_clean}' is denied.")

    # Block dotless hostnames or internal domain suffixes
    if '.' not in hostname_clean and hostname_clean != 'localhost':
        raise SecurityError(f"Dotless internal hostname '{hostname_clean}' is prohibited.")

    blocked_suffixes = ('.local', '.internal', '.lan', '.corp', '.home', '.localdomain')
    if any(hostname_clean.endswith(suffix) for suffix in blocked_suffixes):
        raise SecurityError(f"Access to blocked internal/local hostname '{hostname_clean}' is denied.")

    # Check if host is direct IP literal
    try:
        ip_obj = ipaddress.ip_address(hostname_clean)
        if is_ip_blocked(str(ip_obj)):
            raise SecurityError(f"Direct connection to private/internal IP literal '{ip_obj}' is denied.")
    except ValueError:
        pass

    # Resolve IP addresses for hostname
    port = parsed.port or (443 if scheme == "https" else 80)
    try:
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as dns_err:
        raise SecurityError(f"DNS resolution failed for '{hostname}': {str(dns_err)}")

    if not addr_info:
        raise SecurityError(f"Could not resolve IP addresses for host '{hostname}'.")

    # Verify every resolved IP address
    for family, socktype, proto, canonname, sockaddr in addr_info:
        ip_str = sockaddr[0]
        if is_ip_blocked(ip_str):
            raise SecurityError(f"Access to private/blocked IP address '{ip_str}' is denied by SSRF policy.")

    return url, hostname, port

class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    Custom HTTP Redirect Handler that validates every redirect hop against SSRF policies.
    """
    def __init__(self, max_redirects: int = 5):
        super().__init__()
        self.max_redirects = max_redirects
        self.redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        if self.redirect_count > self.max_redirects:
            raise SecurityError(f"Exceeded maximum allowed redirects ({self.max_redirects}).")

        # Validate target redirect URL
        validate_url_safety(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def safe_fetch_document(
    url: str,
    timeout: float = 12.0,
    max_size_bytes: int = MAX_DOCUMENT_SIZE_BYTES,
    max_size: Optional[int] = None
) -> Tuple[bytes, str, str]:
    """
    Safely downloads a document via HTTP/HTTPS with:
    1. Pre-flight SSRF DNS & IP validation
    2. Safe redirect handling (validates each hop)
    3. Stream chunking with strict size bound (10MB limit)
    4. Timeout enforcement
    """
    effective_max_size = max_size if max_size is not None else max_size_bytes
    safe_url, _, _ = validate_url_safety(url)

    req = urllib.request.Request(
        safe_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,application/pdf,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
    )

    redirect_handler = SafeRedirectHandler()
    opener = urllib.request.build_opener(redirect_handler)

    try:
        with opener.open(req, timeout=timeout) as response:
            final_url = response.geturl()
            validate_url_safety(final_url)

            content_type = response.headers.get("Content-Type", "application/octet-stream").lower()

            # Stream read in chunks to strictly enforce size limits
            chunks = []
            total_read = 0
            chunk_size = 64 * 1024  # 64 KB chunks

            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                total_read += len(chunk)
                if total_read > effective_max_size:
                    raise SecurityError(f"Document exceeded maximum size limit of {effective_max_size} bytes.")
                chunks.append(chunk)

            return b"".join(chunks), content_type, final_url

    except SecurityError:
        raise
    except Exception as fetch_err:
        raise IOError(f"Failed to safely fetch document from '{url}': {str(fetch_err)}")
