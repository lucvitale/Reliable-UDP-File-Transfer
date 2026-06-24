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
from server import file_manager


USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")
INVALID_FILENAME = "ERROR: invalid filename"


def load_users():
    """Load valid username/password pairs from server/users.json."""
    with open(USERS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def make_packet(packet_type, payload):
    """Build a Packet from text or bytes payload."""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")

    return Packet(packet_type, 0, 0, payload)


def decode_payload(packet):
    """Decode request payloads as UTF-8 text."""
    return packet.payload.decode("utf-8").strip()


def send_response(udp, address, packet_type, payload):
    """Send every server response through ReliableUDP."""
    udp.send_packet(make_packet(packet_type, payload), address)


def parse_login(payload):
    """Parse login credentials from JSON or username:password text."""
    try:
        data = json.loads(payload)
        if not isinstance(data, dict):
            return "", ""

        return data.get("username", ""), data.get("password", "")
    except json.JSONDecodeError:
        if ":" not in payload:
            return "", ""

        username, password = payload.split(":", 1)
        return username.strip(), password.strip()


def is_safe_filename(filename):
    """Reject paths so clients can only address files inside shared/."""
    if not filename:
        return False

    if filename in {".", ".."}:
        return False

    if os.path.isabs(filename):
        return False

    if filename != os.path.basename(filename):
        return False

    # Avoid Windows drive names, alternate streams, and embedded null bytes.
    return ":" not in filename and "\x00" not in filename


def get_shared_path(filename):
    """Return an absolute path inside shared/ or None for invalid names."""
    if not is_safe_filename(filename):
        return None

    shared_root = os.path.abspath(file_manager.SHARED_FOLDER)
    path = os.path.abspath(os.path.join(shared_root, filename))

    if os.path.dirname(path) != shared_root:
        return None

    return path


def handle_login(udp, address, packet, users):
    username, password = parse_login(decode_payload(packet))

    if users.get(username) == password:
        send_response(udp, address, LOGIN_RESPONSE, "OK")
        return True

    send_response(udp, address, LOGIN_RESPONSE, "ERROR: invalid credentials")
    return False


def handle_list(udp, address):
    files = file_manager.list_files()
    payload = "\n".join(files)
    send_response(udp, address, LIST_RESPONSE, payload)


def handle_upload(udp, address, packet):
    filename = decode_payload(packet)
    path = get_shared_path(filename)

    if path is None:
        send_response(udp, address, ERROR, INVALID_FILENAME)
        return

    send_response(udp, address, UPLOAD_REQUEST, "OK")

    udp.receive_file(path)
    send_response(udp, address, UPLOAD_REQUEST, "OK")


def handle_download(udp, address, packet):
    filename = decode_payload(packet)
    path = get_shared_path(filename)

    if path is None:
        send_response(udp, address, ERROR, INVALID_FILENAME)
        return

    if not file_manager.file_exists(filename):
        send_response(udp, address, ERROR, "ERROR: file not found")
        return

    send_response(udp, address, DOWNLOAD_REQUEST, "OK")
    udp.send_file(path, address)


def handle_request(udp, address, packet, users, logged_clients):
    try:
        if packet.packet_type == LOGIN_REQUEST:
            if handle_login(udp, address, packet, users):
                logged_clients.add(address)
            return

        if address not in logged_clients:
            send_response(udp, address, ERROR, "ERROR: login required")
            return

        if packet.packet_type == LIST_REQUEST:
            handle_list(udp, address)
            return

        if packet.packet_type == UPLOAD_REQUEST:
            handle_upload(udp, address, packet)
            return

        if packet.packet_type == DOWNLOAD_REQUEST:
            handle_download(udp, address, packet)
            return

        send_response(udp, address, ERROR, "ERROR: unknown request")
    except UnicodeDecodeError:
        send_response(udp, address, ERROR, "ERROR: invalid text payload")


def main():
    users = load_users()
    logged_clients = set()
    udp = ReliableUDP(bind_address=(SERVER_HOST, SERVER_PORT))

    os.makedirs(file_manager.SHARED_FOLDER, exist_ok=True)

    try:
        while True:
            packet, address = udp.receive_packet()
            handle_request(udp, address, packet, users, logged_clients)
    finally:
        udp.sock.close()


if __name__ == "__main__":
    main()
