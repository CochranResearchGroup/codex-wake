"""Read-only, bounded adapter experiment. Never sets any system clock."""
import concurrent.futures
import json
import os
import socket
import struct
import subprocess
import time
from pathlib import Path

RAW = time.CLOCK_MONOTONIC_RAW

def raw():
    return time.clock_gettime(RAW)

def ntp(host, port=123):
    # Connected socket pins the reply peer. Random origin token avoids trusting Linux UTC.
    token = os.urandom(8)
    request = bytearray(48)
    request[0] = 0x23
    request[40:48] = token
    started = raw()
    addresses = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_DGRAM)
    ip = addresses[0][4][0]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(3)
        sock.connect((ip, port))
        sent = raw()
        sock.send(request)
        packet = sock.recv(512)
        received = raw()
    if len(packet) != 48:
        raise ValueError('only plain 48-byte NTP supported in this experiment')
    li, version, mode = packet[0] >> 6, (packet[0] >> 3) & 7, packet[0] & 7
    if li == 3 or version not in (3, 4) or mode != 4 or not 1 <= packet[1] <= 15:
        raise ValueError('unsynchronized, invalid reply, or kiss-of-death')
    if packet[24:32] != token:
        raise ValueError('origin mismatch')
    def stamp(offset):
        sec, frac = struct.unpack_from('!II', packet, offset)
        return sec - 2208988800 + frac / 2**32
    rx, tx = stamp(32), stamp(40)
    delay = struct.unpack_from('!i', packet, 4)[0] / 65536
    dispersion = struct.unpack_from('!I', packet, 8)[0] / 65536
    rtt = received - sent
    if packet[32:40] == bytes(8) or packet[40:48] == bytes(8) or tx < rx or tx-rx > rtt+.01 or dispersion > 5 or abs(delay)>10:
        raise ValueError('implausible timestamps or root quality')
    uncertainty = dispersion + abs(delay)/2
    return dict(source=host,peer=ip,received_raw=received,rtt_raw_seconds=rtt,dns_seconds=sent-started,
                server_tx_utc=tx,interval_at_receive=[tx-uncertainty,tx+rtt+uncertainty],
                stratum=packet[1],leap=li,root_dispersion=dispersion,authenticated=False)

def windows():
    script="[ordered]@{utcTicks=[DateTime]::UtcNow.Ticks;qpc=[Diagnostics.Stopwatch]::GetTimestamp();frequency=[Diagnostics.Stopwatch]::Frequency}|ConvertTo-Json -Compress"
    begin=raw()
    result=subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,timeout=8)
    end=raw()
    if result.returncode:
        raise ValueError(result.stderr.decode(errors='replace')[:250])
    item=json.loads(result.stdout.decode('utf-8-sig'))
    utc=(int(item['utcTicks'])-621355968000000000)/10**7
    return dict(source='Windows',received_raw=end,utc=utc,interop_duration_raw_seconds=end-begin,
                transport_interval_at_receive=[utc,utc+end-begin],qpc=item['qpc'],frequency=item['frequency'],
                accuracy_bound='unknown: transport interval excludes Windows UTC error')

def collect(name,call):
    try:return dict(ok=True,**call())
    except Exception as exc:return dict(source=name,ok=False,error=type(exc).__name__,detail=str(exc)[:300])

def main():
    tasks=[('Windows',windows),('time.cloudflare.com',lambda:ntp('time.cloudflare.com')),('time.nist.gov',lambda:ntp('time.nist.gov'))]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows=list(pool.map(lambda x:collect(*x),tasks))
    print(json.dumps(dict(experiment='read-only source transport qualification',boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),samples=rows,limitations=['DNS is bounded only by the outer process timeout','RAW duration is a diagnostic measurement, not qualified absolute time','UDP NTP is not authenticated','NTP era 0 only; not production ready','No source-selection authorization or mailbox effects']),indent=2))

if __name__=='__main__':main()
