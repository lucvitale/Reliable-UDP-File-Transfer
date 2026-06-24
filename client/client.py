import json
import os

from protocol.constants import (
    DOWNLOAD_REQUEST,
    ERROR,
    LIST_REQUEST,
    LIST_RESPONSE,
    LOGIN_REQUEST,
    LOGIN_RESPONSE,
    SERVER_HOST,
    SERVER_PORT,
    UPLOAD_REQUEST,
)
from protocol.packet import Packet
from protocol.reliable_udp import ReliableUDP


SERVER_ADDRESS = (SERVER_HOST, SERVER_PORT)
DOWNLOADS_FOLDER = "downloads"

udp = ReliableUDP()


def make_packet(packet_type, payload=b""):
    """Build a Packet from text or bytes payload."""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")

    return Packet(packet_type, 0, 0, payload)


def decode_payload(packet):
    """Decode a response payload as UTF-8 text."""
    return packet.payload.decode("utf-8").strip()


def receive_response(expected_type):
    """Receive and validate a response from the server."""
    packet, address = udp.receive_packet()

    if address[1] != SERVER_PORT:
        raise RuntimeError("Received packet from unknown server")

    if packet.packet_type == ERROR:
        raise RuntimeError(decode_payload(packet))

    if packet.packet_type != expected_type:
        raise RuntimeError("Unexpected response from server")

    return packet


def login(username, password):
    """Authenticate with the server."""
    payload = json.dumps({
        "username": username,
        "password": password,
    })

    udp.send_packet(make_packet(LOGIN_REQUEST, payload), SERVER_ADDRESS)
    response = receive_response(LOGIN_RESPONSE)

    return decode_payload(response) == "OK"


def list_files():
    """Return the list of files available on the server."""
    udp.send_packet(make_packet(LIST_REQUEST), SERVER_ADDRESS)
    response = receive_response(LIST_RESPONSE)
    payload = decode_payload(response)

    if not payload:
        return []

    return payload.splitlines()


def upload_file(path, filename=None):
    """Upload a local file to the server."""
    if filename is None:
        filename = os.path.basename(path)

    udp.send_packet(make_packet(UPLOAD_REQUEST, filename), SERVER_ADDRESS)
    response = receive_response(UPLOAD_REQUEST)

    if decode_payload(response) != "OK":
        return False

    udp.send_file(path, SERVER_ADDRESS)
    response = receive_response(UPLOAD_REQUEST)

    return decode_payload(response) == "OK"


def download_file(filename, destination_path=None):
    """Download a server file into downloads/ by default."""
    if destination_path is None:
        os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
        destination_path = os.path.join(DOWNLOADS_FOLDER, filename)

    udp.send_packet(make_packet(DOWNLOAD_REQUEST, filename), SERVER_ADDRESS)
    response = receive_response(DOWNLOAD_REQUEST)

    if decode_payload(response) != "OK":
        return False

    udp.receive_file(destination_path)
    return True
