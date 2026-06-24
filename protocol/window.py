class SlidingWindow:

    def __init__(self, size=4):

        self.size = size

        self.base = 1

        self.next_sequence = 1

        self.pending = {}

    def can_send(self):

        return self.next_sequence < self.base + self.size

    def add(self, packet):

        self.pending[self.next_sequence] = packet

        self.next_sequence += 1

    def ack(self, sequence):

        if sequence in self.pending:

            del self.pending[sequence]

        while self.base not in self.pending and self.base < self.next_sequence:

            self.base += 1

    def timeout_packets(self):

        return list(self.pending.values())