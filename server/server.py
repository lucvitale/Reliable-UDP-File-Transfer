import json

from protocol.constants import *
from protocol.network import create_server_socket
from protocol.reliable_udp import ReliableUDP
from protocol.packet import Packet
from server.file_manager import list_files, file_exists, read_file, write_file

server_socket = create_server_socket()
reliable = ReliableUDP(server_socket)

print("Servidor iniciado...")


with open("server/users.json", "r", encoding="utf-8") as file:
    users = json.load(file)


while True:

    packet, address = reliable.receive()

    print(
        f"[RX] Tipo={packet.packet_type} Seq={packet.sequence}"
    )

    if packet.packet_type == LOGIN:

        username, password = packet.payload.decode().split(":")

        if users.get(username) == password:

            reliable.send_ack(
                packet.sequence,
                b"LOGIN_OK",
                address,
                SUCCESS
            )

        else:

            reliable.send_ack(
                packet.sequence,
                b"LOGIN_ERROR",
                address,
                ERROR
            )

    elif packet.packet_type == LIST:

        files = "\n".join(list_files())

        reliable.send_ack(
            packet.sequence,
            files.encode(),
            address,
            SUCCESS
        )

    elif packet.packet_type == DOWNLOAD:

        filename = packet.payload.decode()

        if file_exists(filename):

            reliable.send_ack(
                packet.sequence,
                read_file(filename),
                address,
                DATA
            )

        else:

            reliable.send_ack(
                packet.sequence,
                b"FILE_NOT_FOUND",
                address,
                ERROR
            )

    elif packet.packet_type == UPLOAD:

        filename, content = packet.payload.split(b"||", 1)

        filename = filename.decode()

        write_file(filename, content)

        reliable.send_ack(
            packet.sequence,
            b"UPLOAD_OK",
            address,
            SUCCESS
        )