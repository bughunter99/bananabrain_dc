#!/usr/bin/env python3
"""
Console-compatible Chaoslauncher replacement (Python, Windows only).

Goals:
- Reuse existing Chaoslauncher.ini values.
- Launch StarCraft suspended, run BWL4 plugin patch callbacks, then resume.
- Keep behavior close to launcher/Source/Launcher/Launcher/*.pas.

This tool targets 32-bit Python for best compatibility with legacy 32-bit plugins.
"""

import argparse
import configparser
import ctypes
import ctypes.wintypes as wt
import datetime as _dt
import glob
import os
import subprocess
import sys
import time
import traceback
import winreg
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ------------------------------ WinAPI constants ------------------------------

CREATE_SUSPENDED = 0x00000004
PROCESS_ALL_ACCESS = 0x1F0FFF
WAIT_TIMEOUT = 0x00000102
SE_PRIVILEGE_ENABLED = 0x00000002
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
ERROR_NOT_ALL_ASSIGNED = 1300

WM_USER = 0x0400
CHAOSLAUNCHER_SC_NOTIFY = WM_USER + 0x02

# From Downloads Source: Experimente/MultipleInstance/MultipleInstance.dpr
MULTI_INSTANCE_PATCH_ADDRESS = 0x004DFFF0
MULTI_INSTANCE_PATCH_BYTES = bytes([0xE9, 0x89, 0x00, 0x00, 0x00, 0x90])
AUTO_PATCH_MAX_CANDIDATES = 64
AUTO_PATCH_PAIR_BASE = 8
SOURCE_MULTI_INSTANCE_PLUGINS = (
    "BWAPI 4.4.0 Injector [RELEASE]",
    "W-MODE 1.02",
)


# ------------------------------ WinAPI bindings ------------------------------

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
version_dll = ctypes.WinDLL("version", use_last_error=True)


class STARTUPINFOA(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("lpReserved", wt.LPSTR),
        ("lpDesktop", wt.LPSTR),
        ("lpTitle", wt.LPSTR),
        ("dwX", wt.DWORD),
        ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD),
        ("dwYSize", wt.DWORD),
        ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD),
        ("dwFillAttribute", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("wShowWindow", wt.WORD),
        ("cbReserved2", wt.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
        ("hStdInput", wt.HANDLE),
        ("hStdOutput", wt.HANDLE),
        ("hStdError", wt.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wt.HANDLE),
        ("hThread", wt.HANDLE),
        ("dwProcessId", wt.DWORD),
        ("dwThreadId", wt.DWORD),
    ]


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wt.DWORD), ("HighPart", wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wt.DWORD), ("Privileges", LUID_AND_ATTRIBUTES)]


class VS_FIXEDFILEINFO(ctypes.Structure):
    _fields_ = [
        ("dwSignature", wt.DWORD),
        ("dwStrucVersion", wt.DWORD),
        ("dwFileVersionMS", wt.DWORD),
        ("dwFileVersionLS", wt.DWORD),
        ("dwProductVersionMS", wt.DWORD),
        ("dwProductVersionLS", wt.DWORD),
        ("dwFileFlagsMask", wt.DWORD),
        ("dwFileFlags", wt.DWORD),
        ("dwFileOS", wt.DWORD),
        ("dwFileType", wt.DWORD),
        ("dwFileSubtype", wt.DWORD),
        ("dwFileDateMS", wt.DWORD),
        ("dwFileDateLS", wt.DWORD),
    ]


# Signatures
kernel32.CreateProcessA.argtypes = [
    wt.LPCSTR,
    wt.LPSTR,
    wt.LPVOID,
    wt.LPVOID,
    wt.BOOL,
    wt.DWORD,
    wt.LPVOID,
    wt.LPCSTR,
    ctypes.POINTER(STARTUPINFOA),
    ctypes.POINTER(PROCESS_INFORMATION),
]
kernel32.CreateProcessA.restype = wt.BOOL

kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.CloseHandle.restype = wt.BOOL

kernel32.ResumeThread.argtypes = [wt.HANDLE]
kernel32.ResumeThread.restype = wt.DWORD

kernel32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
kernel32.WaitForSingleObject.restype = wt.DWORD

kernel32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
kernel32.GetExitCodeProcess.restype = wt.BOOL

