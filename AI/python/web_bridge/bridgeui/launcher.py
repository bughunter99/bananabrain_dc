"""
StarCraft 실행 및 DLL 인젝션 헬퍼.

흐름:
  1. StarCraft.exe -w  (윈도우 모드)
  2. 프로세스가 뜰 때까지 잠시 대기
  3. CreateRemoteThread + LoadLibraryA 로 DLL 인젝션
"""

import ctypes
import ctypes.wintypes
import os
import subprocess
import threading
import time

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------

SC_EXE = r"D:\util\StarCraft\StarCraft.exe"
SC_DIR = r"D:\util\StarCraft"

_THIS_DIR    = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))

# wmode.bwl — DirectDraw 훅으로 하드웨어 가속 창모드 제공 (SC 창 생성 전 주입)
WMODE_BWL = os.path.normpath(
    os.path.join(_PROJECT_ROOT,
                 "launcher", "Source", "Launcher", "Launcher", "Plugins", "wmode.bwl")
)

DLL_RELEASE = os.path.join(_PROJECT_ROOT, "src", "Release", "ai_dc.dll")
DLL_DEBUG   = os.path.join(_PROJECT_ROOT, "src", "Debug",   "ai_dcd.dll")

# 인젝션 전에 추가로 주입할 DLL 목록 (순서 유지).
# StarCraft 폴더에 BWAPI.dll 이 있다면 자동으로 앞에 삽입됩니다.
_BWAPI_DLL = os.path.join(SC_DIR, "BWAPI.dll")

# ---------------------------------------------------------------------------
# Windows API 바인딩
# ---------------------------------------------------------------------------

_k32  = ctypes.WinDLL("kernel32", use_last_error=True)
_u32  = ctypes.WinDLL("user32",   use_last_error=True)

_PROCESS_ALL_ACCESS = 0x1F0FFF
_MEM_COMMIT         = 0x1000
_MEM_RESERVE        = 0x2000
_MEM_RELEASE        = 0x8000
_PAGE_READWRITE     = 0x04

_k32.OpenProcess.restype  = ctypes.wintypes.HANDLE
_k32.OpenProcess.argtypes = [
    ctypes.wintypes.DWORD,
    ctypes.wintypes.BOOL,
    ctypes.wintypes.DWORD,
]

_k32.VirtualAllocEx.restype  = ctypes.wintypes.LPVOID
_k32.VirtualAllocEx.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.LPVOID,
    ctypes.c_size_t,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD,
]

_k32.WriteProcessMemory.restype  = ctypes.wintypes.BOOL
_k32.WriteProcessMemory.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.LPVOID,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]

_k32.GetModuleHandleW.restype  = ctypes.wintypes.HMODULE
_k32.GetModuleHandleW.argtypes = [ctypes.wintypes.LPCWSTR]

_k32.GetProcAddress.restype  = ctypes.c_void_p
_k32.GetProcAddress.argtypes = [ctypes.wintypes.HMODULE, ctypes.c_char_p]

_k32.CreateRemoteThread.restype  = ctypes.wintypes.HANDLE
_k32.CreateRemoteThread.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.wintypes.LPVOID,
    ctypes.wintypes.DWORD,
    ctypes.POINTER(ctypes.wintypes.DWORD),
]

_k32.WaitForSingleObject.restype  = ctypes.wintypes.DWORD
_k32.WaitForSingleObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]

_k32.CloseHandle.restype  = ctypes.wintypes.BOOL
_k32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]

_k32.VirtualFreeEx.restype  = ctypes.wintypes.BOOL
_k32.VirtualFreeEx.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.LPVOID,
    ctypes.c_size_t,
    ctypes.wintypes.DWORD,
]

# user32 — 창 스타일 수정
_GWL_STYLE       = -16
_WS_CAPTION      = 0x00C00000   # 타이틀바 + 테두리
_WS_SYSMENU      = 0x00080000   # 닫기/최소화 버튼
_WS_THICKFRAME   = 0x00040000   # 크기 조정 가능한 테두리
_WS_MINIMIZEBOX  = 0x00020000
_SWP_NOMOVE      = 0x0002
_SWP_NOSIZE      = 0x0001
_SWP_NOZORDER    = 0x0004
_SWP_FRAMECHANGED = 0x0020
_SWP_SHOWWINDOW  = 0x0040
HWND_TOP = 0

_u32.FindWindowW.restype  = ctypes.wintypes.HWND
_u32.FindWindowW.argtypes = [ctypes.wintypes.LPCWSTR, ctypes.wintypes.LPCWSTR]

_u32.GetWindowLongW.restype  = ctypes.c_long
_u32.GetWindowLongW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]

_u32.SetWindowLongW.restype  = ctypes.c_long
_u32.SetWindowLongW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_long]

_u32.SetWindowPos.restype  = ctypes.wintypes.BOOL
_u32.SetWindowPos.argtypes = [
    ctypes.wintypes.HWND, ctypes.wintypes.HWND,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.wintypes.UINT,
]

_u32.SendMessageW.restype  = ctypes.c_long
_u32.SendMessageW.argtypes = [
    ctypes.wintypes.HWND, ctypes.wintypes.UINT,
    ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM,
]

