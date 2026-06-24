from dataclasses import dataclass
import struct

HEADER_FORMAT = "!BIIH"

"""
!  -> Network Byte Order (Big Endian)
B  -> unsigned char (1 byte)   -> packet_type
I  -> unsigned int  (4 bytes)  -> sequence
I  -> unsigned int  (4 bytes)  -> ack
H  -> unsigned short (2 bytes) -> payload_length
"""

HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


@dataclass
class Packet:
    packet_type: int
    sequence: int
    ack: int
    payload: bytes

    def to_bytes(self):
        header = struct.pack(
            HEADER_FORMAT,
            self.packet_type,
            self.sequence,
            self.ack,
            len(self.payload)
        )

        return header + self.payload

    @staticmethod
    def from_bytes(data: bytes):

        header = data[:HEADER_SIZE]
        payload = data[HEADER_SIZE:]

        packet_type, sequence, ack, payload_length = struct.unpack(
            HEADER_FORMAT,
            header
        )

        payload = payload[:payload_length]

        return Packet(
            packet_type,
            sequence,
            ack,
            payload
        )