import json
import os

from protocol.network import create_server_socket
from protocol.packet import Packet
from protocol.constants import *

server = create_server_socket()

print("Servidor iniciado...")

with open("server/users.json", "r", encoding="utf-8") as file:
    users = json.load(file)

while True:

    data, address = server.recvfrom(BUFFER_SIZE)

    packet = Packet.from_bytes(data)

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

        files = os.listdir("shared")

        response = Packet(
            packet_type=SUCCESS,
            sequence=0,
            ack=packet.sequence,
            payload="\n".join(files).encode()
        )

        server.sendto(response.to_bytes(), address)

    elif packet.packet_type == DOWNLOAD:

        filename = packet.payload.decode()
        filepath = os.path.join("shared", filename)

        if not os.path.exists(filepath):

            response = Packet(
                packet_type=ERROR,
                sequence=0,
                ack=packet.sequence,
                payload=b"FILE_NOT_FOUND"
            )

        else:

            with open(filepath, "rb") as file:
                content = file.read()

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

        with open(os.path.join("shared", filename), "wb") as file:
            file.write(content)

        response = Packet(
            packet_type=SUCCESS,
            sequence=0,
            ack=packet.sequence,
            payload=b"UPLOAD_OK"
        )

        server.sendto(response.to_bytes(), address)