_u32.GetWindowTextW.restype  = ctypes.c_int
_u32.GetWindowTextW.argtypes = [
    ctypes.wintypes.HWND, ctypes.wintypes.LPWSTR, ctypes.c_int,
]

_WNDENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
)
_u32.EnumChildWindows.restype  = ctypes.wintypes.BOOL
_u32.EnumChildWindows.argtypes = [
    ctypes.wintypes.HWND, _WNDENUMPROC, ctypes.wintypes.LPARAM,
]

_u32.WaitForInputIdle.restype  = ctypes.wintypes.DWORD
_u32.WaitForInputIdle.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]

_BM_CLICK = 0x00F5
_SW_MINIMIZE = 6

_u32.ShowWindow.restype  = ctypes.wintypes.BOOL
_u32.ShowWindow.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]


def _apply_windowed_style() -> bool:
    """
    SWarClass 창에 타이틀바/테두리를 달아 이동 가능한 창으로 만듭니다.
    StarCraft 창이 아직 뜨지 않았으면 False 를 반환합니다.
    """
    hwnd = _u32.FindWindowW("SWarClass", None)
    if not hwnd:
        return False

    style = _u32.GetWindowLongW(hwnd, _GWL_STYLE)
    new_style = style | _WS_CAPTION | _WS_SYSMENU | _WS_THICKFRAME | _WS_MINIMIZEBOX
    _u32.SetWindowLongW(hwnd, _GWL_STYLE, new_style)
    _u32.SetWindowPos(
        hwnd, HWND_TOP, 0, 0, 0, 0,
        _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOZORDER | _SWP_FRAMECHANGED | _SWP_SHOWWINDOW,
    )
    return True


def _inject_dll(pid: int, dll_path: str) -> None:
    """pid 프로세스에 dll_path 를 CreateRemoteThread + LoadLibraryA 방식으로 인젝션."""
    dll_bytes = os.path.abspath(dll_path).encode("mbcs") + b"\x00"

    h_proc = _k32.OpenProcess(_PROCESS_ALL_ACCESS, False, pid)
    if not h_proc:
        raise OSError(f"OpenProcess 실패 (err={ctypes.get_last_error()}, pid={pid})")

    try:
        remote_mem = _k32.VirtualAllocEx(
            h_proc, None, len(dll_bytes),
            _MEM_COMMIT | _MEM_RESERVE, _PAGE_READWRITE,
        )
        if not remote_mem:
            raise OSError(f"VirtualAllocEx 실패 (err={ctypes.get_last_error()})")

        try:
            written = ctypes.c_size_t(0)
            ok = _k32.WriteProcessMemory(
                h_proc, remote_mem,
                ctypes.cast(ctypes.c_char_p(dll_bytes), ctypes.c_void_p),
                len(dll_bytes), ctypes.byref(written),
            )
            if not ok:
                raise OSError(f"WriteProcessMemory 실패 (err={ctypes.get_last_error()})")

            h_k32    = _k32.GetModuleHandleW("kernel32.dll")
            loadlib  = _k32.GetProcAddress(h_k32, b"LoadLibraryA")
            if not loadlib:
                raise OSError("GetProcAddress(LoadLibraryA) 실패")

            h_thread = _k32.CreateRemoteThread(
                h_proc, None, 0,
                ctypes.cast(loadlib, ctypes.c_void_p),
                remote_mem, 0, None,
            )
            if not h_thread:
                raise OSError(f"CreateRemoteThread 실패 (err={ctypes.get_last_error()})")

            try:
                _k32.WaitForSingleObject(h_thread, 10_000)
            finally:
                _k32.CloseHandle(h_thread)
        finally:
            _k32.VirtualFreeEx(h_proc, remote_mem, 0, _MEM_RELEASE)
    finally:
        _k32.CloseHandle(h_proc)


# ---------------------------------------------------------------------------
# 공개 상태
# ---------------------------------------------------------------------------

_state_lock  = threading.Lock()
_launch_status = {"phase": "idle", "error": None, "pid": None}
# phase: idle | launching | injecting | running | error


def _set_phase(phase, error=None, pid=None):
    with _state_lock:
        _launch_status["phase"] = phase
        _launch_status["error"] = error
        if pid is not None:
            _launch_status["pid"] = pid


# ---------------------------------------------------------------------------
# psutil 기반 프로세스 탐색
# ---------------------------------------------------------------------------

def _find_sc_pid():
    """실행 중인 StarCraft.exe 의 PID 반환. 없으면 None."""
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "name"]):
            name = proc.info.get("name") or ""
            if name.lower() in ("starcraft.exe", "starcraft"):
                return proc.info["pid"]
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# 런처 스레드
# ---------------------------------------------------------------------------

