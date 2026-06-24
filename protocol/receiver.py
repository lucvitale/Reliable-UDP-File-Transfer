from protocol.packet import Packet


class Receiver:

    def __init__(self, socket, session):

        self.socket = socket

        self.session = session

    def receive_packet(self):

        data, address = self.socket.recvfrom(4096)

        packet = Packet.from_bytes(data)

        self.session.bytes_received += len(packet.payload)

        return packet, address