kernel32.WriteProcessMemory.argtypes = [
    wt.HANDLE,
    wt.LPVOID,
    wt.LPCVOID,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.WriteProcessMemory.restype = wt.BOOL

kernel32.ReadProcessMemory.argtypes = [
    wt.HANDLE,
    wt.LPCVOID,
    wt.LPVOID,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.ReadProcessMemory.restype = wt.BOOL

kernel32.GetCurrentProcess.argtypes = []
kernel32.GetCurrentProcess.restype = wt.HANDLE

user32.WaitForInputIdle.argtypes = [wt.HANDLE, wt.DWORD]
user32.WaitForInputIdle.restype = wt.DWORD

user32.FindWindowA.argtypes = [wt.LPCSTR, wt.LPCSTR]
user32.FindWindowA.restype = wt.HWND

user32.FindWindowExA.argtypes = [wt.HWND, wt.HWND, wt.LPCSTR, wt.LPCSTR]
user32.FindWindowExA.restype = wt.HWND

user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD

user32.SendMessageA.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.SendMessageA.restype = ctypes.c_long

advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
advapi32.OpenProcessToken.restype = wt.BOOL

advapi32.LookupPrivilegeValueA.argtypes = [wt.LPCSTR, wt.LPCSTR, ctypes.POINTER(LUID)]
advapi32.LookupPrivilegeValueA.restype = wt.BOOL

advapi32.AdjustTokenPrivileges.argtypes = [
    wt.HANDLE,
    wt.BOOL,
    ctypes.POINTER(TOKEN_PRIVILEGES),
    wt.DWORD,
    wt.LPVOID,
    wt.LPVOID,
]
advapi32.AdjustTokenPrivileges.restype = wt.BOOL

version_dll.GetFileVersionInfoSizeW.argtypes = [wt.LPCWSTR, ctypes.POINTER(wt.DWORD)]
version_dll.GetFileVersionInfoSizeW.restype = wt.DWORD

version_dll.GetFileVersionInfoW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, wt.LPVOID]
version_dll.GetFileVersionInfoW.restype = wt.BOOL

version_dll.VerQueryValueW.argtypes = [wt.LPCVOID, wt.LPCWSTR, ctypes.POINTER(wt.LPVOID), ctypes.POINTER(wt.UINT)]
version_dll.VerQueryValueW.restype = wt.BOOL


# ------------------------------ Data models ------------------------------


class Settings:
    def __init__(self, game_version_name: str, run_sc_on_startup: bool, warn_no_admin: bool) -> None:
        self.game_version_name = game_version_name
        self.run_sc_on_startup = run_sc_on_startup
        self.warn_no_admin = warn_no_admin


class GameVersion:
    def __init__(self, name: str, version: str, filename: str) -> None:
        self.name = name
        self.version = version
        self.filename = filename


class BWLExchangeData(ctypes.Structure):
    _fields_ = [
        ("PluginAPI", ctypes.c_int),
        ("StarCraftBuild", ctypes.c_int),
        ("NotSCBWmodule", wt.BOOL),
        ("ConfigDialog", wt.BOOL),
    ]


class BwlPlugin:
    def __init__(
        self,
        path: str,
        name: str,
        description: str,
        sc_build_id: int,
        enabled: bool,
        run_incompatible: bool,
        lib,
    ) -> None:
        self.path = path
        self.name = name
        self.description = description
        self.sc_build_id = sc_build_id
        self.enabled = enabled
        self.run_incompatible = run_incompatible
        self.lib = lib


BWL_BUILD_ID_TO_VERSION: Dict[int, str] = {
    -1: "All",
    0: "1.04",
    1: "1.08b",
    2: "1.09b",
    3: "1.10",
    4: "1.11b",
    5: "1.12b",
    6: "1.13f",
    7: "1.14.0",
    8: "1.15.0",
    9: "1.15.1",
    10: "1.15.2",
    11: "1.15.3",
    12: "1.16.0",
    13: "1.16.1",
}


# ------------------------------ Logging ------------------------------


class Logger:
    def __init__(self, log_path: Path, verbose: bool = True) -> None:
        self.log_path = log_path
        self.verbose = verbose
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, message: str) -> None:
        ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} {os.getpid()} {message}"
        if self.verbose:
            print(line)
        with self.log_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")


# ------------------------------ Helpers ------------------------------


