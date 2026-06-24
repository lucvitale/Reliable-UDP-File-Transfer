class Session:

    def __init__(self):

        self.sequence = 1

        self.expected_sequence = 1

        self.retransmissions = 0

        self.bytes_sent = 0

        self.bytes_received = 0