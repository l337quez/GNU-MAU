"""
DevOps tools module for GNU Mau CLI.

Provides pure-Python equivalents of the GUI tools:
- Port scanning
- IP/CIDR calculation
- JWT decoding (no secret required)
- Password hashing (PBKDF2)
"""
import socket
import ipaddress
import hashlib
import base64
import json


def scan_port(host, port, timeout=2):
    """Check if a TCP port is open on *host*."""
    port = int(port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((host, port))
        status = "open" if result == 0 else "closed"
    except socket.gaierror as e:
        status = f"error: {e}"
    finally:
        sock.close()
    return {"host": host, "port": port, "status": status}


def calc_ip(cidr):
    """Calculate network info for a CIDR block."""
    net = ipaddress.ip_network(cidr, strict=False)
    return {
        "cidr": str(cidr),
        "network_address": str(net.network_address),
        "broadcast_address": str(net.broadcast_address),
        "netmask": str(net.netmask),
        "total_hosts": net.num_addresses,
        "usable_hosts": max(net.num_addresses - 2, 0),
    }


def decode_jwt(token):
    """Decode a JWT token payload without verification."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format (expected 3 parts)")
    payload = parts[1]
    # Fix padding
    padding = len(payload) % 4
    if padding:
        payload += "=" * (4 - padding)
    decoded_bytes = base64.urlsafe_b64decode(payload)
    decoded_str = decoded_bytes.decode("utf-8")
    return json.loads(decoded_str)


def hash_password(password, rounds=1, algorithm="sha256"):
    """Hash a password with PBKDF2-HMAC."""
    salt = b"constant_devops_salt"
    dk = hashlib.pbkdf2_hmac(algorithm, password.encode(), salt, rounds)
    return {
        "algorithm": f"PBKDF2-{algorithm.upper()}",
        "rounds": rounds,
        "salt": salt.decode(),
        "hash": dk.hex(),
    }
