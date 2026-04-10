"""
EAON 2.0 — IP Utilities
========================
IP address extraction, validation, and classification.
"""

import re
import ipaddress
from typing import Optional, Tuple
from dataclasses import dataclass


# Regex patterns
IPV4_PATTERN = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
)

IPV6_PATTERN = re.compile(
    r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|'
    r'\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b|'
    r'\b(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\b|'
    r'\b::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}\b'
)

CIDR_PATTERN = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/(?:3[0-2]|[12]?[0-9])\b'
)


@dataclass
class IPInfo:
    """IP address information."""
    ip: str
    version: int  # 4 or 6
    is_private: bool
    is_loopback: bool
    is_multicast: bool
    is_reserved: bool
    is_global: bool


def extract_ip(text: str) -> Optional[str]:
    """
    Extract first IPv4 address from text.
    
    Args:
        text: Input text to search
    
    Returns:
        First IPv4 found or None
    """
    match = IPV4_PATTERN.search(text)
    return match.group(0) if match else None


def extract_all_ips(text: str) -> list[str]:
    """
    Extract all IPv4 addresses from text.
    
    Args:
        text: Input text to search
    
    Returns:
        List of all IPv4 addresses found
    """
    return IPV4_PATTERN.findall(text)


def extract_ipv6(text: str) -> Optional[str]:
    """
    Extract first IPv6 address from text.
    
    Args:
        text: Input text to search
    
    Returns:
        First IPv6 found or None
    """
    match = IPV6_PATTERN.search(text)
    return match.group(0) if match else None


def extract_ip_pair(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract source and destination IP from text.
    Assumes format: "src_ip -> dst_ip" or "from src_ip to dst_ip"
    Falls back to first two IPs found.
    
    Args:
        text: Input text to search
    
    Returns:
        Tuple of (src_ip, dst_ip), either can be None
    """
    ips = extract_all_ips(text)
    
    if len(ips) >= 2:
        return ips[0], ips[1]
    elif len(ips) == 1:
        return ips[0], None
    else:
        return None, None


def is_valid_ip(ip: str) -> bool:
    """
    Check if string is a valid IP address (v4 or v6).
    
    Args:
        ip: IP address string
    
    Returns:
        True if valid
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_valid_ipv4(ip: str) -> bool:
    """Check if string is a valid IPv4 address."""
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ValueError:
        return False


def is_valid_ipv6(ip: str) -> bool:
    """Check if string is a valid IPv6 address."""
    try:
        ipaddress.IPv6Address(ip)
        return True
    except ValueError:
        return False


def get_ip_info(ip: str) -> Optional[IPInfo]:
    """
    Get detailed information about an IP address.
    
    Args:
        ip: IP address string
    
    Returns:
        IPInfo object or None if invalid
    """
    try:
        addr = ipaddress.ip_address(ip)
        return IPInfo(
            ip=str(addr),
            version=addr.version,
            is_private=addr.is_private,
            is_loopback=addr.is_loopback,
            is_multicast=addr.is_multicast,
            is_reserved=addr.is_reserved,
            is_global=addr.is_global,
        )
    except ValueError:
        return None


def is_public_ip(ip: str) -> bool:
    """
    Check if IP is a public (globally routable) address.
    
    Args:
        ip: IP address string
    
    Returns:
        True if public/global
    """
    info = get_ip_info(ip)
    return info.is_global if info else False


def is_private_ip(ip: str) -> bool:
    """
    Check if IP is a private (RFC 1918) address.
    
    Args:
        ip: IP address string
    
    Returns:
        True if private
    """
    info = get_ip_info(ip)
    return info.is_private if info else False


def normalize_ip(ip: str) -> Optional[str]:
    """
    Normalize IP address to standard form.
    
    Args:
        ip: IP address string (may have leading zeros, etc.)
    
    Returns:
        Normalized IP string or None if invalid
    """
    try:
        return str(ipaddress.ip_address(ip))
    except ValueError:
        return None


def ip_in_network(ip: str, network: str) -> bool:
    """
    Check if IP is within a CIDR network.
    
    Args:
        ip: IP address string
        network: CIDR notation network (e.g., "192.168.0.0/16")
    
    Returns:
        True if IP is in network
    """
    try:
        addr = ipaddress.ip_address(ip)
        net = ipaddress.ip_network(network, strict=False)
        return addr in net
    except ValueError:
        return False


def is_bogon(ip: str) -> bool:
    """
    Check if IP is a bogon (non-routable) address.
    
    Args:
        ip: IP address string
    
    Returns:
        True if bogon
    """
    bogon_networks = [
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
    ]
    
    return any(ip_in_network(ip, net) for net in bogon_networks)


def obfuscate_ip(ip: str) -> str:
    """
    Obfuscate IP for logging (hide last octet for IPv4).
    
    Args:
        ip: IP address string
    
    Returns:
        Obfuscated IP (e.g., "192.168.1.xxx")
    """
    if is_valid_ipv4(ip):
        parts = ip.split(".")
        parts[-1] = "xxx"
        return ".".join(parts)
    elif is_valid_ipv6(ip):
        # Hide last 64 bits
        parts = ip.split(":")
        if len(parts) >= 4:
            return ":".join(parts[:4]) + "::xxxx"
    return ip


def parse_port(text: str) -> Optional[int]:
    """
    Extract port number from text (e.g., ":8080" or "port 443").
    
    Args:
        text: Input text
    
    Returns:
        Port number or None
    """
    # Match :port or port=N or port N
    patterns = [
        r':(\d{1,5})\b',
        r'port[=:\s]+(\d{1,5})\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            port = int(match.group(1))
            if 1 <= port <= 65535:
                return port
    
    return None


def extract_ip_port(text: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Extract IP and port from text (e.g., "192.168.1.1:8080").
    
    Args:
        text: Input text
    
    Returns:
        Tuple of (ip, port)
    """
    # Match IP:port pattern
    match = re.search(
        r'(\b(?:\d{1,3}\.){3}\d{1,3}):(\d{1,5})\b',
        text
    )
    
    if match:
        ip = match.group(1)
        port = int(match.group(2))
        if is_valid_ip(ip) and 1 <= port <= 65535:
            return ip, port
    
    # Fall back to separate extraction
    ip = extract_ip(text)
    port = parse_port(text)
    return ip, port
