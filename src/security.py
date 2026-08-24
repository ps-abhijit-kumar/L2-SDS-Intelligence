import ipaddress
import socket
import urllib.parse
import urllib.request
from typing import Tuple, Optional, Set

class SecurityError(Exception):
    """Raised when a URL or network request violates security policies (SSRF, etc.)."""
    pass

# Prohibited private / reserved IP ranges
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network (only valid as source address)
    ipaddress.ip_network("10.0.0.0/8"),         # Private-Use (RFC 1918)
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space (Carrier-Grade NAT)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback (RFC 1122)
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local (RFC 3927) - includes AWS/GCP/Azure 169.254.169.254 metadata
    ipaddress.ip_network("172.16.0.0/12"),      # Private-Use (RFC 1918)
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # Documentation (TEST-NET-1)
    ipaddress.ip_network("192.168.0.0/16"),     # Private-Use (RFC 1918)
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),    # Documentation (TEST-NET-2)
    ipaddress.ip_network("203.0.113.0/24"),     # Documentation (TEST-NET-3)
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved for Future Use
    ipaddress.ip_network("255.255.255.255/32"), # Limited Broadcast
    # IPv6 blocked ranges
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local Unicast
]

BLOCKED_DOMAINS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "metadata.google.internal",
    "instance-data",
}

BLOCKED_TLDS = {
    ".local",
    ".internal",
    ".corp",
    ".lan",
    ".home",
    ".localdomain"
}

ALLOWED_SCHEMES = {"http", "https"}
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit (Priority 5)

def is_ip_blocked(ip_addr_str: str) -> bool:
    """Checks if an IPv4 or IPv6 address belongs to any blocked/private network."""
    try:
        ip_obj = ipaddress.ip_address(ip_addr_str)
        for net in BLOCKED_IP_NETWORKS:
            if ip_obj in net:
                return True
        return False
    except ValueError:
        return True

def validate_url_safety(url: str) -> Tuple[str, str, int]:
    """
    Strict SSRF validation function.
    Resolves hostname to IP addresses and rejects:
    - Non-http/https schemes
    - Loopback, link-local, private, carrier NAT, or cloud metadata IP addresses
    - Internal / local domain names

    Returns: (sanitized_url, hostname, port)
    Raises: SecurityError if URL fails validation.
    """
    if not url or not isinstance(url, str):
        raise SecurityError("URL cannot be empty.")

    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as parse_err:
        raise SecurityError(f"Malformed URL structure: {str(parse_err)}")

    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise SecurityError(f"Invalid URL scheme '{scheme}'. Only HTTP and HTTPS schemes are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SecurityError("Missing host in target URL.")

    hostname_lower = hostname.lower()

    if hostname_lower in BLOCKED_DOMAINS:
        raise SecurityError(f"Access to blocked internal/local hostname '{hostname}' is denied.")

    for tld in BLOCKED_TLDS:
        if hostname_lower.endswith(tld):
            raise SecurityError(f"Access to blocked internal/local hostname with suffix '{tld}' is denied.")

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

    Returns: (raw_bytes, content_type, final_url)
    Raises: SecurityError on policy violation, ValueError/IOError on fetch failure.
    """
    effective_max_size = max_size if max_size is not None else max_size_bytes
    safe_url, _, _ = validate_url_safety(url)

    req = urllib.request.Request(
        safe_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
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
                    raise SecurityError(f"Document size exceeded maximum size limit of {effective_max_size} bytes.")
                chunks.append(chunk)

            return b"".join(chunks), content_type, final_url

    except SecurityError:
        raise
    except Exception as fetch_err:
        raise IOError(f"Network error while fetching document from '{url}': {str(fetch_err)}")