def bool_from_ini(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_version(version_str: str) -> Tuple[int, int, int, int]:
    nums: List[int] = []
    cur = ""
    for ch in version_str:
        if ch.isdigit():
            cur += ch
        else:
            if cur:
                nums.append(int(cur))
                cur = ""
    if cur:
        nums.append(int(cur))
    while len(nums) < 4:
        nums.append(0)
    return nums[0], nums[1], nums[2], nums[3]


def get_version_info_buffer(path: str):
    handle = wt.DWORD(0)
    size = version_dll.GetFileVersionInfoSizeW(path, ctypes.byref(handle))
    if size == 0:
        return None

    buf = (ctypes.c_byte * size)()
    if not version_dll.GetFileVersionInfoW(path, 0, size, ctypes.byref(buf)):
        return None
    return buf


def get_fixed_file_version(path: str) -> Optional[Tuple[int, int, int, int]]:
    buf = get_version_info_buffer(path)
    if buf is None:
        return None

    value_ptr = wt.LPVOID()
    value_len = wt.UINT(0)
    if not version_dll.VerQueryValueW(ctypes.byref(buf), "\\", ctypes.byref(value_ptr), ctypes.byref(value_len)):
        return None

    ffi = ctypes.cast(value_ptr, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
    ms = ffi.dwProductVersionMS
    ls = ffi.dwProductVersionLS
    return ((ms >> 16) & 0xFFFF, ms & 0xFFFF, (ls >> 16) & 0xFFFF, ls & 0xFFFF)


def version_tuple_to_str(v: Tuple[int, int, int, int]) -> str:
    a, b, c, d = v
    out = f"{a}.{b}"
    if c != 0 or d != 0:
        out += f".{c}"
    if d != 0:
        out += f".{d}"
    return out


def get_localized_product_version(path: str) -> str:
    buf = get_version_info_buffer(path)
    if buf is None:
        return ""

    value_ptr = wt.LPVOID()
    value_len = wt.UINT(0)
    if not version_dll.VerQueryValueW(
        ctypes.byref(buf),
        "\\VarFileInfo\\Translation",
        ctypes.byref(value_ptr),
        ctypes.byref(value_len),
    ):
        return ""
    if value_len.value < 4:
        return ""

    words = ctypes.cast(value_ptr, ctypes.POINTER(wt.WORD))
    lang = int(words[0])
    codepage = int(words[1])
    query = "\\StringFileInfo\\%04x%04x\\ProductVersion" % (lang, codepage)

    value_ptr2 = wt.LPVOID()
    value_len2 = wt.UINT(0)
    if not version_dll.VerQueryValueW(
        ctypes.byref(buf),
        query,
        ctypes.byref(value_ptr2),
        ctypes.byref(value_len2),
    ):
        return ""
    if not value_ptr2:
        return ""

    s = ctypes.wstring_at(value_ptr2)
    s = s.replace("Version ", "").strip()
    return s


def get_product_version_string(path: str) -> str:
    localized = get_localized_product_version(path)
    if localized:
        return localized

    vt = get_fixed_file_version(path)
    if vt is None:
        return "Unknown"
    return version_tuple_to_str(vt)


def get_registry_game_path() -> str:
    subkey = r"SOFTWARE\Blizzard Entertainment\Starcraft"
    views = [
        winreg.KEY_READ | getattr(winreg, "KEY_WOW64_32KEY", 0),
        winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0),
        winreg.KEY_READ,
    ]

    for access in views:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey, 0, access) as k:
                value, _ = winreg.QueryValueEx(k, "InstallPath")
                if value:
                    return os.path.join(str(value), "")
        except OSError:
            continue
    return ""


def get_versions(game_path: str) -> List[GameVersion]:
    result: List[GameVersion] = []
    for exe in glob.glob(os.path.join(game_path, "Starcraft*.exe")):
        ver = get_product_version_string(exe)
        name = f"Starcraft {ver}"
        result.append(GameVersion(name=name, version=ver, filename=exe))

    result.sort(key=lambda v: parse_version(v.version))
    return result


def choose_version(versions: List[GameVersion], wanted_name: str) -> GameVersion:
    if not versions:
        raise RuntimeError("No Starcraft*.exe found in game path")

    for v in versions:
        if v.name == wanted_name:
            return v
    return versions[-1]


def enable_debug_privilege() -> Tuple[bool, str]:
    token = wt.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(token)):
        return False, f"OpenProcessToken failed ({ctypes.get_last_error()})"

    try:
        luid = LUID()
        if not advapi32.LookupPrivilegeValueA(None, b"SeDebugPrivilege", ctypes.byref(luid)):
            return False, f"LookupPrivilegeValue failed ({ctypes.get_last_error()})"

        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges.Luid = luid
        tp.Privileges.Attributes = SE_PRIVILEGE_ENABLED

        ctypes.set_last_error(0)
        if not advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp), 0, None, None):
            return False, f"AdjustTokenPrivileges failed ({ctypes.get_last_error()})"

        if ctypes.get_last_error() == ERROR_NOT_ALL_ASSIGNED:
            return False, "SeDebugPrivilege not assigned to token"

        return True, "ok"
    finally:
        kernel32.CloseHandle(token)


def write_process_memory(h_process: wt.HANDLE, address: int, data: bytes) -> None:
    written = ctypes.c_size_t(0)
    ok = kernel32.WriteProcessMemory(
        h_process,
        ctypes.c_void_p(address),
        data,
        len(data),
        ctypes.byref(written),
    )
    if not ok or written.value != len(data):
        raise RuntimeError(f"WriteProcessMemory failed at 0x{address:08X} (err={ctypes.get_last_error()})")


def read_process_memory(h_process: wt.HANDLE, address: int, size: int) -> bytes:
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t(0)
    ok = kernel32.ReadProcessMemory(
        h_process,
        ctypes.c_void_p(address),
        buf,
        size,
        ctypes.byref(read),
    )
    if not ok:
        raise RuntimeError(f"ReadProcessMemory failed at 0x{address:08X} (err={ctypes.get_last_error()})")
    return buf.raw[: int(read.value)]


