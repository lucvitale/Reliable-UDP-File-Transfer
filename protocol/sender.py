import socket
import time

from protocol.packet import Packet
from protocol.constants import *


class Sender:

    def __init__(self, socket, session):

        self.socket = socket
        self.session = session

    def send_packet(self, packet_type, payload, address):

        while not self.session.window.can_send():
            self.process_ack()

        sequence = self.session.window.next_sequence

        packet = Packet(
            packet_type=packet_type,
            sequence=sequence,
            ack=0,
            payload=payload
        )

        self.session.window.add(packet)

        send_time = time.time()

        self.socket.sendto(
            packet.to_bytes(),
            address
        )

        self.session.bytes_sent += len(payload)

        retries = 0

        while retries < MAX_RETRIES:

            try:

                data, _ = self.socket.recvfrom(BUFFER_SIZE)

                response = Packet.from_bytes(data)

                if response.packet_type == ACK:

                    self.session.window.ack(response.ack)

                    rtt = time.time() - send_time

                    self.session.rtt.append(rtt)

                    return response

            except socket.timeout:

                retries += 1

                self.session.retransmissions += 1

                print(f"Timeout -> retransmisión {retries}")

                for pending in self.session.window.timeout_packets():

                    self.socket.sendto(
                        pending.to_bytes(),
                        address
                    )

        raise TimeoutError("Máximo de retransmisiones alcanzado.")

    def process_ack(self):

        try:

            data, _ = self.socket.recvfrom(BUFFER_SIZE)

            packet = Packet.from_bytes(data)

            if packet.packet_type == ACK:

                self.session.window.ack(packet.ack)

        except socket.timeout:

            pass