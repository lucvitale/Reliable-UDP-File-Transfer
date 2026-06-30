import hashlib
import multiprocessing
import os
import time

from client import client
from server import server


TEST_FILENAME = "integration_test.txt"
TEST_CONTENT = b"Reliable UDP integration test\n"


def sha256_file(path):
    with open(path, "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()


def start_server():
    process = multiprocessing.Process(target=server.main)
    process.start()
    time.sleep(1)
    return process


def stop_server(process):
    process.terminate()
    process.join(timeout=3)


def remove_if_exists(path):
    if os.path.exists(path):
        os.remove(path)


def test_full_client_server_flow(tmp_path):

    upload_path = tmp_path / TEST_FILENAME
    download_path = tmp_path / f"downloaded_{TEST_FILENAME}"
    shared_path = os.path.join("shared", TEST_FILENAME)

    upload_path.write_bytes(TEST_CONTENT)

    remove_if_exists(shared_path)
    remove_if_exists(download_path)

    print("\n=== Iniciando servidor ===")
    process = start_server()

    try:

        print("1. Login incorrecto")
        assert client.login("admin", "wrong-password") is False

        print("2. Login correcto")
        assert client.login("admin", "1234") is True

        print("3. Listar archivos")
        files_before_upload = client.list_files()
        print(files_before_upload)

        print("4. Upload")
        assert client.upload_file(str(upload_path), TEST_FILENAME) is True

        print("5. Listar nuevamente")
        files_after_upload = client.list_files()
        print(files_after_upload)

        assert TEST_FILENAME in files_after_upload

        print("6. Download")
        assert client.download_file(
            TEST_FILENAME,
            str(download_path)
        ) is True

        print("7. Verificando SHA256")
        assert sha256_file(upload_path) == sha256_file(download_path)

        print("8. Estadísticas")
        print(client.udp.get_statistics())

        print("=== TEST FINALIZADO ===")

    finally:
        print("Deteniendo servidor...")
        stop_server(process)

        remove_if_exists(shared_path)
        remove_if_exists(download_path)

        client.udp.sock.close()