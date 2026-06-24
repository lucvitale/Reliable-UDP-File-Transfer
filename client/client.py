from protocol.network import create_client_socket
from protocol.packet import Packet
from protocol.constants import *

client = create_client_socket()

filename = "cliente.txt"

with open(f"downloads/{filename}", "rb") as file:
    content = file.read()

payload = filename.encode() + b"||" + content

packet = Packet(
    packet_type=UPLOAD,
    sequence=1,
    ack=0,
    payload=payload
)

client.sendto(
    packet.to_bytes(),
    (SERVER_HOST, SERVER_PORT)
)

data, _ = client.recvfrom(BUFFER_SIZE)

response = Packet.from_bytes(data)
print(
    f"ACK recibido: {response.ack}"
)

print(response.payload.decode())