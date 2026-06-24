import socket

from protocol.packet import Packet
from protocol.constants import *


class ReliableUDP:

    def __init__(self, sock: socket.socket):

        self.socket = sock

        self.sequence = 1

    def send(self, packet_type, payload, address):

        retries = 0

        while retries < MAX_RETRIES:

            packet = Packet(
                packet_type=packet_type,
                sequence=self.sequence,
                ack=0,
                payload=payload
            )

            self.socket.sendto(packet.to_bytes(), address)

            try:

                data, addr = self.socket.recvfrom(BUFFER_SIZE)

                response = Packet.from_bytes(data)

                if response.ack == self.sequence:

                    self.sequence += 1

                    return response

            except socket.timeout:

                retries += 1

                print(f"Timeout. Reintentando ({retries}/{MAX_RETRIES})...")

        raise TimeoutError("No se recibió ACK.")

    def receive(self):

        data, address = self.socket.recvfrom(BUFFER_SIZE)

        packet = Packet.from_bytes(data)

        return packet, address

    def send_ack(self, sequence, payload, address, packet_type=SUCCESS):

        packet = Packet(
            packet_type=packet_type,
            sequence=0,
            ack=sequence,
            payload=payload
        )

        self.socket.sendto(packet.to_bytes(), address)