"""Isolate the shared local Viewer namespace before starting unprivileged.

No default route, no DNS, no Admin/PG network membership. The ingress subnet
is retained for the fixed relay and host-port replies. Used only by the explicit local shared-Viewer deployment.
"""
import ctypes
import ipaddress
import os
from pathlib import Path
import socket
import struct
import sys
from urllib.parse import urlsplit

relay = urlsplit(os.environ['REPORT_ADMIN_BASE_URL'])
assert relay.scheme == 'http' and relay.port == 8090 and relay.path == ''
relay_ip = ipaddress.ip_address(relay.hostname)
assert relay_ip.version == 4 and relay_ip.is_private
assert os.environ.get('REPORT_VIO_VIEWER_ENABLED') == 'true'
vio_relay = urlsplit(os.environ['REPORT_VIO_ADMIN_BASE_URL'])
assert vio_relay.scheme == 'http' and vio_relay.port == 8090
assert ipaddress.ip_address(vio_relay.hostname).is_private
sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, socket.NETLINK_ROUTE)
sock.bind((0, 0)); sock.settimeout(5)
sequence = 0


def exchange(kind, flags, payload):
    global sequence
    sequence += 1
    sock.send(struct.pack('IHHII', 16 + len(payload), kind, flags, sequence, 0) + payload)
    replies = []
    while True:
        packet = sock.recv(65536); offset = 0
        while offset < len(packet):
            length, message, _, seq, _ = struct.unpack_from('IHHII', packet, offset)
            body = packet[offset + 16:offset + length]; offset += (length + 3) & ~3
            if seq != sequence: continue
            if message == 2:
                assert struct.unpack_from('i', body)[0] == 0, 'route operation failed'
                return replies
            if message == 3: return replies
            replies.append(body)


routes = exchange(26, 0x301, struct.pack('BBBBBBBBI', 2, 0, 0, 0, 0, 0, 0, 0, 0))
relay_interface = None
for route in routes:
    family, prefix, _, _, table, _, _, kind, _ = struct.unpack_from('BBBBBBBBI', route)
    if family == 2 and prefix == 0 and table == 254 and kind == 1:
        exchange(25, 5, route)
    if family == 2 and prefix > 0 and table == 254 and kind == 1:
        attrs = {}; offset = 12
        while offset < len(route):
            length, key = struct.unpack_from('HH', route, offset)
            attrs[key] = route[offset + 4:offset + length]
            offset += (length + 3) & ~3
        if 1 in attrs and 4 in attrs and relay_ip in ipaddress.ip_network((str(ipaddress.ip_address(attrs[1])), prefix)):
            relay_interface = attrs[4]
assert relay_interface is not None
# Only the connected private subnet is retained. The dedicated relay listener
# belongs to that subnet; no route to the Admin/PostgreSQL network is added.
sock.close()
assert not any(line.split()[1] == '00000000' for line in Path('/proc/net/route').read_text().splitlines()[1:])
assert Path('/proc/sys/net/ipv6/conf/all/disable_ipv6').read_text().strip() == '1'
assert Path('/proc/sys/net/ipv4/ip_forward').read_text().strip() == '0'
libc = ctypes.CDLL(None, use_errno=True)
assert libc.prctl(38, 1, 0, 0, 0) == 0
os.setgroups([]); os.setgid(10001)
for cap in range(int(Path('/proc/sys/kernel/cap_last_cap').read_text()) + 1):
    assert libc.prctl(24, cap, 0, 0, 0) == 0
os.setuid(10001)
os.execv(sys.executable, [sys.executable, '-B', '-m', 'uvicorn', 'main:app',
                        '--host', '0.0.0.0', '--port', '8000', '--no-access-log', '--no-proxy-headers'])
