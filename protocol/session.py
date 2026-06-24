from protocol.window import SlidingWindow


class Session:

    def __init__(self):

        self.window = SlidingWindow(4)

        self.expected_sequence = 1

        self.retransmissions = 0

        self.bytes_sent = 0

        self.bytes_received = 0

        self.rtt = []

        self.losses = 0