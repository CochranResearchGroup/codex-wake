"""Local-only refusal controls for the read-only adapter experiment."""
import json
import socket
import threading
from qualify_clock_sources import collect, ntp

results = []
for kind in ('short', 'unsynchronized', 'wrong_origin', 'timeout'):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind(('127.0.0.1', 0))
        server.settimeout(5)
        port = server.getsockname()[1]
        def reply(kind=kind):
            request, peer = server.recvfrom(512)
            if kind == 'timeout':
                return
            packet = bytearray(48)
            packet[0], packet[1] = 0x24, 1
            packet[24:32] = request[40:48]
            if kind == 'short':
                packet = packet[:10]
            elif kind == 'unsynchronized':
                packet[0] = 0xe4
            else:
                packet[24:32] = bytes(8)
            server.sendto(packet, peer)
        worker = threading.Thread(target=reply)
        worker.start()
        results.append(collect(kind, lambda: ntp('127.0.0.1', port)))
        worker.join()
print(json.dumps(results, indent=2))
if any(row['ok'] for row in results):
    raise SystemExit('failure control admitted an observation')