def apply_multiple_instance_patch_if_needed(
    logger: Logger,
    version: GameVersion,
    h_process: wt.HANDLE,
    patch_address: int,
    disable_patch: bool,
) -> None:
    if disable_patch:
        logger.log("Multiple-instance patch disabled by argument")
        return
    if version.version != "1.16.1":
        logger.log(f"Skipping multi-instance patch for version {version.version}")
        return
    before = read_process_memory(h_process, patch_address, len(MULTI_INSTANCE_PATCH_BYTES))
    logger.log("Multi-instance bytes before patch @0x%08X: %s" % (patch_address, " ".join(["%02X" % b for b in before])))
    patch_bytes = build_multi_instance_patch_bytes(before)
    logger.log("Multi-instance patch bytes to write @0x%08X: %s" % (patch_address, " ".join(["%02X" % b for b in patch_bytes])))
    write_process_memory(h_process, patch_address, patch_bytes)
    after = read_process_memory(h_process, patch_address, len(MULTI_INSTANCE_PATCH_BYTES))
    logger.log("Multi-instance bytes after  patch @0x%08X: %s" % (patch_address, " ".join(["%02X" % b for b in after])))
    logger.log("Multiple-instance patch applied")


def build_multi_instance_patch_bytes(before: bytes) -> bytes:
    # Convert near conditional jump (0F 84/85 xx xx xx xx) into unconditional jump
    # while preserving the original relative displacement.
    if len(before) >= 6 and before[0] == 0x0F and before[1] in (0x84, 0x85):
        return bytes([0xE9]) + before[2:6] + bytes([0x90])

    # Already patched form.
    if len(before) >= 6 and before[0] == 0xE9 and before[5] == 0x90:
        return before[:6]

    # Fallback to legacy hard-coded bytes used by original experiment.
    return MULTI_INSTANCE_PATCH_BYTES


def get_pe32_imagebase_and_sections(exe_path: str):
    with open(exe_path, "rb") as f:
        data = f.read()

    if len(data) < 0x40:
        raise RuntimeError("EXE too small")

    pe_off = int.from_bytes(data[0x3C:0x40], "little")
    if pe_off + 0x18 > len(data):
        raise RuntimeError("Invalid PE header offset")

    num_sections = int.from_bytes(data[pe_off + 0x06: pe_off + 0x08], "little")
    opt_size = int.from_bytes(data[pe_off + 0x14: pe_off + 0x16], "little")
    magic = int.from_bytes(data[pe_off + 0x18: pe_off + 0x1A], "little")
    if magic != 0x10B:
        raise RuntimeError("Only PE32 is supported for auto patch scan")

    image_base = int.from_bytes(data[pe_off + 0x34: pe_off + 0x38], "little")

    sec_off = pe_off + 0x18 + opt_size
    sections = []
    for i in range(num_sections):
        off = sec_off + i * 40
        if off + 40 > len(data):
            break
        vsize = int.from_bytes(data[off + 8: off + 12], "little")
        vaddr = int.from_bytes(data[off + 12: off + 16], "little")
        raw_size = int.from_bytes(data[off + 16: off + 20], "little")
        raw_ptr = int.from_bytes(data[off + 20: off + 24], "little")
        chars = int.from_bytes(data[off + 36: off + 40], "little")
        sections.append((vsize, vaddr, raw_size, raw_ptr, chars))

    return image_base, sections, data


def find_multi_instance_patch_candidates(exe_path: str, around_va: int) -> List[int]:
    image_base, sections, data = get_pe32_imagebase_and_sections(exe_path)
    candidates: List[int] = []

    for (vsize, vaddr, raw_size, raw_ptr, chars) in sections:
        # Scan executable sections only.
        if (chars & 0x20000000) == 0:
            continue
        if raw_ptr <= 0 or raw_size <= 6:
            continue
        end = min(raw_ptr + raw_size, len(data))
        i = raw_ptr
        while i + 6 <= end:
            if data[i] == 0x0F and data[i + 1] in (0x84, 0x85):
                rva = vaddr + (i - raw_ptr)
                va = image_base + rva
                candidates.append(int(va))
            i += 1

    uniq = sorted(set(candidates), key=lambda a: abs(int(a) - int(around_va)))
    if len(uniq) > AUTO_PATCH_MAX_CANDIDATES:
        uniq = uniq[:AUTO_PATCH_MAX_CANDIDATES]
    return uniq


def create_process_suspended(exe_path: str) -> PROCESS_INFORMATION:
    si = STARTUPINFOA()
    si.cb = ctypes.sizeof(STARTUPINFOA)
    pi = PROCESS_INFORMATION()

    cwd = os.path.dirname(exe_path).encode("mbcs", errors="replace")
    app = exe_path.encode("mbcs", errors="replace")

    ok = kernel32.CreateProcessA(
        app,
        None,
        None,
        None,
        False,
        CREATE_SUSPENDED,
        None,
        cwd,
        ctypes.byref(si),
        ctypes.byref(pi),
    )
    if not ok:
        raise RuntimeError(f"CreateProcess failed ({ctypes.get_last_error()}) for {exe_path}")
    return pi


def wait_for_input_idle(h_process: wt.HANDLE, timeout_ms: int = 60000) -> None:
    rv = user32.WaitForInputIdle(h_process, timeout_ms)
    if rv != 0:
        raise RuntimeError(f"WaitForInputIdle failed/timeout (code={rv}, err={ctypes.get_last_error()})")


