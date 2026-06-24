from protocol.sender import Sender
from protocol.receiver import Receiver
from protocol.session import Session
from protocol.fragment import fragment_data, join_fragments

from protocol.constants import *

from protocol.packet import Packet


class ReliableUDP:

    def __init__(self, socket):

        self.socket = socket

        self.session = Session()

        self.sender = Sender(socket, self.session)

        self.receiver = Receiver(socket, self.session)

    def send(self, packet_type, payload, address):

        return self.sender.send_packet(
            packet_type,
            payload,
            address
        )

    def receive(self):

        return self.receiver.receive_packet()

    def send_ack(self, sequence, payload, address, packet_type=SUCCESS):

        packet = Packet(
            packet_type=packet_type,
            sequence=0,
            ack=sequence,
            payload=payload
        )

        self.socket.sendto(
            packet.to_bytes(),
            address
        )

    def send_file(self, packet_type, data, address):

        fragments = fragment_data(data)

        print(f"Enviando {len(fragments)} fragmentos")

        for fragment in fragments:

            self.send(
                packet_type,
                fragment,
                address
            )

        self.send(
            FIN,
            b"",
            address
        )

    def receive_file(self):

        fragments = []

        while True:

            packet, address = self.receive()

            if packet.packet_type == FIN:

                self.send_ack(
                    packet.sequence,
                    b"FIN",
                    address,
                    ACK
                )

                break

            fragments.append(packet.payload)

            self.send_ack(
                packet.sequence,
                b"ACK",
                address,
                ACK
            )

        return join_fragments(fragments)