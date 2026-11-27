"""Read native Linux UTC and its synchronization bound in one kernel call."""
import ctypes
import math
import platform
import sys


class Timex(ctypes.Structure):
    # Native 64-bit Linux struct timex. modes=0 makes adjtimex read-only.
    _fields_ = [
        ('modes', ctypes.c_uint),
        ('offset', ctypes.c_long), ('freq', ctypes.c_long),
        ('maxerror', ctypes.c_long), ('esterror', ctypes.c_long),
        ('status', ctypes.c_int),
        ('constant', ctypes.c_long), ('precision', ctypes.c_long),
        ('tolerance', ctypes.c_long),
        ('seconds', ctypes.c_long), ('fraction', ctypes.c_long),
        ('tick', ctypes.c_long), ('ppsfreq', ctypes.c_long),
        ('jitter', ctypes.c_long), ('shift', ctypes.c_int),
        ('stabil', ctypes.c_long), ('jitcnt', ctypes.c_long),
        ('calcnt', ctypes.c_long), ('errcnt', ctypes.c_long),
        ('stbcnt', ctypes.c_long), ('tai', ctypes.c_int),
        ('padding', ctypes.c_int * 11),
    ]


def native_linux():
    if sys.platform != 'linux':
        return False
    kernel = platform.uname()
    return 'microsoft' not in (kernel.release + ' ' + kernel.version).lower()


def measurement():
    if ctypes.sizeof(ctypes.c_long) != 8 or ctypes.sizeof(Timex) != 208:
        raise ValueError('unsupported native Linux clock ABI')
    stamp = Timex()
    query = ctypes.CDLL(None, use_errno=True).adjtimex
    query.argtypes = [ctypes.POINTER(Timex)]
    query.restype = ctypes.c_int
    state = query(ctypes.byref(stamp))
    return state, stamp


def snapshot():
    unavailable = {'utc': None, 'counter': None, 'reason': 'native_linux_clock_unqualified'}
    try:
        state, stamp = measurement()
    except (OSError, ValueError, AttributeError):
        return unavailable
    if state != 0 or stamp.status & (0x0040 | 0x1000) or not 0 <= stamp.maxerror <= 1_000_000:
        return unavailable
    scale = 1_000_000_000 if stamp.status & 0x2000 else 1_000_000
    if stamp.seconds <= 0 or not 0 <= stamp.fraction < scale:
        return unavailable
    center = stamp.seconds + stamp.fraction / scale
    uncertainty = stamp.maxerror / 1_000_000 + 1 / scale
    return {
        'utc': {'status': 'native-linux', 'sources': ['linux:adjtimex'],
                'lower': math.nextafter(center - uncertainty, -math.inf),
                'upper': math.nextafter(center + uncertainty, math.inf), 'reason': ''},
        'counter': None, 'reason': 'native_linux_synchronized_utc',
    }
