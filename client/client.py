from protocol.constants import *
from protocol.network import create_client_socket
from protocol.reliable_udp import ReliableUDP

client_socket = create_client_socket()

reliable = ReliableUDP(client_socket)

filename = "cliente.txt"

with open(f"downloads/{filename}", "rb") as file:
    content = file.read()

payload = filename.encode() + b"||" + content

response = reliable.send(
    packet_type=UPLOAD,
    payload=payload,
    address=(SERVER_HOST, SERVER_PORT)
)

print()

print("Respuesta del servidor")

print("----------------------")

print("ACK :", response.ack)

print("Tipo:", response.packet_type)

print(response.payload.decode())