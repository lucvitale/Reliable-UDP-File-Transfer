import socket

from protocol.packet import Packet
from protocol.constants import *


class Sender:

    def __init__(self, socket, session):

        self.socket = socket

        self.session = session

    def send_packet(self, packet_type, payload, address):

        packet = Packet(
            packet_type=packet_type,
            sequence=self.session.sequence,
            ack=0,
            payload=payload
        )

        retries = 0

        while retries < MAX_RETRIES:

            self.socket.sendto(
                packet.to_bytes(),
                address
            )

            try:

                data, _ = self.socket.recvfrom(BUFFER_SIZE)

                response = Packet.from_bytes(data)

                if response.ack == self.session.sequence:

                    self.session.sequence += 1

                    self.session.bytes_sent += len(payload)

                    return response

            except socket.timeout:

                retries += 1

                self.session.retransmissions += 1

        raise TimeoutError()