def process_running(h_process: wt.HANDLE) -> bool:
    rv = kernel32.WaitForSingleObject(h_process, 0)
    return rv == WAIT_TIMEOUT


def str_buffer(size: int) -> ctypes.Array:
    return ctypes.create_string_buffer(size)


def fit_zero_terminated(raw: bytes) -> str:
    i = raw.find(b"\x00")
    if i >= 0:
        raw = raw[:i]
    return raw.decode("mbcs", errors="replace").strip()


def plugin_version_is_compatible(sc_build_id: int, game_version: str) -> bool:
    mapped = BWL_BUILD_ID_TO_VERSION.get(sc_build_id, "Unknown")
    if mapped == "Unknown":
        raise RuntimeError("Plugin reports unknown StarCraft build id")
    if mapped == "All":
        return True
    return mapped == game_version


def load_bwl_plugins(
    launcher_dir: Path,
    ini: configparser.ConfigParser,
    game_version: str,
    logger: Logger,
    no_plugins: bool,
) -> List[BwlPlugin]:
    if no_plugins:
        logger.log("Plugin loading disabled by --no-plugins")
        return []

    plugins_enabled = ini["PluginsEnabled"] if ini.has_section("PluginsEnabled") else {}
    plugins_run_incompat = ini["PluginsRunIncompatible"] if ini.has_section("PluginsRunIncompatible") else {}

    plugins_dir = launcher_dir / "Plugins"
    result: List[BwlPlugin] = []

    for bwl_path in sorted(plugins_dir.rglob("*.bwl")):
        try:
            logger.log(f"Loading BWL4-Plugin {bwl_path}")
            lib = ctypes.WinDLL(str(bwl_path))

            get_plugin_api = ctypes.CFUNCTYPE(None, ctypes.POINTER(BWLExchangeData))(("GetPluginAPI", lib))
            data = BWLExchangeData()
            get_plugin_api(ctypes.byref(data))
            if data.PluginAPI != 4:
                logger.log(f"Skip {bwl_path.name}: PluginAPI={data.PluginAPI} (expected 4)")
                continue

            get_data = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p)(("GetData", lib))
            name_buf = str_buffer(1024)
            desc_buf = str_buffer(8192)
            url_buf = str_buffer(1024)
            get_data(name_buf, desc_buf, url_buf)

            name = fit_zero_terminated(name_buf.raw) or bwl_path.stem
            desc = fit_zero_terminated(desc_buf.raw)

            enabled = bool_from_ini(plugins_enabled.get(name, "0"), default=False)
            run_incompatible = bool_from_ini(plugins_run_incompat.get(name, "0"), default=False)

            p = BwlPlugin(
                path=str(bwl_path),
                name=name,
                description=desc,
                sc_build_id=int(data.StarCraftBuild),
                enabled=enabled,
                run_incompatible=run_incompatible,
                lib=lib,
            )

            comp = plugin_version_is_compatible(p.sc_build_id, game_version)
            if not comp and not p.run_incompatible:
                logger.log(f"Plugin incompatible and disabled: {p.name}")
                continue
            if not p.enabled:
                logger.log(f"Plugin disabled in ini: {p.name}")
                continue

            result.append(p)
            logger.log(f"Plugin loaded {p.name}")
        except Exception as exc:
            logger.log(f"Plugin load failed: {bwl_path} ({exc})")

    return result


def call_patch_suspended(plugin: BwlPlugin, h_process: wt.HANDLE, process_id: int, logger: Logger) -> None:
    fn = ctypes.CFUNCTYPE(wt.BOOL, wt.HANDLE, wt.DWORD)(("ApplyPatchSuspended", plugin.lib))
    logger.log(f"ApplyPatchSuspended for {plugin.name}")
    ok = fn(h_process, process_id)
    if not ok:
        raise RuntimeError(f"ApplyPatchSuspended failed in {plugin.name}")


def call_patch_window_created(plugin: BwlPlugin, h_process: wt.HANDLE, process_id: int, logger: Logger) -> None:
    fn = ctypes.CFUNCTYPE(wt.BOOL, wt.HANDLE, wt.DWORD)(("ApplyPatch", plugin.lib))
    logger.log(f"ApplyPatch for {plugin.name}")
    ok = fn(h_process, process_id)
    if not ok:
        raise RuntimeError(f"ApplyPatch failed in {plugin.name}")


def notify_starcraft_window_if_present() -> None:
    hwnd = user32.FindWindowA(b"SWarClass", None)
    if hwnd:
        user32.SendMessageA(hwnd, CHAOSLAUNCHER_SC_NOTIFY, 0, 0)


def find_sc_window_by_process_id(process_id: int) -> int:
    wnd = user32.FindWindowA(b"SWarClass", None)
    while wnd:
        pid = wt.DWORD(0)
        user32.GetWindowThreadProcessId(wnd, ctypes.byref(pid))
        if int(pid.value) == int(process_id):
            return int(wnd)
        wnd = user32.FindWindowExA(0, wnd, b"SWarClass", None)
    return 0


