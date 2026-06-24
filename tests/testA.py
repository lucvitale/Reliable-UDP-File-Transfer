from protocol.checksum import calculate_checksum, verify_checksum

data = b"Hola Mundo"

checksum = calculate_checksum(data)

print(checksum)

print(verify_checksum(data, checksum))

print(verify_checksum(b"Otro texto", checksum))