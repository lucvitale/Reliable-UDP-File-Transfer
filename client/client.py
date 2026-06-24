from protocol.network import create_client_socket
from protocol.packet import Packet
from protocol.constants import *

client = create_client_socket()

filename = "mensaje.txt"

packet = Packet(
    packet_type=DOWNLOAD,
    sequence=1,
    ack=0,
    payload=filename.encode()
)

client.sendto(
    packet.to_bytes(),
    (SERVER_HOST, SERVER_PORT)
)

data, _ = client.recvfrom(BUFFER_SIZE)

response = Packet.from_bytes(data)

if response.packet_type == DATA:

    with open(f"downloads/{filename}", "wb") as file:
        file.write(response.payload)

    print("Archivo descargado correctamente.")

else:

    print(response.payload.decode())