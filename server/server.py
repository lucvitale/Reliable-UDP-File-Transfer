from protocol.network import create_server_socket
from protocol.packet import Packet
from protocol.constants import SUCCESS

server = create_server_socket()

print("Servidor iniciado...")

while True:

    data, address = server.recvfrom(4096)

    packet = Packet.from_bytes(data)

    print(f"Recibido: {packet}")

    response = Packet(
        packet_type=SUCCESS,
        sequence=0,
        ack=packet.sequence,
        payload=b"OK"
    )

    server.sendto(response.to_bytes(), address)