def get_sc_window_and_pid() -> Tuple[int, int]:
    wnd = user32.FindWindowA(b"SWarClass", None)
    if not wnd:
        return 0, 0
    pid = wt.DWORD(0)
    user32.GetWindowThreadProcessId(wnd, ctypes.byref(pid))
    return int(wnd), int(pid.value)


def notify_sc_window_for_pid(process_id: int) -> bool:
    hwnd = find_sc_window_by_process_id(process_id)
    if not hwnd:
        return False
    user32.SendMessageA(hwnd, CHAOSLAUNCHER_SC_NOTIFY, 0, 0)
    return True


def detect_fast_exit(h_process: wt.HANDLE, timeout_ms: int) -> Optional[int]:
    # Quick-exit usually means StarCraft single-instance guard still won.
    rv = kernel32.WaitForSingleObject(h_process, timeout_ms)
    if rv == WAIT_TIMEOUT:
        return None
    code = wt.DWORD(0)
    if kernel32.GetExitCodeProcess(h_process, ctypes.byref(code)):
        return int(code.value)
    return -1


def load_ini(ini_path: Path) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.optionxform = str
    if not ini_path.exists():
        raise FileNotFoundError(f"INI not found: {ini_path}")
    with ini_path.open("r", encoding="utf-8", errors="replace") as f:
        cfg.read_file(f)
    return cfg


def read_settings(cfg: configparser.ConfigParser) -> Settings:
    launcher = cfg["Launcher"] if cfg.has_section("Launcher") else {}
    return Settings(
        game_version_name=str(launcher.get("GameVersion", "")),
        run_sc_on_startup=bool_from_ini(launcher.get("RunScOnStartup", "0"), default=False),
        warn_no_admin=bool_from_ini(launcher.get("WarnNoAdmin", "1"), default=True),
    )


def apply_source_multiinstance_profile(cfg: configparser.ConfigParser, include_chaosplugin: bool) -> None:
    if not cfg.has_section("PluginsEnabled"):
        cfg.add_section("PluginsEnabled")

    cfg["PluginsEnabled"]["Chaosplugin for 1.16.1"] = "1" if include_chaosplugin else "0"
    for name in SOURCE_MULTI_INSTANCE_PLUGINS:
        cfg["PluginsEnabled"][name] = "1"


def get_ini_game_path(cfg: configparser.ConfigParser) -> str:
    if not cfg.has_section("ToolPaths"):
        return ""

    raw = str(cfg["ToolPaths"].get("0", "")).strip()
    if not raw:
        return ""

    p = Path(raw).expanduser()
    try:
        p = p.resolve()
    except Exception:
        pass

    s = str(p)
    if s.lower().endswith(".exe"):
        return os.path.join(str(Path(s).parent), "")
    return os.path.join(s, "")


