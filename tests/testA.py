from protocol.packet import Packet

packet = Packet(
    packet_type=1,
    sequence=15,
    ack=10,
    payload=b"Hola Mundo"
)

raw = packet.to_bytes()

print(raw)

received = Packet.from_bytes(raw)

print(received)