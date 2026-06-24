from protocol.network import create_client_socket
from protocol.packet import Packet
from protocol.constants import *

client = create_client_socket()

username = "admin"
password = "1234"

packet = Packet(
    packet_type=LOGIN,
    sequence=1,
    ack=0,
    payload=f"{username}:{password}".encode()
)

client.sendto(
    packet.to_bytes(),
    (SERVER_HOST, SERVER_PORT)
)

data, _ = client.recvfrom(BUFFER_SIZE)

response = Packet.from_bytes(data)

print(response)