def _launch_thread(debug: bool, extra_dlls: list):
    ai_dll = DLL_DEBUG if debug else DLL_RELEASE

    if not os.path.isfile(ai_dll):
        _set_phase("error", error=f"DLL 없음: {ai_dll}")
        return
    if not os.path.isfile(SC_EXE):
        _set_phase("error", error=f"StarCraft.exe 없음: {SC_EXE}")
        return

    # 이미 실행 중이면 인젝션만 시도
    existing_pid = _find_sc_pid()
    if existing_pid:
        _set_phase("injecting", pid=existing_pid)
        try:
            for d in extra_dlls:
                _inject_dll(existing_pid, d)
            _inject_dll(existing_pid, ai_dll)
            _apply_windowed_style()
            _set_phase("running", pid=existing_pid)
        except Exception as exc:
            _set_phase("error", error=str(exc))
        return

    # --------------- StarCraft 직접 실행 + wmode 조기 주입 ---------------
    _set_phase("launching")

    try:
        proc = subprocess.Popen([SC_EXE], cwd=SC_DIR)  # -w 없이 실행 (풀스크린 기본값)
    except Exception as exc:
        _set_phase("error", error=f"StarCraft 실행 실패: {exc}")
        return

    pid = proc.pid  # Popen 이 즉시 PID 반환

    # SC 메인 모듈이 로딩될 때까지 아주 짧게 대기 후
    # CreateWindowEx/DirectDraw 호출 전에 wmode.bwl 주입
    time.sleep(0.4)
    if os.path.isfile(WMODE_BWL):
        try:
            _inject_dll(pid, WMODE_BWL)
        except Exception as exc:
            # wmode 실패해도 게임 자체는 계속 진행 (풀스크린으로 뜸)
            pass

    # SC 창이 생성될 때까지 대기 (최대 30초)
    for _ in range(60):
        sc_hwnd = _u32.FindWindowW("SWarClass", None)
        if sc_hwnd:
            break
        time.sleep(0.5)
    else:
        _set_phase("error", error="StarCraft 창을 찾을 수 없음 (30초 초과)")
        return

    if proc.poll() is not None:
        _set_phase("error", error="StarCraft 가 즉시 종료됨")
        return

    # BWAPI.dll + ai_dc.dll 주입
    _set_phase("injecting", pid=pid)
    try:
        for d in extra_dlls:
            _inject_dll(pid, d)
        _inject_dll(pid, ai_dll)
    except Exception as exc:
        _set_phase("error", error=f"인젝션 실패: {exc}")
        return

    _set_phase("running", pid=pid)


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def launch_and_inject(debug: bool = False):
    """
    StarCraft 를 윈도우 모드로 실행 후 DLL 을 인젝션합니다 (비동기).
    즉시 반환하고, status() 로 진행 상황을 확인하세요.
    """
    with _state_lock:
        phase = _launch_status["phase"]
        if phase in ("launching", "injecting"):
            return {"ok": False, "error": "이미 시작 중입니다"}
        if phase == "running" and _find_sc_pid():
            return {"ok": False, "error": "StarCraft 가 이미 실행 중입니다"}

    # BWAPI.dll 이 StarCraft 폴더에 있으면 앞에 추가
    extra = []
    if os.path.isfile(_BWAPI_DLL):
        extra.append(_BWAPI_DLL)

    _set_phase("launching")
    t = threading.Thread(target=_launch_thread, args=(debug, extra), daemon=True)
    t.start()
    return {"ok": True, "status": "launching"}


def inject_into_running(debug: bool = False):
    """
    이미 실행 중인 StarCraft 에만 DLL 을 인젝션합니다 (런처 없이).
    카오스 런처 등 외부 프로그램으로 스타를 먼저 띄운 후 사용하세요.
    """
    pid = _find_sc_pid()
    if pid is None:
        return {"ok": False, "error": "실행 중인 StarCraft 를 찾을 수 없습니다"}

    ai_dll = DLL_DEBUG if debug else DLL_RELEASE
    if not os.path.isfile(ai_dll):
        return {"ok": False, "error": f"DLL 없음: {ai_dll}"}

    def _do():
        _set_phase("injecting", pid=pid)
        try:
            _inject_dll(pid, ai_dll)
            _set_phase("running", pid=pid)
        except Exception as exc:
            _set_phase("error", error=f"인젝션 실패: {exc}")

    _set_phase("injecting", pid=pid)
    threading.Thread(target=_do, daemon=True).start()
    return {"ok": True, "status": "injecting", "pid": pid}


def kill_starcraft():
    """StarCraft.exe 프로세스를 종료합니다."""
    pid = _find_sc_pid()
    if pid is None:
        return {"ok": False, "error": "StarCraft 가 실행 중이 아닙니다"}
    try:
        import psutil
        psutil.Process(pid).terminate()
        _set_phase("idle")
        return {"ok": True, "pid": pid}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def status():
    """현재 런처 상태를 반환합니다."""
    with _state_lock:
        s = dict(_launch_status)

    pid = _find_sc_pid()
    s["sc_running"] = pid is not None
    if pid:
        s["pid"] = pid
    # 실제로 살아있는데 phase 가 idle 이면 외부에서 실행된 경우
    if pid and s["phase"] == "idle":
        s["phase"] = "running"
    # 실제로 꺼졌는데 running 이면 갱신
    if not pid and s["phase"] == "running":
        with _state_lock:
            _launch_status["phase"] = "idle"
        s["phase"] = "idle"
    return s
