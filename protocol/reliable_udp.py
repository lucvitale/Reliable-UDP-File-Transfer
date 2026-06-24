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
    WINDOW_SIZE,
)
from protocol.packet import Packet


class ReliableUDP:
    """Go-Back-N reliable transport built on top of UDP.

    The public API remains intentionally small. Internally the sender keeps a
    sliding window of unacknowledged packets and retransmits the whole window
    when the oldest unacknowledged packet times out.
    """

    def __init__(
        self,
        sock=None,
        bind_address=None,
        timeout=TIMEOUT,
        max_retries=MAX_RETRIES,
        window_size=WINDOW_SIZE,
    ):
        """Create a reliable UDP endpoint.

        Args:
            sock: Optional UDP socket. When omitted, a new socket is created.
            bind_address: Optional local address tuple for server-style use.
            timeout: ACK wait timeout in seconds.
            max_retries: Number of whole-window retransmission rounds.
            window_size: Maximum number of outstanding packets.
        """
        self.sock = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if bind_address is not None:
            self.sock.bind(bind_address)

        self.timeout = timeout
        self.max_retries = max_retries
        self.window_size = window_size

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
            "duplicate_acks": 0,
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

        ACK packets are control packets and are sent once. Every other packet
        uses the same Go-Back-N sender as file transfers, with a one-packet
        batch.
        """
        if packet.packet_type == ACK:
            self._send_raw(packet, address)
            self.stats["acks_sent"] += 1
            return True

        self._send_packets_go_back_n([packet], address)
        return True

    def receive_packet(self):
        """Receive the next in-order non-ACK packet.

        Duplicate packets are ACKed again and discarded. Out-of-order packets are
        not delivered in Go-Back-N; the receiver repeats the last cumulative ACK.
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

        packets = [
            Packet(DATA, 0, 0, payload)
            for payload in self._fragment_data(data)
        ]
        packets.append(Packet(FIN, 0, 0, b""))

        self._send_packets_go_back_n(packets, address)
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

    def _send_packets_go_back_n(self, packets, address):
        """Send packets with a Go-Back-N sliding window."""
        if not packets:
            return

        window_size = max(1, self.window_size)
        start_sequence = self.next_sequence
        prepared = [
            replace(packet, sequence=start_sequence + index)
            for index, packet in enumerate(packets)
        ]

        base_index = 0
        next_index = 0
        retries = 0
        unacked = {}

        old_timeout = self.sock.gettimeout()

        try:
            while base_index < len(prepared):
                next_index = self._fill_window(
                    prepared,
                    base_index,
                    next_index,
                    window_size,
                    address,
                    unacked,
                )

                remaining = self._time_until_oldest_timeout(
                    prepared,
                    base_index,
                    unacked,
                )

                if remaining <= 0:
                    retries = self._retransmit_window(
                        prepared,
                        base_index,
                        next_index,
                        address,
                        unacked,
                        retries,
                    )
                    continue

                self.sock.settimeout(remaining)

                try:
                    packet, sender = self._recv_valid_packet()
                except socket.timeout:
                    retries = self._retransmit_window(
                        prepared,
                        base_index,
                        next_index,
                        address,
                        unacked,
                        retries,
                    )
                    continue

                if self._is_ack(packet):
                    if sender != address:
                        continue

                    base_index, retries = self._handle_ack(
                        packet.ack,
                        prepared,
                        base_index,
                        next_index,
                        unacked,
                        retries,
                    )
                    continue

                if self._process_incoming_packet(packet, sender):
                    self.pending_packets.append((packet, sender))
        finally:
            self.sock.settimeout(old_timeout)

        self.next_sequence = start_sequence + len(prepared)

    def _fill_window(
        self,
        prepared,
        base_index,
        next_index,
        window_size,
        address,
        unacked,
    ):
        """Send new packets until the Go-Back-N window is full."""
        window_end = base_index + window_size

        while next_index < len(prepared) and next_index < window_end:
            self._send_and_track(
                prepared[next_index],
                address,
                unacked,
                retransmitted=False,
            )
            next_index += 1

        return next_index

    def _time_until_oldest_timeout(self, prepared, base_index, unacked):
        """Return seconds left before the oldest unacked packet times out."""
        oldest_sequence = prepared[base_index].sequence
        oldest_sent_at = unacked[oldest_sequence]["sent_at"]
        return self.timeout - (time.monotonic() - oldest_sent_at)

    def _handle_ack(
        self,
        ack,
        prepared,
        base_index,
        next_index,
        unacked,
        retries,
    ):
        """Apply a cumulative ACK and return updated base/retry values."""
        new_base = self._apply_cumulative_ack(
            ack,
            prepared,
            base_index,
            next_index,
            unacked,
        )

        if new_base == base_index:
            self.stats["duplicate_acks"] += 1
            return base_index, retries

        return new_base, 0

    def _retransmit_window(
        self,
        prepared,
        base_index,
        next_index,
        address,
        unacked,
        retries,
    ):
        """Retransmit every outstanding packet after the oldest timeout."""
        if retries >= self.max_retries:
            sequence = prepared[base_index].sequence
            raise TimeoutError(f"No cumulative ACK received for packet {sequence}")

        self.stats["timeouts"] += 1

        for index in range(base_index, next_index):
            self._send_and_track(
                prepared[index],
                address,
                unacked,
                retransmitted=True,
            )
            self.stats["retransmissions"] += 1

        return retries + 1

    def _send_and_track(self, packet, address, unacked, retransmitted):
        """Send a packet and remember ACK/RTT state for it."""
        self._send_raw(packet, address)
        unacked[packet.sequence] = {
            "sent_at": time.monotonic(),
            "retransmitted": retransmitted,
        }

    def _apply_cumulative_ack(
        self,
        ack,
        prepared,
        base_index,
        next_index,
        unacked,
    ):
        """Move the send base after a cumulative ACK."""
        if ack < prepared[base_index].sequence:
            return base_index

        highest_sent = prepared[next_index - 1].sequence
        ack = min(ack, highest_sent)
        new_base = base_index

        while new_base < next_index and prepared[new_base].sequence <= ack:
            sequence = prepared[new_base].sequence
            state = unacked.pop(sequence, None)

            if state is not None and not state["retransmitted"]:
                self._record_rtt(state["sent_at"])

            new_base += 1

        return new_base

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