def run_once(args: argparse.Namespace) -> int:
    launcher_dir = Path(__file__).resolve().parent
    ini_path = Path(args.ini).resolve() if args.ini else launcher_dir / "Chaoslauncher.ini"
    log_path = launcher_dir / "Chaoslauncher_python.log"
    logger = Logger(log_path, verbose=not args.quiet)

    logger.log("Logging started")
    logger.log(f"Python {sys.version.split()[0]} ({ctypes.sizeof(ctypes.c_void_p) * 8}-bit)")
    logger.log(f"Using ini: {ini_path}")

    if ctypes.sizeof(ctypes.c_void_p) != 4:
        logger.log("WARNING: 64-bit Python detected. 32-bit Python is strongly recommended.")

    cfg = load_ini(ini_path)
    settings = read_settings(cfg)

    if args.source_multiinstance_profile:
        apply_source_multiinstance_profile(cfg, args.include_chaosplugin)
        if args.include_chaosplugin:
            logger.log("Applied source multi-instance profile (enabled BWAPI/Chaosplugin/W-MODE)")
        else:
            logger.log("Applied source multi-instance profile (enabled BWAPI/W-MODE, Chaosplugin disabled)")

    ini_game_path = get_ini_game_path(cfg)

    if args.game_exe:
        forced_exe = Path(args.game_exe).expanduser().resolve()
        if not forced_exe.exists():
            raise FileNotFoundError("--game-exe not found: %s" % forced_exe)
        game_path = os.path.join(str(forced_exe.parent), "")
    elif args.game_path:
        forced_path = Path(args.game_path).expanduser().resolve()
        if not forced_path.exists():
            raise FileNotFoundError("--game-path not found: %s" % forced_path)
        game_path = os.path.join(str(forced_path), "")
    elif ini_game_path:
        game_path = ini_game_path
    else:
        game_path = get_registry_game_path()
        if not game_path:
            raise RuntimeError("Could not resolve StarCraft InstallPath from registry")
    logger.log(f"GamePath: {game_path}")

    if args.game_exe:
        ver = get_product_version_string(str(forced_exe))
        versions = [
            GameVersion(
                name="Starcraft %s" % ver,
                version=ver,
                filename=str(forced_exe),
            )
        ]
    else:
        versions = get_versions(game_path)

    if args.list_versions:
        for v in versions:
            print(f"{v.name} -> {v.filename}")
        return 0

    wanted_name = args.version_name or settings.game_version_name
    version = choose_version(versions, wanted_name)
    logger.log(f"Selected version: {version.name} ({version.filename})")

    patch_address = int(args.multi_patch_address, 0)
    logger.log("Using multi-instance patch address: 0x%08X" % patch_address)

    plugins = load_bwl_plugins(
        launcher_dir=launcher_dir,
        ini=cfg,
        game_version=version.version,
        logger=logger,
        no_plugins=args.no_plugins,
    )

    if args.dry_run:
        logger.log("Dry-run mode: no process launch")
        return 0

    ok_priv, msg = enable_debug_privilege()
    if ok_priv:
        logger.log("Obtained DebugPrivilege")
    else:
        logger.log(f"Could not obtain SeDebugPrivilege ({msg})")
        if settings.warn_no_admin:
            logger.log("WarnNoAdmin=1: some plugins may fail without admin privileges")

    candidate_addresses = [patch_address]
    auto_probe = (not args.no_auto_multi_patch) and (not args.disable_multi_patch) and (version.version == "1.16.1")
    if auto_probe:
        try:
            found = find_multi_instance_patch_candidates(version.filename, patch_address)
            for addr in found:
                if addr not in candidate_addresses:
                    candidate_addresses.append(addr)
            logger.log("Auto patch probe enabled. Candidate addresses: %d" % len(candidate_addresses))
        except Exception as exc:
            logger.log("Auto patch probe setup failed: %s" % exc)

    candidate_sets: List[Tuple[int, ...]] = []
    for addr in candidate_addresses:
        candidate_sets.append((addr,))

    if auto_probe and args.auto_multi_patch_pairs:
        pair_source = candidate_addresses[:AUTO_PATCH_PAIR_BASE]
        for i in range(len(pair_source)):
            for j in range(i + 1, len(pair_source)):
                candidate_sets.append((pair_source[i], pair_source[j]))
        logger.log("Auto dual-patch probe enabled. Candidate sets: %d" % len(candidate_sets))

    quick_probe_limit = max(1, int(args.quick_probe_limit))
    if not args.probe_all_patches and len(candidate_sets) > quick_probe_limit:
        logger.log(
            "Quick probe mode: trying first %d candidate set(s) only (use --probe-all-patches for exhaustive scan)."
            % quick_probe_limit
        )
        candidate_sets = candidate_sets[:quick_probe_limit]

    last_fast_exit: Optional[int] = None
    last_error: Optional[Exception] = None

    for idx, addr_set in enumerate(candidate_sets, start=1):
        pi: Optional[PROCESS_INFORMATION] = None
        try:
            patch_label = ",".join(["0x%08X" % a for a in addr_set])
            logger.log("CreateProcess (attempt %d/%d, patch=%s)" % (idx, len(candidate_sets), patch_label))
            pi = create_process_suspended(version.filename)

            for addr in addr_set:
                apply_multiple_instance_patch_if_needed(
                    logger,
                    version,
                    pi.hProcess,
                    addr,
                    args.disable_multi_patch,
                )

            logger.log("Call ScSuspended for active plugins")
            for p in plugins:
                try:
                    call_patch_suspended(p, pi.hProcess, int(pi.dwProcessId), logger)
                except Exception as exc:
                    logger.log(f"Plugin ScSuspended error ({p.name}): {exc}")

            logger.log("ResumeThread")
            kernel32.ResumeThread(pi.hThread)

            logger.log("WaitForInputIdle")
            wait_for_input_idle(pi.hProcess, 60000)

            if not process_running(pi.hProcess):
                raise RuntimeError("StarCraft terminated before patch completion")

            logger.log("Call ScWindowCreated for active plugins")
            for p in plugins:
                try:
                    call_patch_window_created(p, pi.hProcess, int(pi.dwProcessId), logger)
                except Exception as exc:
                    logger.log(f"Plugin ScWindowCreated error ({p.name}): {exc}")

            fast_exit_code = detect_fast_exit(pi.hProcess, args.fast_exit_timeout_ms)
            if fast_exit_code is not None:
                last_fast_exit = fast_exit_code
                logger.log(
                    "Launch attempt exited shortly after start (exit code=%s, patch=%s)."
                    % (fast_exit_code, patch_label)
                )
                continue

            if not notify_sc_window_for_pid(int(pi.dwProcessId)):
                logger.log("SC window for launched PID not found yet; skipped notify")
            logger.log("Starting Starcraft completed (patch=%s)" % patch_label)
            return 0
        except Exception as exc:
            last_error = exc
            logger.log("Launch attempt failed (patch=%s): %s" % (patch_label, exc))
            if not auto_probe:
                raise
        finally:
            if pi is not None:
                if pi.hThread:
                    kernel32.CloseHandle(pi.hThread)
                if pi.hProcess:
                    kernel32.CloseHandle(pi.hProcess)

    wnd, existing_pid = get_sc_window_and_pid()
    if wnd and args.focus_existing_on_block and not args.fail_on_single_instance:
        logger.log(
            "All launch attempts ended quickly. Fallback requested: focusing existing StarCraft PID=%s."
            % existing_pid
        )
        notify_starcraft_window_if_present()
        return 0

    if last_fast_exit is not None:
        raise RuntimeError(
            "StarCraft exited shortly after launch (exit code=%s) for all patch candidates. "
            "Single-instance guard is still active." % last_fast_exit
        )

    if last_error is not None:
        raise last_error

    raise RuntimeError("Launch failed for unknown reason")


