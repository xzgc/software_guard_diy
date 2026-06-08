import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

import httpx


# Internal/private IP ranges that should never be accessed via SSRF
PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),     # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),    # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
]

BLOCKED_SCHEMES = {"file", "ftp", "data", "javascript", "vbscript"}

ALLOWED_UPLOAD_EXTENSIONS = {
    ".exe", ".msi", ".zip", ".rar", ".7z",
    ".dmg", ".pkg", ".deb", ".rpm",
    ".tar", ".gz", ".bz2", ".xz",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".iso", ".img",
}


def validate_download_url(url: str) -> str:
    """Validate download_url to prevent SSRF attacks.

    Ensures the URL uses HTTP/HTTPS scheme and does not point to
    internal/private IP addresses.
    """
    if not url or not url.strip():
        raise ValueError("download_url 不能为空")

    parsed = urlparse(url)

    # Only allow http and https
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"download_url 不支持 {parsed.scheme} 协议，仅允许 http/https")

    if not parsed.hostname:
        raise ValueError("download_url 缺少主机名")

    hostname = parsed.hostname.lower()

    # Block obvious internal hostnames
    if hostname in ("localhost", "localhost.localdomain"):
        raise ValueError("download_url 不能指向内部地址")

    # Resolve hostname and check against private networks
    try:
        import socket
        resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for _, _, _, _, addr in resolved_ips:
            ip = ipaddress.ip_address(addr[0])
            for network in PRIVATE_NETWORKS:
                if ip in network:
                    raise ValueError("download_url 不能指向内部/私有网络地址")
    except socket.gaierror:
        raise ValueError(f"无法解析 download_url 的主机名: {hostname}")

    return url


def sanitize_filename(filename: str) -> str:
    """Sanitize a user-provided filename to prevent path traversal.

    Strips directory components and removes dangerous characters.
    """
    if not filename:
        return "unnamed_file"

    # Take only the final component (strip any directory path)
    name = os.path.basename(filename)

    # Remove null bytes and other dangerous characters
    name = name.replace("\x00", "")

    # Remove leading dots to prevent hidden files / dot-dot issues
    name = name.lstrip(".")

    if not name:
        return "unnamed_file"

    return name


def validate_path_within_dir(file_path: str, base_dir: str) -> str:
    """Ensure resolved file_path is within base_dir to prevent path traversal.

    Returns the resolved path if safe, raises ValueError otherwise.
    """
    resolved = Path(file_path).resolve()
    base = Path(base_dir).resolve()

    if not str(resolved).startswith(str(base) + os.sep) and resolved != base:
        raise ValueError("路径不合法")

    return str(resolved)


def _is_private_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return any(ip in net for net in PRIVATE_NETWORKS)


class _SSRFSafeTransport(httpx.AsyncHTTPTransport):
    """Custom httpx transport that validates the resolved IP at connection time,
    preventing DNS rebinding attacks (TOCTOU)."""

    async def handle_async_request(self, request):
        parsed = urlparse(str(request.url))
        hostname = parsed.hostname
        if hostname:
            try:
                infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                for _, _, _, _, addr in infos:
                    if _is_private_ip(addr[0]):
                        raise ValueError(f"SSRF blocked: {hostname} resolves to private IP {addr[0]}")
            except socket.gaierror:
                raise ValueError(f"Cannot resolve hostname: {hostname}")
        return await super().handle_async_request(request)


def safe_httpx_client(**kwargs) -> httpx.AsyncClient:
    """Create an httpx client with SSRF-safe transport that validates IPs at connection time."""
    transport = _SSRFSafeTransport()
    kwargs.setdefault("follow_redirects", True)
    kwargs["transport"] = transport
    return httpx.AsyncClient(**kwargs)
