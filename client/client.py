from protocol.network import create_client_socket
from protocol.packet import Packet
from protocol.constants import *

client = create_client_socket()

packet = Packet(
    packet_type=LOGIN,
    sequence=1,
    ack=0,
    payload=b"Hola servidor"
)

client.sendto(
    packet.to_bytes(),
    (SERVER_HOST, SERVER_PORT)
)

data, _ = client.recvfrom(4096)

response = Packet.from_bytes(data)

print(response)