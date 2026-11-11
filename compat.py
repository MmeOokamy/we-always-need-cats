"""Cross-platform helpers so the cats run on Linux, macOS and Windows alike.

Only the standard library (and ctypes on Windows) is used here, with no Qt
import, so the status line script can load this module on every refresh.

The pieces that differ between systems are gathered here:

* the single-instance lock and the event channel, both built on a loopback UDP
  socket (Unix-domain sockets are not available the same way on Windows);
* finding out whether a process is still alive and which parent is Claude Code;
* starting a windowless background program.
"""

import os
import socket
import sys

IS_WINDOWS = sys.platform.startswith("win")

HOST = "127.0.0.1"
# Fixed loopback ports. Binding one is also how a program marks itself as
# running: a second instance fails to bind and steps aside. UDP over 127.0.0.1
# behaves the same on every OS, unlike Unix-domain sockets.
SESSION_PORT = 51710  # session cats: receives the events and acts as their lock


def has_display():
    """Whether a desktop is available to show a window."""
    if IS_WINDOWS:
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def instance_running(port):
    """True when a program already holds the port (so it is running).

    A UDP send to a dead port is not reliably reported, so running state is
    probed by trying to take the port instead.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.bind((HOST, port))
    except OSError:
        return True
    probe.close()
    return False


def claim_port(port):
    """Bind the port to mark this process as running; None if already taken.

    Keep the returned socket alive for as long as the program should live. The
    session cats also use it to receive their events.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((HOST, port))
    except OSError:
        sock.close()
        return None
    return sock


def send(port, data):
    """Send one datagram to a local program (check instance_running first)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(data, (HOST, port))


def process_alive(pid):
    """Whether a process still exists (to drop a cat when Claude stops)."""
    if not pid:
        return True
    if IS_WINDOWS:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return not ok or code.value == 259  # STILL_ACTIVE
    return os.path.exists(f"/proc/{pid}")


def claude_pid():
    """Walk up the parent processes to Claude Code, to know when it stops."""
    if IS_WINDOWS:
        return _claude_pid_windows()
    pid = os.getppid()
    for _ in range(8):
        try:
            with open(f"/proc/{pid}/comm") as f:
                name = f.read().strip()
            with open(f"/proc/{pid}/stat") as f:
                parent = int(f.read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            return 0
        if name in ("claude", "node"):
            return pid
        if parent <= 1:
            return 0
        pid = parent
    return 0


def _claude_pid_windows():
    """Windows equivalent: walk the process tree up to claude/node."""
    try:
        import ctypes
        from ctypes import wintypes

        class ProcessEntry(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_char * 260),
            ]

        kernel32 = ctypes.windll.kernel32
        snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
        if snapshot in (0, -1, wintypes.HANDLE(-1).value):
            return 0
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(ProcessEntry)
        parents = {}  # pid -> (ppid, lowercased executable name)
        if kernel32.Process32First(snapshot, ctypes.byref(entry)):
            while True:
                parents[entry.th32ProcessID] = (
                    entry.th32ParentProcessID,
                    entry.szExeFile.decode("latin-1", "ignore").lower(),
                )
                if not kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                    break
        kernel32.CloseHandle(snapshot)
        pid = os.getppid()
        for _ in range(12):
            info = parents.get(pid)
            if not info:
                return 0
            parent, name = info
            if name in ("claude.exe", "node.exe", "claude", "node"):
                return pid
            if parent <= 0 or parent == pid:
                return 0
            pid = parent
    except Exception:
        return 0
    return 0


def spawn_detached(script, log_path):
    """Start a Python GUI script in the background, without a console window."""
    import subprocess

    base = os.path.dirname(os.path.abspath(script))
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "ab") as log:
        if IS_WINDOWS:
            # pythonw.exe runs the interface without opening a console window.
            executable = sys.executable
            pythonw = os.path.join(os.path.dirname(executable), "pythonw.exe")
            if os.path.exists(pythonw):
                executable = pythonw
            flags = 0x00000008 | 0x08000000 | 0x00000200  # DETACHED | NO_WINDOW | NEW_GROUP
            subprocess.Popen(
                [executable, script],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                cwd=base,
                creationflags=flags,
                close_fds=True,
            )
        else:
            subprocess.Popen(
                ["/usr/bin/env", "python3", script],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                cwd=base,
                start_new_session=True,
            )
