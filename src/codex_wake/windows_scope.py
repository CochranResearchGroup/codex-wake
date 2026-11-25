"""Exact Windows execution scope from the primary token of a local process."""
from __future__ import annotations

import os
from pathlib import Path
import re


class ScopeError(ValueError):
    pass


def scope_identity(value):
    if (not isinstance(value, dict) or set(value) != {'sid', 'elevated'}
            or not isinstance(value['sid'], str) or len(value['sid']) > 184
            or not re.fullmatch(r'S-1(?:-[0-9]+)+', value['sid'])
            or type(value['elevated']) is not bool):
        raise ScopeError('windows_scope_identity_invalid')
    return value


def process_scope(pid=None):
    if os.name != 'nt':
        raise ScopeError('native_windows_executor_required')
    import ctypes
    from ctypes import wintypes as w

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    security = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.OpenProcess.argtypes = (w.DWORD, w.BOOL, w.DWORD)
    kernel.OpenProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = (w.HANDLE,)
    security.OpenProcessToken.argtypes = (w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE))
    security.GetTokenInformation.argtypes = (
        w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD))

    process = kernel.OpenProcess(0x1000, False, os.getpid() if pid is None else pid)
    if not process:
        raise ScopeError('windows_process_scope_unavailable')
    token = w.HANDLE()
    try:
        if not security.OpenProcessToken(process, 0x0008, ctypes.byref(token)):
            raise ScopeError('windows_process_scope_unavailable')
        from .tab_psmux_bridge import BridgeError, _sid_string

        def read_sid(information_class):
            size = w.DWORD()
            security.GetTokenInformation(token, information_class, None, 0, ctypes.byref(size))
            if not 0 < size.value <= 1024:
                raise ScopeError('windows_process_scope_unavailable')
            value = ctypes.create_string_buffer(size.value)
            if not security.GetTokenInformation(token, information_class, value, len(value), ctypes.byref(size)):
                raise ScopeError('windows_process_scope_unavailable')
            return _sid_string(ctypes.cast(value, ctypes.POINTER(ctypes.c_void_p))[0])

        try:
            sid = read_sid(1)
            integrity = read_sid(25)
        except BridgeError as exc:
            raise ScopeError('windows_process_scope_unavailable') from exc
        if integrity not in ('S-1-16-8192', 'S-1-16-12288'):
            raise ScopeError('windows_integrity_level_unsupported')
        return scope_identity(dict(sid=sid, elevated=integrity == 'S-1-16-12288'))
    finally:
        if token:
            kernel.CloseHandle(token)
        kernel.CloseHandle(process)


def require_scope(expected=None, *, pid=None):
    """An unpinned legacy caller remains limited to non-elevated execution."""
    actual = process_scope(pid)
    if (expected is None and actual['elevated']
            or expected is not None and actual != scope_identity(expected)):
        raise ScopeError('windows_execution_scope_changed')
    return actual


def set_created_owner(path, identity):
    """Pin a newly created object inside the private elevated scope directory."""
    if identity is None or not identity['elevated']:
        return
    actual = require_scope(identity)
    import ctypes
    from ctypes import wintypes as w

    kernel = ctypes.WinDLL('kernel32')
    kernel.LocalFree.argtypes = (ctypes.c_void_p,)
    kernel.LocalFree.restype = ctypes.c_void_p
    security = ctypes.WinDLL('advapi32')
    security.ConvertStringSidToSidW.argtypes = (w.LPCWSTR, ctypes.POINTER(ctypes.c_void_p))
    security.SetNamedSecurityInfoW.argtypes = (w.LPWSTR, ctypes.c_int, w.DWORD, *([ctypes.c_void_p] * 4))
    security.SetNamedSecurityInfoW.restype = w.DWORD
    sid = ctypes.c_void_p()
    if not security.ConvertStringSidToSidW(actual['sid'], ctypes.byref(sid)):
        raise ScopeError('windows_created_owner_unverified')
    try:
        if security.SetNamedSecurityInfoW(str(path), 1, 1, sid, None, None, None):
            raise ScopeError('windows_created_owner_unverified')
    finally:
        kernel.LocalFree(sid)


def require_elevated_path(path, identity, *, no_read_up=False):
    """Require Windows no-write-up protection where normal and elevated share a SID."""
    if identity is None or not identity['elevated']:
        return
    import ctypes
    from ctypes import wintypes as w
    from .tab_psmux_bridge import BridgeError, _sid_string

    required_policy = 3 if no_read_up else 1
    path = Path(path)
    if (not path.is_absolute() or path != path.resolve(strict=True)
            or getattr(path.lstat(), 'st_file_attributes', 0) & 1024):
        raise ScopeError('windows_elevated_path_unprotected')
    kernel = ctypes.WinDLL('kernel32')
    security = ctypes.WinDLL('advapi32')
    kernel.LocalFree.argtypes = (ctypes.c_void_p,)
    kernel.LocalFree.restype = ctypes.c_void_p
    security.GetNamedSecurityInfoW.argtypes = (w.LPWSTR, ctypes.c_int, w.DWORD,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p))
    security.GetNamedSecurityInfoW.restype = w.DWORD
    security.GetAce.argtypes = (ctypes.c_void_p, w.DWORD, ctypes.POINTER(ctypes.c_void_p))
    label, descriptor = ctypes.c_void_p(), ctypes.c_void_p()
    if security.GetNamedSecurityInfoW(str(path), 1, 0x10, None, None, None,
                                      ctypes.byref(label), ctypes.byref(descriptor)):
        raise ScopeError('windows_elevated_path_unprotected')
    try:
        if label.value:
            count = ctypes.c_ushort.from_address(label.value + 4).value
            for index in range(min(count, 256)):
                entry = ctypes.c_void_p()
                if not security.GetAce(label, index, ctypes.byref(entry)):
                    break
                kind, flags = bytes((ctypes.c_ubyte * 2).from_address(entry.value))
                mask = w.DWORD.from_address(entry.value + 4).value
                if (kind == 0x11 and not flags & 0x08 and mask & required_policy == required_policy
                        and _sid_string(entry.value + 8) == 'S-1-16-12288'):
                    return
    except BridgeError:
        pass
    finally:
        kernel.LocalFree(descriptor)
    raise ScopeError('windows_elevated_path_unprotected')


def executor_enabled(path, identity):
    if identity is None or not scope_identity(identity)['elevated']:
        return True
    if path is None:
        return False
    import json

    from .tab_psmux_bridge import check_private_manifest
    try:
        path = Path(path)
        if (not path.is_absolute() or path != path.resolve(strict=True) or not path.is_file()
                or getattr(path.lstat(), 'st_file_attributes', 0) & 1024):
            return False
        check_private_manifest(path)
        require_elevated_path(path, identity)
        if path.stat().st_size > 4096:
            return False
        config = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return False
    return (isinstance(config, dict) and set(config) == {'version', 'scope', 'enabled'} and type(config['version']) is int
            and config['version'] == 1 and config['scope'] == identity and config['enabled'] is True)


def main(argv=None):
    import argparse
    import json

    argparse.ArgumentParser(prog='codex-wake windows-scope').parse_args(argv)
    try:
        print(json.dumps(process_scope(), sort_keys=True))
        return 0
    except ScopeError as exc:
        print(json.dumps(dict(status='held', reason=str(exc)), sort_keys=True))
        return 2
