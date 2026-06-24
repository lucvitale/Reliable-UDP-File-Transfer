import socket

from protocol.constants import *


def create_server_socket():

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.bind((SERVER_HOST, SERVER_PORT))

    sock.settimeout(None)

    return sock


def create_client_socket():

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.settimeout(TIMEOUT)

    return sock