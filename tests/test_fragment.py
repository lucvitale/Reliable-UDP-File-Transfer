from protocol.fragment import fragment_data, join_fragments

data = b"A" * 5000

parts = fragment_data(data)

print("Cantidad de fragmentos:", len(parts))

print("Primer fragmento:", len(parts[0]))

print("Último fragmento:", len(parts[-1]))

joined = join_fragments(parts)

print(joined == data)