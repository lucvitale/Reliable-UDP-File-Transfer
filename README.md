# Reliable UDP File Transfer

A reliable file transfer system implemented over UDP using Python. The project provides reliable communication through a custom transport protocol that implements Go-Back-N, packet checksum validation, retransmissions, timeout control, and a Mini-CDN mechanism for automatic server selection based on RTT.

## Features

- Reliable file transfer over UDP
- Go-Back-N sliding window protocol
- Packet checksum verification
- Automatic retransmissions
- Configurable timeout
- File upload and download
- User authentication
- Mini-CDN with RTT-based server selection
- Configurable network simulation
  - Artificial latency
  - Packet loss
  - Window size
  - Timeout
- Transfer statistics
  - RTT
  - Throughput
  - Retransmissions
  - Timeouts

---

## Project Structure

```
.
├── client/
│   └── client.py
├── server/
│   ├── server.py
│   ├── users.json
│   └── file_manager.py
├── protocol/
│   ├── constants.py
│   ├── packet.py
│   └── reliable_udp.py
├── shared/
├── downloads/
├── tests/
└── README.md
```

---

## Requirements

- Python 3.11 or newer

Clone the repository:

```bash
git clone https://github.com/<your-user>/Reliable-UDP-File-Transfer.git
cd Reliable-UDP-File-Transfer
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

Windows:

```powershell
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

---

## Running the Servers

Two server instances can be executed simultaneously to simulate a Mini-CDN.

Server 1

```bash
python -m server.server 5000
```

Server 2

```bash
python -m server.server 5001
```

At startup, each server allows configuring:

- Artificial latency
- Packet loss
- Window size
- Timeout

These parameters are used during the experimental evaluation.

---

## Running the Client

Open a Python interpreter:

```bash
python
```

Import the client:

```python
from client.client import (
    login,
    list_files,
    upload_file,
    download_file,
)
```

Login:

```python
login("admin", "1234")
```

List files:

```python
list_files()
```

Upload:

```python
upload_file("archivo_1MB.bin")
```

Download:

```python
download_file(
    "archivo_1MB.bin",
    "downloads/archivo_1MB.bin",
)
```

---

## Mini-CDN

Before authenticating, the client:

1. Requests the list of available servers.
2. Measures the RTT of each server.
3. Selects the server with the lowest latency.
4. Uses that server for the entire session.

This reduces communication latency automatically.

---

## Reliable UDP Protocol

The protocol implements:

- Packet sequencing
- ACK packets
- Go-Back-N sliding window
- Timeout detection
- Automatic retransmissions
- Checksum verification
- File fragmentation and reassembly

---

## Experimental Configuration

The implementation supports configurable network simulation.

Parameters:

- Latency
- Packet loss
- Window size
- Timeout

These settings allow testing the protocol under different network conditions.

---

## Experiments

The protocol was evaluated under four scenarios:

1. Normal network conditions
2. Increased latency
3. High latency
4. Packet loss

Metrics collected:

- Average RTT
- Throughput
- Retransmissions
- Timeouts

File integrity was verified using SHA-256.

---

## Technologies

- Python 3
- UDP sockets
- Go-Back-N protocol
- SHA-256
- JSON

---

## Authors

Developed as a university project for the Computer Networks course.

- Luciano Burgos

---

## License

This project was developed exclusively for academic purposes.