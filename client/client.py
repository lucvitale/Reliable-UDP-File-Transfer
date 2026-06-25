import json
import os
import socket
import time

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
    CDN_SERVERS_REQUEST,
    CDN_SERVERS_RESPONSE,
    CDN_PING_REQUEST,
    CDN_PING_RESPONSE,
)
from protocol.packet import Packet
from protocol.reliable_udp import ReliableUDP


SERVER_ADDRESS = (SERVER_HOST, SERVER_PORT)
DOWNLOADS_FOLDER = "downloads"


udp = ReliableUDP()
server_selected = False


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
    return receive_with(udp, expected_type, SERVER_ADDRESS)


def receive_with(transport, expected_type, server_address):
    """Receive one response using a specific temporary transport."""
    packet, address = transport.receive_packet()

    if address != server_address:
        raise RuntimeError("Received packet from unknown server")

    if packet.packet_type == ERROR:
        raise RuntimeError(decode_payload(packet))

    if packet.packet_type != expected_type:
        raise RuntimeError("Unexpected response from server")

    return packet


def send_cdn_request(packet_type, address):
    """Send one Mini-CDN request over plain UDP and return packet, address, RTT."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)

    try:
        request = make_packet(packet_type)

        started_at = time.perf_counter()
        sock.sendto(request.to_bytes(), address)
        data, sender = sock.recvfrom(4096)
        finished_at = time.perf_counter()

        rtt = finished_at - started_at

        print("Inicio :", started_at)
        print("Fin    :", finished_at)
        print("RTT    :", rtt)

        return Packet.from_bytes(data), sender, rtt
    finally:
        sock.close()


def request_candidate_servers():
    """Ask the bootstrap server for CDN candidates."""
    response, address, _ = send_cdn_request(CDN_SERVERS_REQUEST, SERVER_ADDRESS)

    if address != SERVER_ADDRESS:
        raise RuntimeError("Received CDN response from unknown server")

    if response.packet_type != CDN_SERVERS_RESPONSE:
        raise RuntimeError("Unexpected CDN server list response")

    candidates = json.loads(decode_payload(response))

    return [
        (candidate["host"], int(candidate["port"]))
        for candidate in candidates
    ]


def measure_rtt(address):
    """Measure request/response RTT to one candidate server."""
    response, sender, rtt = send_cdn_request(CDN_PING_REQUEST, address)

    if sender != address:
        raise RuntimeError("Received CDN ping from unknown server")

    if response.packet_type != CDN_PING_RESPONSE:
        raise RuntimeError("Unexpected CDN ping response")

    return rtt


def select_best_server():
    """Select the CDN server with the lowest measured RTT."""
    global SERVER_ADDRESS
    global server_selected
    global udp

    print("1 - Pidiendo candidatos")
    candidates = request_candidate_servers()
    print("2 - Candidatos:", candidates)

    measurements = []

    for address in candidates:
        print("3 - Midiendo", address)
        try:
            rtt = measure_rtt(address)
            print(repr(rtt))
            measurements.append((rtt, address))
        except (TimeoutError, RuntimeError, OSError) as e:
            print("5 - Error:", e)

    print("6 - Measurements:", measurements)

    if not measurements:
        raise RuntimeError("No CDN server available")

    _, SERVER_ADDRESS = min(measurements, key=lambda item: item[0])

    print("7 - Seleccionado:", SERVER_ADDRESS)

    udp.sock.close()
    udp = ReliableUDP()
    server_selected = True

    return SERVER_ADDRESS


def ensure_server_selected():
    """Run CDN selection once before the first application request."""
    if not server_selected:
        select_best_server()


def login(username, password):
    """Authenticate with the server."""
    ensure_server_selected()

    payload = json.dumps({
        "username": username,
        "password": password,
    })

    udp.send_packet(make_packet(LOGIN_REQUEST, payload), SERVER_ADDRESS)
    response = receive_response(LOGIN_RESPONSE)

    return decode_payload(response) == "OK"


def list_files():
    """Return the list of files available on the server."""
    ensure_server_selected()

    udp.send_packet(make_packet(LIST_REQUEST), SERVER_ADDRESS)
    response = receive_response(LIST_RESPONSE)
    payload = decode_payload(response)

    if not payload:
        return []

    return payload.splitlines()


def upload_file(path, filename=None):
    """Upload a local file to the server."""
    ensure_server_selected()

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
    ensure_server_selected()

    if destination_path is None:
        os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
        destination_path = os.path.join(DOWNLOADS_FOLDER, filename)

    udp.send_packet(make_packet(DOWNLOAD_REQUEST, filename), SERVER_ADDRESS)
    response = receive_response(DOWNLOAD_REQUEST)

    if decode_payload(response) != "OK":
        return False

    udp.receive_file(destination_path)
    return True
