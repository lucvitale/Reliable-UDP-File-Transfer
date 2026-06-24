import json

from protocol.network import create_server_socket
from protocol.packet import Packet
from protocol.constants import *
from server.file_manager import list_files, file_exists, read_file, write_file

server = create_server_socket()

print("Servidor iniciado...")

with open("server/users.json", "r", encoding="utf-8") as file:
    users = json.load(file)

while True:

    data, address = server.recvfrom(BUFFER_SIZE)

    packet = Packet.from_bytes(data)
    print(
    f"Recibido -> Tipo:{packet.packet_type} Seq:{packet.sequence}"
    )

    if packet.packet_type == LOGIN:

        username, password = packet.payload.decode().split(":")

        if users.get(username) == password:

            response = Packet(
                packet_type=SUCCESS,
                sequence=0,
                ack=packet.sequence,
                payload=b"LOGIN_OK"
            )

        else:

            response = Packet(
                packet_type=ERROR,
                sequence=0,
                ack=packet.sequence,
                payload=b"LOGIN_ERROR"
            )

        server.sendto(response.to_bytes(), address)

    elif packet.packet_type == LIST:

        files = list_files()

        response = Packet(
            packet_type=SUCCESS,
            sequence=0,
            ack=packet.sequence,
            payload="\n".join(files).encode()
        )

        server.sendto(response.to_bytes(), address)

    elif packet.packet_type == DOWNLOAD:

        filename = packet.payload.decode()

        if not file_exists(filename):

            response = Packet(
                packet_type=ERROR,
                sequence=0,
                ack=packet.sequence,
                payload=b"FILE_NOT_FOUND"
            )

        else:

            content = read_file(filename)

            response = Packet(
                packet_type=DATA,
                sequence=0,
                ack=packet.sequence,
                payload=content
            )

        server.sendto(response.to_bytes(), address)

    elif packet.packet_type == UPLOAD:

        filename, content = packet.payload.split(b"||", 1)

        filename = filename.decode()

        write_file(filename, content)

        response = Packet(
            packet_type=SUCCESS,
            sequence=0,
            ack=packet.sequence,
            payload=b"UPLOAD_OK"
        )

        server.sendto(response.to_bytes(), address)