def run_delegate_launcher(args: argparse.Namespace) -> int:
    launcher_exe = Path(args.delegate_launcher_exe).expanduser().resolve()
    if not launcher_exe.exists():
        raise FileNotFoundError("Delegate launcher not found: %s" % launcher_exe)

    if args.delegate_count < 1:
        raise ValueError("--delegate-count must be >= 1")

    print("Delegating launch to:", launcher_exe)
    for i in range(args.delegate_count):
        subprocess.Popen([str(launcher_exe)], cwd=str(launcher_exe.parent))
        print("Started delegate launcher (%d/%d)" % (i + 1, args.delegate_count))
        if i + 1 < args.delegate_count and args.delegate_interval_ms > 0:
            time.sleep(float(args.delegate_interval_ms) / 1000.0)
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Chaoslauncher-compatible console launcher")
    p.add_argument("--ini", help="Path to Chaoslauncher.ini (default: script dir)")
    p.add_argument("--game-path", help="Override game install directory instead of registry InstallPath")
    p.add_argument("--game-exe", help="Run this exact StarCraft exe (highest priority override)")
    p.add_argument("--version-name", help="Force version display name (e.g., 'Starcraft 1.16.1')")
    p.add_argument(
        "--source-multiinstance-profile",
        action="store_true",
        help="Apply multi-instance plugin profile based on Downloads Source (BWAPI + W-MODE; Chaosplugin off by default).",
    )
    p.add_argument(
        "--include-chaosplugin",
        action="store_true",
        help="When using source profile, also enable Chaosplugin (may increase crash risk).",
    )
    p.add_argument("--list-versions", action="store_true", help="List discovered StarCraft versions and exit")
    p.add_argument("--dry-run", action="store_true", help="Parse config/plugins only, do not launch game")
    p.add_argument("--no-plugins", action="store_true", help="Disable plugin loading and patch calls")
    p.add_argument("--quiet", action="store_true", help="Suppress console logs (still writes log file)")
    p.add_argument(
        "--fail-on-single-instance",
        action="store_true",
        help="Fail when second instance is blocked instead of falling back to existing StarCraft window.",
    )
    p.add_argument(
        "--focus-existing-on-block",
        action="store_true",
        help="If second launch is blocked, focus existing StarCraft window (legacy fallback behavior).",
    )
    p.add_argument(
        "--no-auto-multi-patch",
        action="store_true",
        help="Disable automatic probing of alternative multi-instance patch addresses.",
    )
    p.add_argument(
        "--auto-multi-patch-pairs",
        action="store_true",
        help="Probe two patch addresses together (slower, useful when binary has multiple guards).",
    )
    p.add_argument(
        "--probe-all-patches",
        action="store_true",
        help="Exhaustively try all discovered patch candidates (default: quick mode, stop after first set).",
    )
    p.add_argument(
        "--quick-probe-limit",
        type=int,
        default=1,
        help="When not using --probe-all-patches, try this many candidate sets (default: 1).",
    )
    p.add_argument(
        "--sc2-quick-probe",
        action="store_true",
        help="Convenience profile for StarCraft2 install: enables pairs, fail-fast, and wider quick probe window.",
    )
    p.add_argument(
        "--fast-exit-timeout-ms",
        type=int,
        default=7000,
        help="Treat process exit within this many milliseconds as launch failure (default: 7000).",
    )
    p.add_argument(
        "--multi-patch-address",
        default="0x004DFFF0",
        help="Address for multi-instance patch (default: 0x004DFFF0). Accepts hex like 0x004DFFF0.",
    )
    p.add_argument(
        "--disable-multi-patch",
        action="store_true",
        help="Disable multi-instance patch write (for diagnosis).",
    )
    p.add_argument(
        "--delegate-launcher-exe",
        help="Bypass Python patching and run this external launcher exe directly (e.g. working MultiInstance build).",
    )
    p.add_argument(
        "--delegate-count",
        type=int,
        default=1,
        help="How many external launcher processes to start when --delegate-launcher-exe is used.",
    )
    p.add_argument(
        "--delegate-interval-ms",
        type=int,
        default=600,
        help="Delay between delegate launches in milliseconds.",
    )
    return p


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        if args.sc2_quick_probe:
            args.auto_multi_patch_pairs = True
            args.fail_on_single_instance = True
            args.source_multiinstance_profile = True
            if not args.probe_all_patches and int(args.quick_probe_limit) <= 1:
                args.quick_probe_limit = 16

        if args.delegate_launcher_exe:
            return run_delegate_launcher(args)
        return run_once(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
