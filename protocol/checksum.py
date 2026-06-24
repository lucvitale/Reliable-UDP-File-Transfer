import hashlib


def calculate_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_checksum(data: bytes, checksum: str) -> bool:
    return calculate_checksum(data) == checksum