import json

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