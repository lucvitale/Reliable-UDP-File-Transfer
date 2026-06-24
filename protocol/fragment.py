from protocol.constants import PACKET_SIZE


def fragment_data(data: bytes):

    fragments = []

    for i in range(0, len(data), PACKET_SIZE):

        fragments.append(data[i:i + PACKET_SIZE])

    return fragments


def join_fragments(fragments):

    return b"".join(fragments)