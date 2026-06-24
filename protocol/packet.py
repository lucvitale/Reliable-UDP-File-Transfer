from dataclasses import dataclass
import struct

from protocol.checksum import calculate_checksum, verify_checksum

HEADER_FORMAT = "!BIIH64s"

HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


@dataclass
class Packet:
    packet_type: int
    sequence: int
    ack: int
    payload: bytes

    def to_bytes(self):

        checksum = calculate_checksum(self.payload).encode()

        header = struct.pack(
            HEADER_FORMAT,
            self.packet_type,
            self.sequence,
            self.ack,
            len(self.payload),
            checksum
        )

        return header + self.payload

    @staticmethod
    def from_bytes(data: bytes):

        header = data[:HEADER_SIZE]
        payload = data[HEADER_SIZE:]

        packet_type, sequence, ack, payload_length, checksum = struct.unpack(
            HEADER_FORMAT,
            header
        )

        payload = payload[:payload_length]

        checksum = checksum.decode().rstrip("\x00")

        if not verify_checksum(payload, checksum):
            raise ValueError("Checksum inválido")

        return Packet(
            packet_type,
            sequence,
            ack,
            payload
        )