import os
import socket
import time
from collections import deque
from dataclasses import replace

from protocol.constants import (
    ACK,
    BUFFER_SIZE,
    DATA,
    FIN,
    FRAGMENT_SIZE,
    MAX_RETRIES,
    TIMEOUT,
)
from protocol.packet import Packet


class ReliableUDP:
    """Stop-and-Wait reliable transport built on top of UDP.

    The class keeps the public API intentionally small. It sends one packet at a
    time, waits for its ACK, retransmits on timeout, and accepts only the next
    expected sequence number from each peer.
    """

    def __init__(
        self,
        sock=None,
        bind_address=None,
        timeout=TIMEOUT,
        max_retries=MAX_RETRIES,
    ):
        """Create a reliable UDP endpoint.

        Args:
            sock: Optional UDP socket. When omitted, a new socket is created.
            bind_address: Optional local address tuple for server-style use.
            timeout: ACK wait timeout in seconds.
            max_retries: Number of retransmission attempts after the first send.
        """
        self.sock = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if bind_address is not None:
            self.sock.bind(bind_address)

        self.timeout = timeout
        self.max_retries = max_retries

        self.next_sequence = 1
        self.expected_sequence = {}
        self.pending_packets = deque()

        self.stats = {
            "packets_sent": 0,
            "packets_received": 0,
            "acks_sent": 0,
            "acks_received": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "retransmissions": 0,
            "duplicates": 0,
            "timeouts": 0,
            "checksum_errors": 0,
            "rtt_samples": [],
            "last_rtt": 0.0,
            "average_rtt": 0.0,
            "throughput_bps": 0.0,
            "transfer_start": None,
            "transfer_end": None,
        }

    def send_packet(self, packet, address):
        """Send one packet reliably to address.

        DATA, FIN, and application packets use Stop-and-Wait. ACK packets are
        control packets and are sent once without waiting for another ACK.
        """
        if packet.packet_type == ACK:
            self._send_raw(packet, address)
            self.stats["acks_sent"] += 1
            return True

        sequence = self.next_sequence
        reliable_packet = replace(packet, sequence=sequence)

        for attempt in range(self.max_retries + 1):
            sent_at = time.monotonic()
            self._send_raw(reliable_packet, address)

            if attempt > 0:
                self.stats["retransmissions"] += 1

            if self._wait_for_ack(sequence, address, sent_at):
                self.next_sequence += 1
                return True

            self.stats["timeouts"] += 1

        raise TimeoutError(f"No ACK received for packet {sequence}")

    def receive_packet(self):
        """Receive the next in-order non-ACK packet.

        Duplicate packets are ACKed again and discarded. Out-of-order packets are
        not delivered in Stop-and-Wait; the receiver repeats the last valid ACK.
        """
        if self.pending_packets:
            return self.pending_packets.popleft()

        while True:
            packet, address = self._recv_valid_packet()

            if self._is_ack(packet):
                continue

            if self._process_incoming_packet(packet, address):
                return packet, address

    def send_file(self, path, address):
        """Send a file as DATA packets followed by a FIN packet."""
        self._start_transfer()

        with open(path, "rb") as file:
            data = file.read()

        for payload in self._fragment_data(data):
            self.send_packet(Packet(DATA, 0, 0, payload), address)

        self.send_packet(Packet(FIN, 0, 0, b""), address)
        self._finish_transfer()

        return self.get_statistics()

    def receive_file(self, path):
        """Receive DATA packets until FIN and write them to path."""
        self._start_transfer()

        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(path, "wb") as file:
            while True:
                packet, address = self.receive_packet()

                if packet.packet_type == DATA:
                    file.write(packet.payload)
                    continue

                if packet.packet_type == FIN:
                    self._finish_transfer()
                    return address, self.get_statistics()

    def get_statistics(self):
        """Return a copy of transfer counters and derived measurements."""
        stats = dict(self.stats)
        samples = stats["rtt_samples"]

        stats["average_rtt"] = sum(samples) / len(samples) if samples else 0.0
        stats["throughput_bps"] = self._calculate_throughput()
        stats["rtt_samples"] = list(samples)

        return stats

    def _wait_for_ack(self, sequence, address, sent_at):
        """Wait for the matching ACK while still handling incoming duplicates."""
        old_timeout = self.sock.gettimeout()
        self.sock.settimeout(self.timeout)

        try:
            while True:
                try:
                    packet, sender = self._recv_valid_packet()
                except socket.timeout:
                    return False

                if self._is_ack(packet):
                    if sender == address and packet.ack == sequence:
                        self._record_rtt(sent_at)
                        return True
                    continue

                if self._process_incoming_packet(packet, sender):
                    self.pending_packets.append((packet, sender))
        finally:
            self.sock.settimeout(old_timeout)

    def _process_incoming_packet(self, packet, address):
        """ACK and classify a received non-ACK packet.

        Returns True only when the packet is the next expected packet and can be
        delivered. Duplicate and out-of-order packets are handled but not
        delivered.
        """
        expected = self.expected_sequence.get(address, 1)

        if packet.sequence == expected:
            self._send_ack(packet.sequence, address)
            self.expected_sequence[address] = expected + 1
            self._record_receive(packet)
            return True

        if packet.sequence < expected:
            self.stats["duplicates"] += 1
            self._send_ack(packet.sequence, address)
            return False

        self._repeat_last_ack(expected, address)
        return False

    def _recv_valid_packet(self):
        """Receive bytes and deserialize packets, dropping corrupt datagrams."""
        while True:
            data, address = self.sock.recvfrom(BUFFER_SIZE)

            try:
                return Packet.from_bytes(data), address
            except ValueError:
                self.stats["checksum_errors"] += 1

    def _is_ack(self, packet):
        if packet.packet_type == ACK:
            self.stats["acks_received"] += 1
            return True

        return False

    def _send_ack(self, sequence, address):
        ack_packet = Packet(ACK, 0, sequence, b"")
        self._send_raw(ack_packet, address)
        self.stats["acks_sent"] += 1

    def _repeat_last_ack(self, expected, address):
        last_received = expected - 1

        if last_received >= 1:
            self._send_ack(last_received, address)

    def _send_raw(self, packet, address):
        data = packet.to_bytes()
        self.sock.sendto(data, address)

        self.stats["packets_sent"] += 1
        self.stats["bytes_sent"] += len(packet.payload)
        self._mark_transfer_activity()

    def _record_receive(self, packet):
        self.stats["packets_received"] += 1
        self.stats["bytes_received"] += len(packet.payload)
        self._mark_transfer_activity()

    def _record_rtt(self, sent_at):
        rtt = time.monotonic() - sent_at
        self.stats["last_rtt"] = rtt
        self.stats["rtt_samples"].append(rtt)

    def _fragment_data(self, data):
        """Split data into payload-sized chunks, preserving empty files."""
        if not data:
            return [b""]

        return [
            data[index:index + FRAGMENT_SIZE]
            for index in range(0, len(data), FRAGMENT_SIZE)
        ]

    def _start_transfer(self):
        now = time.monotonic()
        self.stats["transfer_start"] = now
        self.stats["transfer_end"] = now

    def _finish_transfer(self):
        self.stats["transfer_end"] = time.monotonic()
        self.stats["throughput_bps"] = self._calculate_throughput()

    def _mark_transfer_activity(self):
        now = time.monotonic()

        if self.stats["transfer_start"] is None:
            self.stats["transfer_start"] = now

        self.stats["transfer_end"] = now

    def _calculate_throughput(self):
        start = self.stats["transfer_start"]
        end = self.stats["transfer_end"]

        if start is None or end is None or end <= start:
            return 0.0

        total_bytes = self.stats["bytes_sent"] + self.stats["bytes_received"]
        return total_bytes / (end - start)
