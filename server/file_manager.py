import os


SHARED_FOLDER = "shared"


def list_files():

    return os.listdir(SHARED_FOLDER)


def file_exists(filename):

    return os.path.exists(os.path.join(SHARED_FOLDER, filename))


def read_file(filename):

    with open(os.path.join(SHARED_FOLDER, filename), "rb") as file:
        return file.read()


def write_file(filename, content):

    with open(os.path.join(SHARED_FOLDER, filename), "wb") as file:
        file.write(content)