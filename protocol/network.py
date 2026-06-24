import socket

from protocol.constants import SERVER_HOST, SERVER_PORT


def create_server_socket():

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.bind((SERVER_HOST, SERVER_PORT))

    return sock


def create_client_socket():

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    return sock